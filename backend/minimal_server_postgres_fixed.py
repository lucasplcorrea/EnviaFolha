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

def save_employee_to_db(employee_data):
    """Salva funcionário no PostgreSQL ou JSON como fallback"""
    if SessionLocal:
        try:
            from app.models import Employee
            
            db = SessionLocal()
            
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
                    created_by=1
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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
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
    
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            self.send_status_response()
        elif path == '/health':
            self.send_health_check()
        elif path == '/api/v1/employees':
            self.send_employees_list()
        elif path == '/api/v1/auth/me':
            self.handle_auth_me()
        elif path == '/api/v1/dashboard/stats':
            self.handle_dashboard_stats()
        elif path == '/api/v1/evolution/status':
            self.handle_evolution_status()
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
        health_status = {
            "status": "healthy",
            "database": "connected" if SessionLocal else "json_fallback",
            "timestamp": datetime.now().isoformat()
        }
        
        self.send_json_response(health_status)
    
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

if __name__ == "__main__":
    PORT = int(os.getenv('PORT', 8003))  # Usar porta diferente para evitar conflito
    
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