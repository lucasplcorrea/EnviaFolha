#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Envio RH - Servidor com PostgreSQL (Versão Corrigida)
"""

import http.server
import socketserver
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
import sys
import re
import time
import random

try:
    import PyPDF2
    PDF_PROCESSING_AVAILABLE = True
    print("✅ PyPDF2 disponível - processamento real de PDFs habilitado")
except ImportError:
    PDF_PROCESSING_AVAILABLE = False
    print("⚠️ PyPDF2 não instalado. Processamento de PDF será simulado.")

# Função para carregar variáveis do .env
def load_env_file():
    """Carrega variáveis do arquivo .env"""
    env_vars = {}
    
    # Tentar diferentes caminhos para o .env
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.getcwd(), '.env'),
        '.env'
    ]
    
    env_file = None
    for path in possible_paths:
        if os.path.exists(path):
            env_file = path
            break
    
    if not env_file:
        print(f"⚠️  Arquivo .env não encontrado nos caminhos: {possible_paths}")
        return env_vars
    
    print(f"📄 Carregando .env de: {env_file}")
    
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
                    os.environ[key.strip()] = value.strip()
        
        print(f"✅ Carregadas {len(env_vars)} variáveis do .env")
        return env_vars
    except Exception as e:
        print(f"❌ Erro ao carregar .env: {e}")
        return env_vars

# Carregar variáveis de ambiente primeiro
env_vars = load_env_file()

# Configuração do banco de dados PostgreSQL
def check_database_health():
    """Verifica se o banco de dados está online e acessível"""
    try:
        if not db_engine:
            return {"status": "error", "message": "Engine do banco não inicializada"}
        
        # Importar SQLAlchemy text
        from sqlalchemy import text
        
        # Testar conexão simples
        with db_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return {"status": "online", "message": "Banco de dados PostgreSQL está online"}
            
    except Exception as e:
        return {"status": "offline", "message": f"Banco de dados offline: {str(e)}"}

def setup_database():
    """Configura conexão com PostgreSQL e cria tabelas se necessário"""
    try:
        # Importações SQLAlchemy
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Usar DATABASE_URL do .env ou padrão
        database_url = os.getenv('DATABASE_URL', 'postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')
        print(f"🔌 Conectando ao PostgreSQL: {database_url}")
        
        engine = create_engine(database_url, echo=False)
        
        # Testar conexão
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conectado ao PostgreSQL: {version}")
        
        # Importar todos os modelos para garantir que estejam registrados
        from app.models import Base, User, Employee, Permission, Role, RolePermission, PayrollPeriod, PayrollData, PayrollTemplate, PayrollProcessingLog
        
        # Criar tabelas se não existirem
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas do banco de dados verificadas/criadas")
        
        # Criar sessão
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        return engine, SessionLocal
        
    except Exception as e:
        print(f"❌ Erro ao conectar com PostgreSQL: {e}")
        print("⚠️  Continuando com armazenamento JSON como fallback...")
        return None, None

# Inicializar banco de dados
db_engine, SessionLocal = setup_database()

def load_employees_data():
    """Carrega dados dos funcionários do PostgreSQL ou JSON como fallback"""
    if SessionLocal:
        try:
            # Importar models apenas se PostgreSQL disponível
            sys.path.append(os.path.dirname(__file__))
            from app.models import Employee
            
            db = SessionLocal()
            employees = db.query(Employee).filter(Employee.is_active == True).all()
            db.close()
            
            # Converter para formato compatível
            employees_data = []
            for emp in employees:
                emp_dict = {
                    "id": emp.id,
                    "unique_id": emp.unique_id,
                    "full_name": emp.name,  # Campo correto na tabela PostgreSQL
                    "phone_number": emp.phone,
                    "email": emp.email or "",
                    "department": emp.department or "",
                    "position": emp.position or "",
                    "is_active": emp.is_active
                }
                employees_data.append(emp_dict)
            
            print(f"✅ Carregados {len(employees_data)} funcionários do PostgreSQL")
            return {"employees": employees_data, "users": []}
            
        except Exception as e:
            print(f"❌ Erro ao carregar funcionários do PostgreSQL: {e}")
            print("⚠️  Tentando carregar do arquivo JSON...")
    
    # Fallback para JSON
    try:
        json_file = 'employees.json'
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                employees_count = len(data.get('employees', []))
                print(f"✅ Carregados {employees_count} funcionários do arquivo JSON")
                return data
        else:
            print("⚠️  Arquivo employees.json não encontrado. Criando estrutura vazia.")
            return {"employees": [], "users": []}
    except Exception as e:
        print(f"❌ Erro ao carregar employees.json: {e}")
        return {"employees": [], "users": []}

def save_employee_to_db(employee_data, created_by_user_id=3):
    """Salva funcionário no PostgreSQL ou JSON como fallback"""
    if SessionLocal:
        try:
            from app.models import Employee, User
            
            db = SessionLocal()
            
            # Verificar se o usuário existe
            user_exists = db.query(User).filter(User.id == created_by_user_id).first()
            if not user_exists:
                # Se não existe, buscar o primeiro usuário disponível
                first_user = db.query(User).first()
                if first_user:
                    created_by_user_id = first_user.id
                else:
                    db.close()
                    print("❌ Nenhum usuário encontrado no banco para created_by")
                    return False
            
            # Verificar se funcionário já existe
            existing = db.query(Employee).filter(
                Employee.unique_id == employee_data.get('unique_id')
            ).first()
            
            if existing:
                # Atualizar existente
                existing.name = employee_data.get('full_name', existing.name)
                existing.phone = employee_data.get('phone_number', existing.phone)
                existing.email = employee_data.get('email', existing.email)
                existing.department = employee_data.get('department', existing.department)
                existing.position = employee_data.get('position', existing.position)
                existing.is_active = employee_data.get('is_active', existing.is_active)
            else:
                # Criar novo
                new_employee = Employee(
                    unique_id=employee_data.get('unique_id'),
                    name=employee_data.get('full_name'),
                    cpf=employee_data.get('unique_id', '000.000.000-00'),
                    phone=employee_data.get('phone_number'),
                    email=employee_data.get('email'),
                    department=employee_data.get('department'),
                    position=employee_data.get('position'),
                    is_active=employee_data.get('is_active', True),
                    created_by=created_by_user_id
                )
                db.add(new_employee)
            
            db.commit()
            db.close()
            print(f"✅ Funcionário {employee_data.get('full_name')} salvo no PostgreSQL")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar funcionário no PostgreSQL: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
    
    # Fallback para JSON
    try:
        json_file = 'employees.json'
        data = load_employees_data()
        
        # Atualizar ou adicionar funcionário
        employees = data.get('employees', [])
        updated = False
        
        for i, emp in enumerate(employees):
            if emp.get('unique_id') == employee_data.get('unique_id'):
                employees[i] = employee_data
                updated = True
                break
        
        if not updated:
            employee_data['id'] = len(employees) + 1
            employees.append(employee_data)
        
        data['employees'] = employees
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Funcionário {employee_data.get('full_name')} salvo no arquivo JSON")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao salvar funcionário no JSON: {e}")
        return False

# Carregar dados iniciais
employees_data = load_employees_data()

class EnviaFolhaHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        print(f"🔧 OPTIONS recebido: {self.path}")
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Enviar headers CORS"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, apikey')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def send_json_response(self, data, status_code=200):
        """Enviar resposta JSON"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))
    
    def get_request_data(self):
        """Obter dados da requisição POST/PUT"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except:
            return {}
    
    def send_error(self, code, message=None):
        """Send error response with CORS headers"""
        try:
            self.send_response(code)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "error": message or "Erro interno do servidor",
                "code": code
            }
            
            response = json.dumps(error_response, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
        except (ConnectionAbortedError, BrokenPipeError):
            # Cliente desconectou antes de receber a resposta
            print("⚠️  Conexão abortada pelo cliente")
        except Exception as e:
            print(f"❌ Erro ao enviar resposta de erro: {e}")

    def send_json_response(self, data, status_code=200):
        """Send JSON response with CORS headers and error handling"""
        try:
            self.send_response(status_code)
            self.send_cors_headers()
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response = json.dumps(data, ensure_ascii=False)
            self.wfile.write(response.encode('utf-8'))
        except (ConnectionAbortedError, BrokenPipeError):
            # Cliente desconectou antes de receber a resposta
            print("⚠️  Conexão abortada pelo cliente")
        except Exception as e:
            print(f"❌ Erro ao enviar resposta JSON: {e}")
    
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.send_status_response()
        elif path == '/health':
            self.send_health_check()
        elif path == '/api/v1/database/health':
            self.send_database_health()
        elif path == '/api/v1/users':
            self.handle_users_list()
        elif path == '/api/v1/users/permissions':
            self.handle_available_permissions()
        elif path == '/api/v1/payroll/periods':
            self.handle_payroll_periods_list()
        elif path == '/api/v1/payroll/templates':
            self.handle_payroll_templates_list()
        elif path.startswith('/api/v1/payroll/periods/'):
            period_id = path.split('/')[-1]
            self.handle_payroll_period_summary(period_id)
        elif path == '/api/v1/employees':
            self.send_employees_list()
        elif path == '/api/v1/auth/me':
            self.handle_auth_me()
        elif path == '/api/v1/dashboard/stats':
            self.handle_dashboard_stats()
        elif path == '/api/v1/evolution/status':
            self.handle_evolution_status()
        elif path == '/api/v1/system/status':
            self.handle_system_status()
        elif path == '/api/v1/database/health':
            self.handle_database_health()
        elif path == '/api/v1/payrolls/processed':
            self.handle_payrolls_processed()
        elif path.startswith('/api/v1/employees/'):
            employee_id = path.split('/')[-1]
            self.send_employee_detail(employee_id)
        else:
            self.send_error(404, "Endpoint não encontrado")
    
    def do_POST(self):
        """Handle POST requests"""
        path = urllib.parse.urlparse(self.path).path
        print(f"🔥 POST recebido: {path}")
        
        if path == '/api/v1/auth/login':
            self.handle_login()
        elif path == '/api/v1/employees':
            self.handle_create_employee()
        elif path == '/api/v1/employees/import':
            self.handle_import_employees()
        elif path == '/api/v1/users':
            self.handle_create_user()
        elif path == '/api/v1/users/permissions':
            self.handle_update_user_permissions()
        elif path == '/api/v1/payroll/periods':
            self.handle_create_payroll_period()
        elif path == '/api/v1/payroll/templates':
            self.handle_create_payroll_template()
        elif path == '/api/v1/payroll/process':
            self.handle_process_payroll_file()
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urllib.parse.urlparse(self.path).path
        print(f"🔄 PUT recebido: {path}")
        
        if path.startswith('/api/v1/employees/'):
            employee_id = path.split('/')[-1]
            self.handle_update_employee(employee_id)
        elif path.startswith('/api/v1/users/'):
            user_id = path.split('/')[-1]
            self.handle_update_user(user_id)
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        path = urllib.parse.urlparse(self.path).path
        print(f"🗑️  DELETE recebido: {path}")
        
        if path.startswith('/api/v1/employees/'):
            employee_id = path.split('/')[-1]
            self.handle_delete_employee(employee_id)
        elif path.startswith('/api/v1/users/'):
            user_id = path.split('/')[-1]
            self.handle_delete_user(user_id)
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
        print(f"🗑️ DELETE recebido: {path}")
        
        if path == '/api/v1/employees/bulk':
            self.handle_bulk_delete_employees()
        elif path.startswith('/api/v1/employees/'):
            employee_id = path.split('/')[-1]
            self.handle_delete_employee(employee_id)
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_PATCH(self):
        """Handle PATCH requests"""
        path = urllib.parse.urlparse(self.path).path
        print(f"🔄 PATCH recebido: {path}")
        
        if path == '/api/v1/employees/bulk':
            self.handle_bulk_update_employees()
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def handle_login(self):
        """Handle authentication"""
        data = self.get_request_data()
        username = data.get('username')
        password = data.get('password')
        
        print(f"🔐 Tentativa de login - Username: '{username}', Password: '{password}'")
        print(f"📥 Dados recebidos: {data}")
        
        # Verificar no PostgreSQL se disponível
        if SessionLocal:
            try:
                sys.path.append(os.path.dirname(__file__))
                from app.models import User
                
                db = SessionLocal()
                user = db.query(User).filter(User.username == username).first()
                db.close()
                
                if user and user.verify_password(password):
                    print("✅ Login bem-sucedido com PostgreSQL!")
                    self.send_json_response({
                        "access_token": "postgres-token-123",
                        "token_type": "bearer",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "full_name": user.full_name,
                            "email": user.email,
                            "is_admin": user.is_admin
                        }
                    })
                    return
                else:
                    print("❌ Credenciais inválidas no PostgreSQL!")
                    self.send_json_response({"detail": "Credenciais inválidas"}, 401)
                    return
                    
            except Exception as e:
                print(f"❌ Erro na autenticação PostgreSQL: {e}")
        
        # Fallback para credenciais padrão
        if username == 'admin' and password == 'admin123':
            print("✅ Login bem-sucedido com credenciais padrão!")
            self.send_json_response({
                "access_token": "simple-token-123",
                "token_type": "bearer",
                "user": {
                    "id": 1,
                    "username": "admin",
                    "full_name": "Administrador",
                    "email": "admin@empresa.com",
                    "is_admin": True
                }
            })
        else:
            print("❌ Credenciais inválidas!")
            self.send_json_response({"detail": "Credenciais inválidas"}, 401)
    
    def send_status_response(self):
        """Resposta de status da aplicação"""
        db_status = "PostgreSQL" if SessionLocal else "JSON"
        
        status = {
            "message": "Sistema de Envio RH v2.0 com PostgreSQL",
            "status": "running",
            "database": db_status,
            "docs": "/docs",
            "python_version": sys.version.split()[0],
            "employees_count": len(employees_data.get('employees', [])),
            "note": "Servidor com integração PostgreSQL + JSON fallback"
        }
        
        self.send_json_response(status)
    
    def send_health_check(self):
        """Health check com status do banco"""
        db_health = check_database_health()
        
        health_status = {
            "status": "healthy" if db_health["status"] == "online" else "degraded",
            "database": {
                "status": db_health["status"],
                "message": db_health["message"],
                "type": "PostgreSQL" if SessionLocal else "JSON Fallback"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Retornar status HTTP 503 se banco estiver offline
        if db_health["status"] == "offline":
            self.send_response(503)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_cors_headers()
            self.end_headers()
        
        response = json.dumps(health_status, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))
    
    def send_database_health(self):
        """Endpoint específico para verificar saúde do banco"""
        try:
            db_health = check_database_health()
            
            # Retornar status HTTP apropriado baseado na saúde do banco
            if db_health["status"] == "online":
                status_code = 200
            elif db_health["status"] == "offline":
                status_code = 503
            else:
                status_code = 500
                
            self.send_json_response(db_health, status_code)
        except Exception as e:
            print(f"❌ Erro ao verificar saúde do banco: {e}")
            self.send_json_response({"error": "Erro interno ao verificar banco"}, 500)
    
    def send_employees_list(self):
        """Lista todos os funcionários"""
        try:
            current_data = load_employees_data()
            employees = current_data.get('employees', [])
            
            response = {
                "employees": employees,
                "total": len(employees),
                "source": "PostgreSQL" if SessionLocal else "JSON"
            }
            
            self.send_json_response(response)
            
        except Exception as e:
            self.send_json_response({"error": f"Erro ao carregar funcionários: {str(e)}"}, 500)
    
    def send_employee_detail(self, employee_id):
        """Detalhes de um funcionário específico"""
        try:
            current_data = load_employees_data()
            employees = current_data.get('employees', [])
            
            # Buscar por ID ou unique_id
            employee = None
            for emp in employees:
                if str(emp.get('id')) == employee_id or str(emp.get('unique_id')) == employee_id:
                    employee = emp
                    break
            
            if employee:
                self.send_json_response(employee)
            else:
                self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                
        except Exception as e:
            self.send_json_response({"error": f"Erro ao buscar funcionário: {str(e)}"}, 500)
    
    def handle_auth_me(self):
        """Endpoint para verificar usuário autenticado"""
        # Simular verificação de token - em produção, validar o token JWT
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_json_response({"detail": "Token de acesso necessário"}, 401)
            return
        
        # Retornar dados do usuário (simulado)
        user_data = {
            "id": 1,
            "username": "admin",
            "full_name": "Administrador",
            "email": "admin@empresa.com",
            "is_admin": True
        }
        self.send_json_response(user_data)
    
    def handle_dashboard_stats(self):
        """Estatísticas do dashboard"""
        try:
            current_data = load_employees_data()
            employees_count = len(current_data.get('employees', []))
            
            stats = {
                "total_employees": employees_count,
                "active_employees": employees_count,  # Assumindo todos ativos
                "payrolls_sent_this_month": 0,  # TODO: implementar contagem real
                "communications_sent_this_month": 0,  # TODO: implementar contagem real
                "last_payroll_send": None,  # TODO: implementar data real
                "evolution_api_status": "connected"  # TODO: verificar status real
            }
            
            self.send_json_response(stats)
            
        except Exception as e:
            self.send_json_response({"error": f"Erro ao carregar estatísticas: {str(e)}"}, 500)
    
    def handle_evolution_status(self):
        """Status da Evolution API"""
        # TODO: Implementar verificação real da Evolution API
        status = {
            "status": "connected",
            "instance_name": os.getenv('EVOLUTION_INSTANCE_NAME', 'API-Abecker'),
            "server_url": os.getenv('EVOLUTION_SERVER_URL', 'http://192.168.230.253:8080/'),
            "last_check": datetime.now().isoformat(),
            "message": "Simulado - verificação real da API não implementada"
        }
        
        self.send_json_response(status)
    
    def handle_payrolls_processed(self):
        """Lista de holerites processados"""
        try:
            # TODO: Implementar listagem real de holerites processados
            # Por enquanto, retornar lista vazia
            payrolls = {
                "payrolls": [],
                "total": 0,
                "message": "Nenhum holerite processado encontrado"
            }
            
            self.send_json_response(payrolls)
            
        except Exception as e:
            self.send_json_response({"error": f"Erro ao carregar holerites: {str(e)}"}, 500)
    
    def handle_create_employee(self):
        """Criar novo funcionário"""
        try:
            data = self.get_request_data()
            print(f"📝 Criando funcionário: {data}")
            
            # Validar dados obrigatórios
            required_fields = ['unique_id', 'full_name', 'phone_number']
            for field in required_fields:
                if not data.get(field):
                    self.send_json_response({"error": f"Campo obrigatório: {field}"}, 400)
                    return
            
            # Verificar se unique_id já existe
            current_data = load_employees_data()
            existing_employees = current_data.get('employees', [])
            
            for emp in existing_employees:
                if emp.get('unique_id') == data.get('unique_id'):
                    self.send_json_response({"error": f"ID único {data.get('unique_id')} já existe"}, 400)
                    return
            
            # Preparar dados do funcionário
            employee_data = {
                "unique_id": data.get('unique_id'),
                "full_name": data.get('full_name'),
                "phone_number": data.get('phone_number'),
                "email": data.get('email', ''),
                "department": data.get('department', ''),
                "position": data.get('position', ''),
                "is_active": True
            }
            
            # Salvar no banco
            if save_employee_to_db(employee_data):
                # Recarregar dados para obter o ID gerado
                global employees_data
                employees_data = load_employees_data()
                
                # Encontrar o funcionário recém-criado
                for emp in employees_data.get('employees', []):
                    if emp.get('unique_id') == employee_data.get('unique_id'):
                        employee_data = emp
                        break
                
                self.send_json_response(employee_data, 201)
                print(f"✅ Funcionário {employee_data.get('full_name')} criado com sucesso!")
            else:
                self.send_json_response({"error": "Erro ao salvar funcionário"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao criar funcionário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_update_employee(self, employee_id):
        """Atualizar funcionário existente"""
        try:
            data = self.get_request_data()
            print(f"🔄 Atualizando funcionário ID {employee_id}: {data}")
            
            # Buscar funcionário no PostgreSQL
            if SessionLocal:
                from app.models import Employee
                
                db = SessionLocal()
                
                # Buscar por ID ou unique_id
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Verificar se unique_id já existe em outro funcionário
                if data.get('unique_id') and data.get('unique_id') != employee.unique_id:
                    existing = db.query(Employee).filter(
                        Employee.unique_id == data.get('unique_id'),
                        Employee.id != employee.id
                    ).first()
                    
                    if existing:
                        db.close()
                        self.send_json_response({"error": f"ID único {data.get('unique_id')} já existe"}, 400)
                        return
                
                # Atualizar campos
                if 'unique_id' in data:
                    employee.unique_id = data['unique_id']
                if 'full_name' in data:
                    employee.name = data['full_name']
                if 'phone_number' in data:
                    employee.phone = data['phone_number']
                if 'email' in data:
                    employee.email = data['email']
                if 'department' in data:
                    employee.department = data['department']
                if 'position' in data:
                    employee.position = data['position']
                if 'is_active' in data:
                    employee.is_active = data['is_active']
                
                db.commit()
                
                # Preparar resposta
                updated_employee = {
                    "id": employee.id,
                    "unique_id": employee.unique_id,
                    "full_name": employee.name,
                    "phone_number": employee.phone,
                    "email": employee.email or "",
                    "department": employee.department or "",
                    "position": employee.position or "",
                    "is_active": employee.is_active
                }
                
                db.close()
                
                # Recarregar dados globais
                global employees_data
                employees_data = load_employees_data()
                
                self.send_json_response(updated_employee, 200)
                print(f"✅ Funcionário {updated_employee.get('full_name')} atualizado com sucesso!")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao atualizar funcionário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_delete_employee(self, employee_id):
        """Deletar funcionário (soft delete)"""
        try:
            print(f"🗑️ Deletando funcionário ID {employee_id}")
            
            # Buscar e deletar do PostgreSQL
            if SessionLocal:
                from app.models import Employee
                
                db = SessionLocal()
                
                # Buscar por ID ou unique_id
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Soft delete (marcar como inativo)
                employee.is_active = False
                db.commit()
                
                employee_name = employee.name
                db.close()
                
                # Recarregar dados globais
                global employees_data
                employees_data = load_employees_data()
                
                self.send_json_response({"message": f"Funcionário {employee_name} removido com sucesso"}, 200)
                print(f"✅ Funcionário {employee_name} marcado como inativo!")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar funcionário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_import_employees(self):
        """Handle Excel file import for employees"""
        try:
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                return
            
            # Get boundary from content type
            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break
            
            if not boundary:
                self.send_json_response({"error": "Boundary não encontrado no Content-Type"}, 400)
                return
            
            # Read the body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Parse multipart data
            file_data = self.parse_multipart_data(body, boundary)
            
            if not file_data:
                self.send_json_response({"error": "Arquivo não encontrado no upload"}, 400)
                return
            
            # Process Excel file
            import_result = self.process_excel_import(file_data)
            
            self.send_json_response(import_result, 200)
            
        except Exception as e:
            print(f"❌ Erro ao importar funcionários: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def parse_multipart_data(self, body, boundary):
        """Parse multipart form data to extract file"""
        try:
            boundary_bytes = boundary.encode('utf-8')
            parts = body.split(b'--' + boundary_bytes)
            
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Find the start of file data (after headers)
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        file_data = part[header_end + 4:]
                        # Remove trailing boundary markers
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                        return file_data
            
            return None
        except Exception as e:
            print(f"❌ Erro ao parsear multipart data: {e}")
            return None
    
    def process_excel_import(self, file_data):
        """Process Excel file and import employees"""
        try:
            # Try to import pandas and openpyxl
            try:
                import pandas as pd
                import io
                EXCEL_AVAILABLE = True
            except ImportError:
                EXCEL_AVAILABLE = False
            
            if not EXCEL_AVAILABLE:
                return {
                    "error": "Bibliotecas necessárias não instaladas. Execute: pip install pandas openpyxl",
                    "imported": 0,
                    "errors": []
                }
            
            # Read Excel file
            excel_file = io.BytesIO(file_data)
            df = pd.read_excel(excel_file)
            
            # Validate required columns
            required_columns = ['unique_id', 'full_name', 'cpf', 'phone_number']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    "error": f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}",
                    "imported": 0,
                    "errors": []
                }
            
            # Process each row
            imported = 0
            errors = []
            
            if SessionLocal:
                from sqlalchemy import text
                db = SessionLocal()
                
                try:
                    for index, row in df.iterrows():
                        try:
                            # Validate required fields
                            unique_id = str(row['unique_id']).strip()
                            full_name = str(row['full_name']).strip()
                            cpf = str(row['cpf']).strip()
                            phone_number = str(row['phone_number']).strip()
                            
                            if not unique_id or not full_name or not cpf or not phone_number:
                                errors.append(f"Linha {index + 2}: Campos obrigatórios em branco")
                                continue
                            
                            # Optional fields
                            email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else ''
                            department = str(row.get('department', '')).strip() if pd.notna(row.get('department')) else ''
                            position = str(row.get('position', '')).strip() if pd.notna(row.get('position')) else ''
                            
                            # Check if employee already exists
                            existing = db.execute(text("""
                                SELECT id FROM employees WHERE unique_id = :unique_id AND is_active = true
                            """), {"unique_id": unique_id}).fetchone()
                            
                            if existing:
                                errors.append(f"Linha {index + 2}: ID {unique_id} já existe")
                                continue
                            
                            # Check if CPF already exists
                            existing_cpf = db.execute(text("""
                                SELECT id FROM employees WHERE cpf = :cpf AND is_active = true
                            """), {"cpf": cpf}).fetchone()
                            
                            if existing_cpf:
                                errors.append(f"Linha {index + 2}: CPF {cpf} já existe")
                                continue
                            
                            # Insert new employee
                            db.execute(text("""
                                INSERT INTO employees (unique_id, name, cpf, phone, email, department, position, is_active, created_by, created_at, updated_at)
                                VALUES (:unique_id, :name, :cpf, :phone, :email, :department, :position, true, 3, NOW(), NOW())
                            """), {
                                "unique_id": unique_id,
                                "name": full_name,
                                "cpf": cpf,
                                "phone": phone_number,
                                "email": email,
                                "department": department,
                                "position": position
                            })
                            
                            imported += 1
                            
                        except Exception as row_error:
                            errors.append(f"Linha {index + 2}: {str(row_error)}")
                    
                    db.commit()
                    
                    # Reload global data
                    global employees_data
                    employees_data = load_employees_data()
                    
                finally:
                    db.close()
            
            else:
                return {
                    "error": "PostgreSQL não disponível",
                    "imported": 0,
                    "errors": []
                }
            
            return {
                "message": f"Importação concluída: {imported} funcionários importados",
                "imported": imported,
                "errors": errors
            }
            
        except Exception as e:
            print(f"❌ Erro ao processar Excel: {e}")
            return {
                "error": f"Erro ao processar arquivo Excel: {str(e)}",
                "imported": 0,
                "errors": []
            }

    def handle_bulk_delete_employees(self):
        """Handle bulk deletion of employees"""
        try:
            data = self.get_request_data()
            employee_ids = data.get('employee_ids', [])
            
            if not employee_ids:
                self.send_json_response({"error": "Nenhum funcionário selecionado"}, 400)
                return
            
            if not isinstance(employee_ids, list):
                self.send_json_response({"error": "employee_ids deve ser uma lista"}, 400)
                return
            
            if SessionLocal:
                from sqlalchemy import text
                db = SessionLocal()
                
                try:
                    # Soft delete (marcar como inativo)
                    placeholders = ','.join([':id' + str(i) for i in range(len(employee_ids))])
                    params = {f'id{i}': emp_id for i, emp_id in enumerate(employee_ids)}
                    
                    result = db.execute(text(f"""
                        UPDATE employees 
                        SET is_active = false, updated_at = NOW()
                        WHERE id IN ({placeholders}) AND is_active = true
                    """), params)
                    
                    deleted_count = result.rowcount
                    db.commit()
                    db.close()
                    
                    # Recarregar dados globais
                    global employees_data
                    employees_data = load_employees_data()
                    
                    self.send_json_response({
                        "message": f"{deleted_count} funcionários removidos com sucesso",
                        "deleted_count": deleted_count
                    }, 200)
                    print(f"✅ {deleted_count} funcionários marcados como inativos em lote!")
                    
                except Exception as e:
                    db.rollback()
                    db.close()
                    raise e
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar funcionários em lote: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_bulk_update_employees(self):
        """Handle bulk update of employees"""
        try:
            data = self.get_request_data()
            employee_ids = data.get('employee_ids', [])
            updates = data.get('updates', {})
            
            if not employee_ids:
                self.send_json_response({"error": "Nenhum funcionário selecionado"}, 400)
                return
            
            if not isinstance(employee_ids, list):
                self.send_json_response({"error": "employee_ids deve ser uma lista"}, 400)
                return
                
            if not updates:
                self.send_json_response({"error": "Nenhum campo para atualizar fornecido"}, 400)
                return
            
            # Validar campos permitidos para atualização em lote
            allowed_fields = ['department', 'position']
            update_fields = []
            params = {}
            
            for field, value in updates.items():
                if field in allowed_fields and value.strip():
                    update_fields.append(f"{field} = :{field}")
                    params[field] = value.strip()
            
            if not update_fields:
                self.send_json_response({"error": "Nenhum campo válido para atualizar"}, 400)
                return
            
            if SessionLocal:
                from sqlalchemy import text
                db = SessionLocal()
                
                try:
                    # Atualizar funcionários em lote
                    placeholders = ','.join([':id' + str(i) for i in range(len(employee_ids))])
                    id_params = {f'id{i}': emp_id for i, emp_id in enumerate(employee_ids)}
                    params.update(id_params)
                    params['updated_at'] = 'NOW()'
                    
                    set_clause = ', '.join(update_fields) + ', updated_at = NOW()'
                    
                    result = db.execute(text(f"""
                        UPDATE employees 
                        SET {set_clause}
                        WHERE id IN ({placeholders}) AND is_active = true
                    """), params)
                    
                    updated_count = result.rowcount
                    db.commit()
                    db.close()
                    
                    # Recarregar dados globais
                    global employees_data
                    employees_data = load_employees_data()
                    
                    self.send_json_response({
                        "message": f"{updated_count} funcionários atualizados com sucesso",
                        "updated_count": updated_count,
                        "updates": updates
                    }, 200)
                    print(f"✅ {updated_count} funcionários atualizados em lote!")
                    
                except Exception as e:
                    db.rollback()
                    db.close()
                    raise e
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao atualizar funcionários em lote: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_users_list(self):
        """Lista todos os usuários do sistema"""
        try:
            if SessionLocal:
                from app.services.user_management import UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                # Inicializar sistema de permissões se necessário
                user_service.initialize_system()
                
                users = user_service.get_all_users()
                db.close()
                
                self.send_json_response({
                    "users": users,
                    "total": len(users)
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar usuários: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_available_permissions(self):
        """Lista todas as permissões disponíveis"""
        try:
            if SessionLocal:
                from app.services.user_management import UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                # Inicializar sistema de permissões se necessário
                user_service.initialize_system()
                
                permissions = user_service.get_available_permissions()
                db.close()
                
                self.send_json_response({
                    "permissions": permissions,
                    "modules": list(permissions.keys())
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar permissões: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_create_user(self):
        """Criar novo usuário"""
        try:
            data = self.get_request_data()
            print(f"📝 Criando usuário: {data.get('username')}")
            
            if SessionLocal:
                from app.services.user_management import UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                result = user_service.create_user(data)
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 201)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao criar usuário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_update_user_permissions(self):
        """Atualizar permissões de usuário"""
        try:
            data = self.get_request_data()
            user_id = data.get('user_id')
            permissions = data.get('permissions', [])
            
            print(f"📝 Atualizando permissões do usuário {user_id}")
            
            if SessionLocal:
                from app.services.user_management import UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                result = user_service.update_user_permissions(user_id, permissions)
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 200)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao atualizar permissões: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_update_user(self, user_id):
        """Atualizar dados de usuário"""
        try:
            data = self.get_request_data()
            print(f"📝 Atualizando usuário {user_id}: {data}")
            
            if SessionLocal:
                from app.services.user_management import UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                # Buscar usuário existente
                user = user_service.get_user_by_id(int(user_id))
                if not user:
                    db.close()
                    self.send_json_response({"error": "Usuário não encontrado"}, 404)
                    return
                
                # Atualizar campos
                update_data = {}
                if 'username' in data:
                    update_data['username'] = data['username']
                if 'email' in data:
                    update_data['email'] = data['email']
                if 'password' in data and data['password']:
                    from app.core.auth import get_password_hash
                    update_data['password'] = get_password_hash(data['password'])
                if 'is_active' in data:
                    update_data['is_active'] = data['is_active']
                
                result = user_service.update_user(int(user_id), update_data)
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 200)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao atualizar usuário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_delete_user(self, user_id):
        """Deletar usuário"""
        try:
            print(f"🗑️ Deletando usuário {user_id}")
            
            if SessionLocal:
                from app.services.user_management import UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                # Verificar se usuário existe
                user = user_service.get_user_by_id(int(user_id))
                if not user:
                    db.close()
                    self.send_json_response({"error": "Usuário não encontrado"}, 404)
                    return
                
                # Não permitir deletar o último admin
                if user.username == 'admin':
                    db.close()
                    self.send_json_response({"error": "Não é possível deletar o usuário admin principal"}, 400)
                    return
                
                result = user_service.delete_user(int(user_id))
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 200)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar usuário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_payroll_periods_list(self):
        """Lista períodos de folha de pagamento"""
        try:
            if SessionLocal:
                from app.models.payroll import PayrollPeriod
                
                db = SessionLocal()
                periods = db.query(PayrollPeriod).filter(PayrollPeriod.is_active == True).order_by(
                    PayrollPeriod.year.desc(), PayrollPeriod.month.desc()
                ).all()
                
                periods_data = []
                for period in periods:
                    periods_data.append({
                        "id": period.id,
                        "year": period.year,
                        "month": period.month,
                        "period_name": period.period_name,
                        "description": period.description,
                        "is_closed": period.is_closed,
                        "created_at": period.created_at.isoformat() if hasattr(period, 'created_at') else None
                    })
                
                db.close()
                self.send_json_response({"periods": periods_data, "total": len(periods_data)})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar períodos: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_payroll_templates_list(self):
        """Lista templates de folha de pagamento"""
        try:
            if SessionLocal:
                from app.models.payroll import PayrollTemplate
                
                db = SessionLocal()
                templates = db.query(PayrollTemplate).filter(PayrollTemplate.is_active == True).all()
                
                templates_data = []
                for template in templates:
                    templates_data.append({
                        "id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "column_mapping": template.column_mapping,
                        "is_default": template.is_default,
                        "created_at": template.created_at.isoformat() if hasattr(template, 'created_at') else None
                    })
                
                db.close()
                self.send_json_response({"templates": templates_data, "total": len(templates_data)})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar templates: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_payroll_period_summary(self, period_id: str):
        """Retorna resumo de um período de folha de pagamento"""
        try:
            if SessionLocal:
                from app.services.payroll_processing import PayrollProcessingService
                
                db = SessionLocal()
                payroll_service = PayrollProcessingService(db)
                
                result = payroll_service.get_payroll_summary(int(period_id))
                db.close()
                
                if result["success"]:
                    self.send_json_response(result)
                else:
                    self.send_json_response({"error": result["message"]}, 404)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao obter resumo do período: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_create_payroll_period(self):
        """Criar novo período de folha de pagamento"""
        try:
            data = self.get_request_data()
            print(f"📝 Criando período: {data.get('period_name')}")
            
            if SessionLocal:
                from app.services.payroll_processing import PayrollProcessingService
                
                db = SessionLocal()
                payroll_service = PayrollProcessingService(db)
                
                result = payroll_service.create_period(
                    year=data["year"],
                    month=data["month"],
                    period_name=data["period_name"],
                    description=data.get("description")
                )
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 201)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao criar período: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_create_payroll_template(self):
        """Criar novo template de folha de pagamento"""
        try:
            data = self.get_request_data()
            print(f"📝 Criando template: {data.get('name')}")
            
            if SessionLocal:
                from app.services.payroll_processing import PayrollProcessingService
                
                db = SessionLocal()
                payroll_service = PayrollProcessingService(db)
                
                result = payroll_service.create_template(data)
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 201)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao criar template: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_process_payroll_file(self):
        """Processar arquivo de folha de pagamento"""
        try:
            # Este endpoint será implementado quando tivermos upload de arquivos
            # Por enquanto, retornar não implementado
            self.send_json_response({
                "error": "Funcionalidade de upload não implementada ainda",
                "message": "Use a interface de upload de arquivos"
            }, 501)
                
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_system_status(self):
        """Endpoint para status do sistema"""
        try:
            import time
            uptime = time.time() - start_time if 'start_time' in globals() else 0
            uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"
            
            self.send_json_response({
                "status": "online",
                "uptime": uptime_str,
                "version": "2.0.0",
                "database": "PostgreSQL" if SessionLocal else "JSON",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"❌ Erro ao obter status do sistema: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_evolution_status(self):
        """Endpoint para status da Evolution API"""
        try:
            # Verificar se as variáveis de ambiente estão configuradas
            evolution_url = os.getenv('EVOLUTION_SERVER_URL')
            evolution_key = os.getenv('EVOLUTION_API_KEY')
            evolution_instance = os.getenv('EVOLUTION_INSTANCE_NAME')
            
            if not all([evolution_url, evolution_key, evolution_instance]):
                self.send_json_response({
                    "connected": False,
                    "message": "Evolution API não configurada",
                    "instance": evolution_instance or "N/A"
                })
                return
            
            # Tentar verificar conexão com a Evolution API
            try:
                import requests
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                headers = {
                    'apikey': evolution_key,
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(
                    f"{evolution_url}/instance/fetchInstances",
                    headers=headers,
                    timeout=5,
                    verify=False
                )
                
                if response.status_code == 200:
                    self.send_json_response({
                        "connected": True,
                        "message": "Evolution API conectada",
                        "instance": evolution_instance
                    })
                else:
                    self.send_json_response({
                        "connected": False,
                        "message": f"Erro de conexão: {response.status_code}",
                        "instance": evolution_instance
                    })
                    
            except requests.exceptions.RequestException as e:
                self.send_json_response({
                    "connected": False,
                    "message": f"Erro de rede: {str(e)}",
                    "instance": evolution_instance
                })
                
        except Exception as e:
            print(f"❌ Erro ao verificar Evolution API: {e}")
            self.send_json_response({
                "connected": False,
                "message": f"Erro interno: {str(e)}",
                "instance": "N/A"
            })

    def handle_database_health(self):
        """Endpoint para health check do banco de dados"""
        try:
            if SessionLocal:
                from sqlalchemy import text
                db = SessionLocal()
                try:
                    # Testar conexão com uma query simples
                    result = db.execute(text("SELECT version();"))
                    version = result.fetchone()[0]
                    
                    self.send_json_response({
                        "connected": True,
                        "type": "PostgreSQL",
                        "version": version,
                        "status": "online"
                    })
                except Exception as e:
                    self.send_json_response({
                        "connected": False,
                        "type": "PostgreSQL",
                        "error": str(e),
                        "status": "offline"
                    })
                finally:
                    db.close()
            else:
                self.send_json_response({
                    "connected": True,
                    "type": "JSON Fallback",
                    "status": "online",
                    "message": "Usando armazenamento JSON local"
                })
                
        except Exception as e:
            print(f"❌ Erro ao verificar saúde do banco: {e}")
            self.send_json_response({
                "connected": False,
                "error": str(e),
                "status": "error"
            })

if __name__ == "__main__":
    import time
    start_time = time.time()  # Para calcular uptime
    
    PORT = int(os.getenv('PORT', 8002))  # Usar porta 8002 como padrão
    
    print("=" * 60)
    print("🚀 Sistema de Envio RH v2.0 - PostgreSQL Edition (Corrigido)")
    print("=" * 60)
    print(f"📡 Servidor iniciando na porta {PORT}")
    print(f"🗄️  Banco de dados: {'PostgreSQL' if SessionLocal else 'JSON (fallback)'}")
    print(f"👥 Funcionários carregados: {len(employees_data.get('employees', []))}")
    print(f"🔗 Acesse: http://localhost:{PORT}")
    print("=" * 60)
    
    with socketserver.TCPServer(("", PORT), EnviaFolhaHandler) as httpd:
        print(f"✅ Servidor rodando em http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Servidor finalizado pelo usuário")
            if db_engine:
                db_engine.dispose()
                print("🔌 Conexão com PostgreSQL encerrada")