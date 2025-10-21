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
            return {
                "status": "error", 
                "message": "Engine do banco não inicializada",
                "connected": False,
                "type": "None",
                "version": "N/A"
            }
        
        # Importar SQLAlchemy text
        from sqlalchemy import text
        
        # Testar conexão e obter versão
        with db_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            
            return {
                "status": "online", 
                "message": "Banco de dados PostgreSQL está online",
                "connected": True,
                "type": "PostgreSQL",
                "version": version.split(',')[0] if ',' in version else version
            }
            
    except Exception as e:
        return {
            "status": "offline", 
            "message": f"Banco de dados offline: {str(e)}",
            "connected": False,
            "type": "PostgreSQL",
            "version": "N/A"
        }

def setup_database():
    """Configura conexão com PostgreSQL e cria tabelas se necessário"""
    try:
        # Importações SQLAlchemy
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Usar DATABASE_URL do .env ou padrão
        database_url = os.getenv('DATABASE_URL', 'postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db')
        print(f"🔌 Conectando ao PostgreSQL: {database_url}")
        
        # Criar engine com connection pooling otimizado
        engine = create_engine(
            database_url, 
            echo=False,
            pool_size=5,           # Número de conexões mantidas no pool
            max_overflow=10,       # Conexões extras permitidas quando pool está cheio
            pool_timeout=30,       # Timeout para obter conexão do pool
            pool_recycle=3600,     # Reciclar conexões a cada 1 hora
            pool_pre_ping=True     # Verificar conexão antes de usar
        )
        
        # Testar conexão
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conectado ao PostgreSQL: {version}")
        
        # Importar todos os modelos para garantir que estejam registrados
        from app.models import Base, User, Employee, Role, PayrollPeriod, PayrollData, PayrollTemplate, PayrollProcessingLog
        
        # Criar tabelas se não existirem
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas do banco de dados verificadas/criadas")
        
        # Criar sessão com configurações otimizadas
        SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=engine,
            expire_on_commit=False  # Evita queries extras depois do commit
        )
        
        return engine, SessionLocal
        
    except Exception as e:
        print(f"❌ Erro ao conectar com PostgreSQL: {e}")
        print("⚠️  Continuando com armazenamento JSON como fallback...")
        return None, None

# Inicializar banco de dados
db_engine, SessionLocal = setup_database()

# Cache para employees (atualizado a cada 3 minutos)
employees_cache = {
    'data': None,
    'last_update': 0,
    'ttl': 180  # Time to live em segundos (3 minutos)
}

def load_employees_data():
    """Carrega dados dos funcionários do PostgreSQL ou JSON como fallback com cache"""
    global employees_cache
    
    # Verificar se cache é válido
    import time
    current_time = time.time()
    cache_age = current_time - employees_cache['last_update']
    
    if employees_cache['data'] is not None and cache_age < employees_cache['ttl']:
        # Retornar do cache
        print(f"💾 Usando cache de employees (idade: {cache_age:.1f}s)")
        return employees_cache['data']
    
    print(f"🔄 Cache expirado ou inválido, carregando do banco...")
    
    if SessionLocal:
        db = None
        try:
            # Importar models apenas se PostgreSQL disponível
            sys.path.append(os.path.dirname(__file__))
            from app.models import Employee
            
            print("🔌 Abrindo sessão do banco...")
            db = SessionLocal()
            
            print("📊 Executando query para buscar employees...")
            employees = db.query(Employee).filter(Employee.is_active == True).all()
            print(f"✅ Query concluída: {len(employees)} employees encontrados")
            
            # Converter para formato compatível incluindo novos campos
            employees_data = []
            for emp in employees:
                emp_dict = {
                    "id": emp.id,
                    "unique_id": emp.unique_id,
                    "full_name": emp.name,
                    "cpf": emp.cpf,
                    "phone_number": emp.phone,
                    "email": emp.email or "",
                    "department": emp.department or "",
                    "position": emp.position or "",
                    "birth_date": emp.birth_date.isoformat() if emp.birth_date else "",
                    "sex": emp.sex or "",
                    "marital_status": emp.marital_status or "",
                    "admission_date": emp.admission_date.isoformat() if emp.admission_date else "",
                    "contract_type": emp.contract_type or "",
                    "employment_status": emp.employment_status or "Ativo",
                    "termination_date": emp.termination_date.isoformat() if emp.termination_date else "",
                    "leave_start_date": emp.leave_start_date.isoformat() if emp.leave_start_date else "",
                    "leave_end_date": emp.leave_end_date.isoformat() if emp.leave_end_date else "",
                    "status_reason": emp.status_reason or "",
                    "is_active": emp.is_active
                }
                employees_data.append(emp_dict)
            
            print(f"✅ Carregados {len(employees_data)} funcionários do PostgreSQL")
            
            # Atualizar cache
            result = {"employees": employees_data, "users": []}
            employees_cache['data'] = result
            employees_cache['last_update'] = current_time
            
            return result
            
        except Exception as e:
            print(f"❌ Erro ao carregar funcionários do PostgreSQL: {e}")
            import traceback
            traceback.print_exc()
            print("⚠️  Tentando carregar do arquivo JSON...")
            
        finally:
            if db:
                print("🔒 Fechando sessão do banco...")
                db.close()
                print("✅ Sessão fechada com sucesso")
    
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

def invalidate_employees_cache():
    """Invalida o cache de employees forçando reload no próximo acesso"""
    global employees_cache
    employees_cache['data'] = None
    employees_cache['last_update'] = 0
    print("🔄 Cache de funcionários invalidado")

def get_employee_by_id(employee_id):
    """Busca um funcionário específico diretamente do banco (sem carregar todos)"""
    print(f"🔍 get_employee_by_id chamado para ID: {employee_id}")
    
    if SessionLocal:
        db = None
        try:
            from app.models import Employee
            
            print("🔌 Abrindo sessão do banco para buscar employee...")
            db = SessionLocal()
            
            # Tentar buscar por ID numérico primeiro
            try:
                emp_id = int(employee_id)
                print(f"🔢 Tentando buscar por ID numérico: {emp_id}")
                employee = db.query(Employee).filter(Employee.id == emp_id, Employee.is_active == True).first()
            except ValueError:
                print(f"⚠️  Não é ID numérico, tentando por unique_id")
                employee = None
            
            # Se não encontrou por ID, buscar por unique_id
            if not employee:
                print(f"🔍 Buscando por unique_id: {employee_id}")
                employee = db.query(Employee).filter(Employee.unique_id == employee_id, Employee.is_active == True).first()
            
            if not employee:
                print(f"❌ Funcionário {employee_id} não encontrado")
                return None
            
            # Converter para dicionário
            emp_dict = {
                "id": employee.id,
                "unique_id": employee.unique_id,
                "full_name": employee.name,
                "cpf": employee.cpf,
                "phone_number": employee.phone,
                "email": employee.email or "",
                "department": employee.department or "",
                "position": employee.position or "",
                "birth_date": employee.birth_date.isoformat() if employee.birth_date else "",
                "sex": employee.sex or "",
                "marital_status": employee.marital_status or "",
                "admission_date": employee.admission_date.isoformat() if employee.admission_date else "",
                "contract_type": employee.contract_type or "",
                "employment_status": employee.employment_status or "Ativo",
                "termination_date": employee.termination_date.isoformat() if employee.termination_date else "",
                "leave_start_date": employee.leave_start_date.isoformat() if employee.leave_start_date else "",
                "leave_end_date": employee.leave_end_date.isoformat() if employee.leave_end_date else "",
                "status_reason": employee.status_reason or "",
                "is_active": employee.is_active
            }
            
            print(f"✅ Funcionário {employee.name} (ID: {employee.id}) encontrado diretamente no banco")
            return emp_dict
            
        except Exception as e:
            print(f"❌ Erro ao buscar funcionário do PostgreSQL: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            if db:
                print("🔒 Fechando sessão do banco (get_employee_by_id)...")
                db.close()
                print("✅ Sessão fechada")
    
    # Fallback: buscar nos dados carregados
    print("⚠️  PostgreSQL não disponível, usando fallback para dados carregados")
    current_data = load_employees_data()
    employees = current_data.get('employees', [])
    
    for emp in employees:
        if str(emp.get('id')) == str(employee_id) or str(emp.get('unique_id')) == str(employee_id):
            print(f"✅ Funcionário encontrado no fallback: {emp.get('full_name')}")
            return emp
    
    print(f"❌ Funcionário {employee_id} não encontrado no fallback")
    return None

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
                # Atualizar existente - campos básicos
                existing.name = employee_data.get('full_name', existing.name)
                existing.phone = employee_data.get('phone_number', existing.phone)
                existing.email = employee_data.get('email', existing.email)
                existing.department = employee_data.get('department', existing.department)
                existing.position = employee_data.get('position', existing.position)
                existing.is_active = employee_data.get('is_active', existing.is_active)
                
                # Atualizar novos campos RH
                from datetime import datetime
                if employee_data.get('birth_date'):
                    try:
                        existing.birth_date = datetime.strptime(employee_data['birth_date'], '%Y-%m-%d').date()
                    except:
                        pass
                if employee_data.get('sex'):
                    existing.sex = employee_data['sex']
                if employee_data.get('marital_status'):
                    existing.marital_status = employee_data['marital_status']
                if employee_data.get('admission_date'):
                    try:
                        existing.admission_date = datetime.strptime(employee_data['admission_date'], '%Y-%m-%d').date()
                    except:
                        pass
                if employee_data.get('contract_type'):
                    existing.contract_type = employee_data['contract_type']
                if employee_data.get('status_reason'):
                    existing.status_reason = employee_data['status_reason']
            else:
                # Criar novo - preparar campos de data
                from datetime import datetime
                birth_date_obj = None
                admission_date_obj = None
                
                if employee_data.get('birth_date'):
                    try:
                        birth_date_obj = datetime.strptime(employee_data['birth_date'], '%Y-%m-%d').date()
                    except:
                        pass
                
                if employee_data.get('admission_date'):
                    try:
                        admission_date_obj = datetime.strptime(employee_data['admission_date'], '%Y-%m-%d').date()
                    except:
                        pass
                
                new_employee = Employee(
                    unique_id=employee_data.get('unique_id'),
                    name=employee_data.get('full_name'),
                    cpf=employee_data.get('unique_id', '000.000.000-00'),
                    phone=employee_data.get('phone_number'),
                    email=employee_data.get('email'),
                    department=employee_data.get('department'),
                    position=employee_data.get('position'),
                    birth_date=birth_date_obj,
                    sex=employee_data.get('sex'),
                    marital_status=employee_data.get('marital_status'),
                    admission_date=admission_date_obj,
                    contract_type=employee_data.get('contract_type'),
                    status_reason=employee_data.get('status_reason'),
                    is_active=employee_data.get('is_active', True),
                    created_by=created_by_user_id
                )
                db.add(new_employee)
            
            db.commit()
            db.close()
            print(f"✅ Funcionário {employee_data.get('full_name')} salvo no PostgreSQL")
            
            # Invalidar cache para forçar reload
            invalidate_employees_cache()
            
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
        elif path == '/api/v1/roles':
            self.handle_roles_list()
        elif path == '/api/v1/users/permissions':
            self.handle_available_permissions()
        
        elif path == '/api/v1/payroll/periods':
            self.handle_payroll_periods_list()
        elif path == '/api/v1/payroll/templates':
            self.handle_payroll_templates_list()
        elif path.startswith('/api/v1/payroll/periods/'):
            period_id = path.split('/')[-1]
            self.handle_payroll_period_summary(period_id)
        elif path.startswith('/api/v1/employees/'):
            # IMPORTANTE: Esta rota deve vir ANTES de '/api/v1/employees'
            employee_id = path.split('/')[-1]
            print(f"🔍 Rota de detalhes capturada para employee_id: {employee_id}")
            self.send_employee_detail(employee_id)
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
        elif path == '/api/v1/system/logs':
            self.handle_system_logs()
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
        elif path == '/api/v1/employees/import' or path == '/api/v1/import/employees':
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
        print(f"🗑️ DELETE recebido: {path}")
        
        if path.startswith('/api/v1/employees/'):
            employee_id = path.split('/')[-1]
            self.handle_delete_employee(employee_id)
        elif path.startswith('/api/v1/users/'):
            user_id = path.split('/')[-1]
            self.handle_delete_user(user_id)
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
        
        print(f"🔐 Tentativa de login - Username: '{username}'")
        
        # Verificar no PostgreSQL se disponível
        if SessionLocal:
            try:
                sys.path.append(os.path.dirname(__file__))
                from app.models import User
                
                db = SessionLocal()
                user = db.query(User).filter(User.username == username).first()
                
                if user and user.is_active and user.verify_password(password):
                    # Atualizar o último acesso com timezone brasileiro
                    from datetime import datetime, timezone, timedelta
                    from app.core.auth import create_access_token
                    
                    brazil_tz = timezone(timedelta(hours=-3))  # GMT-3 (Brasília)
                    user.last_login = datetime.now(brazil_tz)
                    db.commit()
                    
                    # Gerar JWT token real
                    access_token = create_access_token(data={"sub": user.username})
                    
                    print("✅ Login bem-sucedido com PostgreSQL!")
                    self.send_json_response({
                        "access_token": access_token,
                        "token_type": "bearer",
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "full_name": user.full_name,
                            "email": user.email,
                            "is_admin": user.is_admin,
                            "role": user.role.name if user.role else None
                        }
                    })
                    db.close()
                    return
                else:
                    if user and not user.is_active:
                        print("❌ Usuário inativo no PostgreSQL!")
                        db.close()
                        self.send_json_response({"detail": "Usuário inativo ou removido"}, 401)
                        return
                    else:
                        print("❌ Credenciais inválidas no PostgreSQL!")
                        db.close()
                        self.send_json_response({"detail": "Credenciais inválidas"}, 401)
                        return
                    
            except Exception as e:
                print(f"❌ Erro na autenticação PostgreSQL: {e}")
                if 'db' in locals():
                    db.close()
        
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
            print(f"🔍 Buscando detalhes do funcionário: {employee_id}")
            
            # Buscar funcionário diretamente do banco (otimizado)
            employee = get_employee_by_id(employee_id)
            
            if employee:
                print(f"✅ Funcionário encontrado: {employee.get('full_name')}")
                self.send_json_response(employee)
            else:
                print(f"❌ Funcionário {employee_id} não encontrado")
                self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                
        except Exception as e:
            print(f"❌ Erro ao buscar funcionário: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro ao buscar funcionário: {str(e)}"}, 500)
    
    def get_authenticated_user(self, db=None):
        """Extrai e valida usuário autenticado do token JWT"""
        from app.core.auth import verify_token
        from app.models.user import User
        
        auth_header = self.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        # Extrair token
        token = auth_header.replace('Bearer ', '')
        
        # Validar token
        payload = verify_token(token)
        if not payload:
            return None
        
        username = payload.get('sub')
        if not username:
            return None
        
        # Usar sessão existente ou criar nova
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            user = db.query(User).filter(User.username == username).first()
            return user
        finally:
            if close_db:
                db.close()
    
    def handle_auth_me(self):
        """Endpoint para verificar usuário autenticado"""
        db = SessionLocal()
        try:
            user = self.get_authenticated_user(db)
            
            if not user:
                self.send_json_response({"detail": "Token de acesso necessário"}, 401)
                return
            
            # Retornar dados do usuário
            user_data = {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "is_admin": user.is_admin,
                "role": user.role
            }
            self.send_json_response(user_data)
        finally:
            db.close()
    
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
            
            # Preparar dados do funcionário (campos básicos + novos campos RH)
            employee_data = {
                "unique_id": data.get('unique_id'),
                "full_name": data.get('full_name'),
                "phone_number": data.get('phone_number'),
                "email": data.get('email', ''),
                "department": data.get('department', ''),
                "position": data.get('position', ''),
                "birth_date": data.get('birth_date', ''),
                "sex": data.get('sex', ''),
                "marital_status": data.get('marital_status', ''),
                "admission_date": data.get('admission_date', ''),
                "contract_type": data.get('contract_type', ''),
                "status_reason": data.get('status_reason', ''),
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
                
                # Atualizar campos básicos
                if 'unique_id' in data:
                    employee.unique_id = data['unique_id']
                if 'full_name' in data:
                    employee.name = data['full_name']
                if 'cpf' in data:
                    employee.cpf = data['cpf']
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
                
                # Atualizar novos campos de métricas RH
                if 'birth_date' in data:
                    from datetime import datetime
                    if data['birth_date']:
                        try:
                            employee.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
                        except:
                            employee.birth_date = None
                    else:
                        employee.birth_date = None
                
                if 'sex' in data:
                    employee.sex = data['sex'] or None
                
                if 'marital_status' in data:
                    employee.marital_status = data['marital_status'] or None
                
                if 'admission_date' in data:
                    from datetime import datetime
                    if data['admission_date']:
                        try:
                            employee.admission_date = datetime.strptime(data['admission_date'], '%Y-%m-%d').date()
                        except:
                            employee.admission_date = None
                    else:
                        employee.admission_date = None
                
                if 'contract_type' in data:
                    employee.contract_type = data['contract_type'] or None
                
                if 'status_reason' in data:
                    employee.status_reason = data['status_reason'] or None
                
                # Atualizar campos de status
                if 'employment_status' in data:
                    employee.employment_status = data['employment_status'] or 'Ativo'
                
                if 'termination_date' in data:
                    from datetime import datetime
                    if data['termination_date']:
                        try:
                            employee.termination_date = datetime.strptime(data['termination_date'], '%Y-%m-%d').date()
                        except:
                            employee.termination_date = None
                    else:
                        employee.termination_date = None
                
                if 'leave_start_date' in data:
                    from datetime import datetime
                    if data['leave_start_date']:
                        try:
                            employee.leave_start_date = datetime.strptime(data['leave_start_date'], '%Y-%m-%d').date()
                        except:
                            employee.leave_start_date = None
                    else:
                        employee.leave_start_date = None
                
                if 'leave_end_date' in data:
                    from datetime import datetime
                    if data['leave_end_date']:
                        try:
                            employee.leave_end_date = datetime.strptime(data['leave_end_date'], '%Y-%m-%d').date()
                        except:
                            employee.leave_end_date = None
                    else:
                        employee.leave_end_date = None
                
                db.commit()
                
                # Preparar resposta com todos os campos
                updated_employee = {
                    "id": employee.id,
                    "unique_id": employee.unique_id,
                    "full_name": employee.name,
                    "cpf": employee.cpf,
                    "phone_number": employee.phone,
                    "email": employee.email or "",
                    "department": employee.department or "",
                    "position": employee.position or "",
                    "is_active": employee.is_active,
                    "birth_date": employee.birth_date.isoformat() if employee.birth_date else None,
                    "sex": employee.sex or "",
                    "marital_status": employee.marital_status or "",
                    "admission_date": employee.admission_date.isoformat() if employee.admission_date else None,
                    "contract_type": employee.contract_type or "",
                    "employment_status": employee.employment_status or "Ativo",
                    "termination_date": employee.termination_date.isoformat() if employee.termination_date else None,
                    "leave_start_date": employee.leave_start_date.isoformat() if employee.leave_start_date else None,
                    "leave_end_date": employee.leave_end_date.isoformat() if employee.leave_end_date else None,
                    "status_reason": employee.status_reason or ""
                }
                
                db.close()
                
                # Invalidar cache para forçar reload
                invalidate_employees_cache()
                
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
                
                # Invalidar cache para forçar reload
                invalidate_employees_cache()
                
                self.send_json_response({"message": f"Funcionário {employee_name} removido com sucesso"}, 200)
                print(f"✅ Funcionário {employee_name} marcado como inativo!")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar funcionário: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_import_employees(self):
        """Handle CSV/XLSX file import for employees using DataImportService"""
        try:
            print("🔥 handle_import_employees chamado")
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            print(f"Content-Type recebido: {content_type}")
            
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
            
            print(f"Body recebido: {len(body)} bytes")
            
            # Parse multipart data
            file_data, filename = self.parse_multipart_data(body, boundary)
            
            if not file_data:
                self.send_json_response({"error": "Arquivo não encontrado no upload"}, 400)
                return
            
            print(f"Arquivo recebido: {filename}, {len(file_data)} bytes")
            
            # Import using DataImportService
            from app.services.data_import import DataImportService
            
            db = SessionLocal()
            try:
                # Obter usuário autenticado usando a mesma sessão do banco
                authenticated_user = self.get_authenticated_user(db)
                if not authenticated_user:
                    self.send_json_response({"error": "Usuário não autenticado"}, 401)
                    return
                
                print(f"👤 Usuário autenticado: {authenticated_user.username} (ID: {authenticated_user.id})")
                
                # Extrair dados da requisição HTTP
                ip_address = self.headers.get('X-Forwarded-For', self.client_address[0] if self.client_address else None)
                user_agent = self.headers.get('User-Agent')
                request_method = self.command
                request_path = self.path
                
                print("📦 Criando DataImportService...")
                import_service = DataImportService(
                    db, 
                    user_id=authenticated_user.id, 
                    username=authenticated_user.username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=request_method,
                    request_path=request_path
                )
                
                print(f"📂 Tipo de arquivo: {filename}")
                
                # Determine file type and parse
                if filename.endswith('.csv'):
                    print("📄 Parseando CSV...")
                    rows = import_service.parse_csv(file_data)
                elif filename.endswith(('.xlsx', '.xls')):
                    print("📊 Parseando XLSX...")
                    rows = import_service.parse_xlsx(file_data)
                    print(f"✅ Parse XLSX concluído: {len(rows)} linhas")
                else:
                    self.send_json_response({
                        "error": "Formato de arquivo não suportado. Use CSV ou XLSX."
                    }, 400)
                    return
                
                print(f"📋 Linhas parseadas: {len(rows)}")
                print(f"📋 Primeiras 2 linhas: {rows[:2] if len(rows) > 0 else 'nenhuma'}")
                
                # Import employees
                print("🚀 Iniciando importação de employees...")
                result = import_service.import_employees(rows)
                
                print(f"✅ Resultado da importação: {result}")
                
                # Invalidar cache após importação bem-sucedida
                if result['created'] > 0 or result['updated'] > 0:
                    print("🔄 Invalidando cache de employees...")
                    invalidate_employees_cache()
                
                self.send_json_response({
                    "success": True,
                    "imported_count": result['created'],
                    "updated_count": result['updated'],
                    "created_list": result.get('created_list', []),
                    "updated_list": result.get('updated_list', []),
                    "errors": result['errors']
                }, 200)
                
            finally:
                db.close()
            
        except Exception as e:
            print(f"❌ Erro ao importar funcionários: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }, 500)
    
    def parse_multipart_data(self, body, boundary):
        """Parse multipart form data to extract file and filename"""
        try:
            boundary_bytes = boundary.encode('utf-8')
            parts = body.split(b'--' + boundary_bytes)
            
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Extract filename
                    disposition_line = part.split(b'\r\n')[0]
                    filename_start = disposition_line.find(b'filename="')
                    if filename_start != -1:
                        filename_start += 10  # len('filename="')
                        filename_end = disposition_line.find(b'"', filename_start)
                        filename = disposition_line[filename_start:filename_end].decode('utf-8')
                    else:
                        filename = 'unknown.xlsx'
                    
                    # Find the start of file data (after headers)
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        file_data = part[header_end + 4:]
                        # Remove trailing boundary markers
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                        return file_data, filename
            
            return None, None
        except Exception as e:
            print(f"❌ Erro ao parsear multipart data: {e}")
            return None, None
    
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
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
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
    
    def handle_roles_list(self):
        """Lista todos os roles disponíveis"""
        try:
            if SessionLocal:
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                roles = user_service.get_all_roles()
                db.close()
                
                self.send_json_response(roles)
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar roles: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_available_permissions(self):
        """Lista todas as permissões disponíveis"""
        try:
            if SessionLocal:
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
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

    def handle_import_employees(self):
        """Import employees from uploaded CSV/XLSX (admin only)"""
        try:
            # minimal auth check: ensure user is admin
            # TODO: integrate with full auth
            # parse multipart/form-data (simple fallback to raw body assuming file bytes)
            file_bytes = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            if not file_bytes:
                self.send_json_response({"error": "No file uploaded"}, 400)
                return

            from app.services.data_import import DataImportService
            if SessionLocal:
                db = SessionLocal()
                importer = DataImportService(db)
                # try parse as CSV first
                try:
                    rows = importer.parse_csv(file_bytes)
                except Exception:
                    # try xlsx
                    rows = importer.parse_xlsx(file_bytes)

                result = importer.import_employees(rows)
                db.close()
                self.send_json_response(result, 200)
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)

        except Exception as e:
            print(f"❌ Erro ao importar funcionários: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
                
    
    def handle_create_user(self):
        """Criar novo usuário"""
        try:
            data = self.get_request_data()
            print(f"📝 Criando usuário: {data.get('username')}")
            
            if SessionLocal:
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                result = user_service.create_user(data)
                print(f"Debug create - resultado: {result}")
                print(f"Debug create - tipo: {type(result)}")
                db.close()
                
                if isinstance(result, dict) and result.get("success"):
                    self.send_json_response(result, 201)
                else:
                    if isinstance(result, dict):
                        self.send_json_response(result, 400)
                    else:
                        self.send_json_response({"error": f"Resposta inesperada: {result}"}, 500)
                    
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
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
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
        print(f"📝 Iniciando atualização do usuário {user_id}")
        try:
            data = self.get_request_data()
            print(f"📝 Dados recebidos: {data}")
            print(f"📝 Atualizando usuário {user_id}: {data}")
            
            if SessionLocal:
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
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
                if 'full_name' in data:
                    update_data['full_name'] = data['full_name']
                if 'password' in data and data['password']:
                    from app.core.auth import get_password_hash
                    update_data['password_hash'] = get_password_hash(data['password'])
                if 'is_active' in data:
                    update_data['is_active'] = data['is_active']
                if 'is_admin' in data:
                    update_data['is_admin'] = data['is_admin']
                if 'role_id' in data and data['role_id']:
                    update_data['role_id'] = int(data['role_id'])
                
                result = user_service.update_user(int(user_id), update_data)
                print(f"Debug - resultado update_user: {result}")
                print(f"Debug - tipo do resultado: {type(result)}")
                db.close()
                
                if isinstance(result, dict) and result.get("success"):
                    self.send_json_response(result, 200)
                else:
                    if isinstance(result, dict):
                        self.send_json_response(result, 400)
                    else:
                        self.send_json_response({"error": f"Resposta inesperada: {result}"}, 500)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao atualizar usuário: {e}")
            print(f"❌ Tipo do erro: {type(e)}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_delete_user(self, user_id):
        """Deletar usuário"""
        print(f"🗑️ Iniciando exclusão do usuário {user_id}")
        try:
            print(f"🗑️ Deletando usuário {user_id}")
            
            if SessionLocal:
                from app.services.user_management_simple import UserManagementServiceSimple as UserManagementService
                
                db = SessionLocal()
                user_service = UserManagementService(db)
                
                # Verificar se usuário existe
                user = user_service.get_user_by_id(int(user_id))
                print(f"🗑️ Usuário encontrado: {user}")
                if not user:
                    db.close()
                    self.send_json_response({"error": "Usuário não encontrado"}, 404)
                    return
                
                # Não permitir deletar o último admin
                if user.get("username") == 'admin':
                    db.close()
                    self.send_json_response({"error": "Não é possível deletar o usuário admin principal"}, 400)
                    return
                
                result = user_service.delete_user(int(user_id))
                print(f"🗑️ Resultado delete: {result}")
                db.close()
                
                if result["success"]:
                    self.send_json_response(result, 200)
                else:
                    self.send_json_response(result, 400)
                    
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar usuário: {e}")
            print(f"❌ Tipo do erro: {type(e)}")
            import traceback
            traceback.print_exc()
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

    def handle_system_logs(self):
        """Endpoint para listar logs do sistema"""
        db = SessionLocal()
        try:
            from app.services.logging_service import LoggingService
            
            # Verificar autenticação com a mesma sessão do banco
            authenticated_user = self.get_authenticated_user(db)
            if not authenticated_user:
                self.send_json_response({"error": "Usuário não autenticado"}, 401)
                return
            
            # Parse query parameters
            parsed = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # Filtros opcionais
            level = query_params.get('level', [None])[0]
            category = query_params.get('category', [None])[0]
            user_id = query_params.get('user_id', [None])[0]
            limit = int(query_params.get('limit', [100])[0])
            offset = int(query_params.get('offset', [0])[0])
            
            # Buscar logs usando a mesma sessão
            logger = LoggingService(db)
            logs_data = logger.get_logs(
                level=level,
                category=category,
                user_id=int(user_id) if user_id else None,
                limit=limit,
                offset=offset
            )
            
            # get_logs já retorna lista de dicionários
            self.send_json_response({
                "logs": logs_data,
                "total": len(logs_data),
                "limit": limit,
                "offset": offset
            })
        except Exception as e:
            print(f"❌ Erro ao buscar logs: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro ao buscar logs: {str(e)}"}, 500)
        finally:
            db.close()


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
