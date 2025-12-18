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
        
        # Construir DATABASE_URL a partir de variáveis individuais ou usar padrão
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            # Montar URL a partir de variáveis individuais
            db_user = os.getenv('DB_USER', 'enviafolha_user')
            db_password = os.getenv('DB_PASSWORD', 'secure_password')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'enviafolha_db')
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
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
        from app.models.send_queue import SendQueue, SendQueueItem
        
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

# Função helper para logging simplificado
def log_system_event(event_type: str, description: str, details: dict = None, 
                     severity: str = 'info', user_id: int = None):
    """
    Helper para registrar eventos no banco de dados (system_logs)
    
    Args:
        event_type: Tipo do evento (ex: 'payroll_processing', 'communication_sent')
        description: Descrição do evento
        details: Dicionário com detalhes adicionais
        severity: Nível de severidade ('info', 'warning', 'error', 'debug', 'critical')
        user_id: ID do usuário que executou a ação
    """
    if not SessionLocal:
        # Sem banco de dados, apenas printar
        print(f"[LOG {severity.upper()}] {event_type}: {description}")
        return
    
    try:
        db = SessionLocal()
        try:
            from app.models.system_log import SystemLog, LogLevel, LogCategory
            import json
            
            # Mapear severity string para LogLevel enum
            level_map = {
                'debug': LogLevel.DEBUG,
                'info': LogLevel.INFO,
                'warning': LogLevel.WARNING,
                'error': LogLevel.ERROR,
                'critical': LogLevel.CRITICAL
            }
            level = level_map.get(severity.lower(), LogLevel.INFO)
            
            # Tentar mapear event_type para categoria
            category = LogCategory.SYSTEM  # Default
            if 'auth' in event_type.lower() or 'login' in event_type.lower():
                category = LogCategory.AUTH
            elif 'employee' in event_type.lower():
                category = LogCategory.EMPLOYEE
            elif 'import' in event_type.lower():
                category = LogCategory.IMPORT
            elif 'payroll' in event_type.lower() or 'holerite' in event_type.lower():
                category = LogCategory.PAYROLL
            elif 'communication' in event_type.lower() or 'comunicado' in event_type.lower():
                category = LogCategory.COMMUNICATION
            elif 'whatsapp' in event_type.lower() or 'evolution' in event_type.lower():
                category = LogCategory.WHATSAPP
            
            # Converter details para JSON string se necessário
            details_json = None
            if details:
                try:
                    details_json = json.dumps(details, ensure_ascii=False, default=str)
                except:
                    details_json = str(details)
            
            log_entry = SystemLog(
                level=level,
                category=category,
                message=f"[{event_type}] {description}",
                details=details_json,
                user_id=user_id,
                created_at=datetime.now()
            )
            
            db.add(log_entry)
            db.commit()
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"⚠️ Erro ao registrar log no banco: {e}")
        # Não lançar exceção para não quebrar o fluxo principal

# Cache para employees (atualizado a cada 3 minutos)
employees_cache = {
    'data': None,
    'last_update': 0,
    'ttl': 180  # Time to live em segundos (3 minutos)
}

# ========================================
# GERENCIADOR DE JOBS EM BACKGROUND
# ========================================
import threading
import uuid
from datetime import datetime

bulk_send_jobs = {}
jobs_lock = threading.Lock()

class BulkSendJob:
    """Representa um job de envio em background"""
    def __init__(self, job_id, total_files):
        self.job_id = job_id
        self.status = 'running'  # running, completed, failed
        self.total_files = total_files
        self.processed_files = 0
        self.successful_sends = 0
        self.failed_sends = 0
        self.failed_employees = []
        self.start_time = datetime.now()
        self.end_time = None
        self.error_message = None
        self.current_file = None
    
    def to_dict(self):
        """Converte job para dicionário serializável"""
        elapsed = (self.end_time or datetime.now()) - self.start_time
        return {
            'job_id': self.job_id,
            'status': self.status,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'successful_sends': self.successful_sends,
            'failed_sends': self.failed_sends,
            'failed_employees': self.failed_employees,
            'progress_percentage': round((self.processed_files / self.total_files) * 100, 1) if self.total_files > 0 else 0,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'elapsed_seconds': int(elapsed.total_seconds()),
            'error_message': self.error_message,
            'current_file': self.current_file
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
            
            # Log dos unique_ids para debug
            if employees_data:
                unique_ids_sample = [emp['unique_id'] for emp in employees_data[:5]]
                print(f"📋 Primeiros unique_ids: {unique_ids_sample}")
            
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

def process_bulk_send_in_background(job_id, selected_files, message_templates, user_id):
    """
    Processa envio em lote em background sem bloquear o servidor HTTP.
    Esta função roda em uma thread separada.
    
    SISTEMA ANTI-SOFTBAN AVANÇADO:
    - Delays aleatórios entre 2-3 minutos (120-180s)
    - A cada 20 envios: delay maior de 10-15 minutos (600-900s)
    - Monitoramento da Evolution API (pausa se offline)
    - Suporte para 8 templates randomizados
    """
    import asyncio
    import sys
    import os
    import time
    import random
    from datetime import datetime
    
    print(f"\n🚀 [JOB {job_id[:8]}] Thread iniciada - processando {len(selected_files)} arquivos...")
    print(f"🛡️ Sistema anti-softban AVANÇADO ativado:")
    print(f"   • Delays: 2-3min entre envios")
    print(f"   • Pausa: 10-15min a cada 20 envios")
    print(f"   • Monitoramento: Evolution API")
    print(f"   • Templates: {len(message_templates)} variações")
    
    # Obter job do dicionário global
    with jobs_lock:
        job = bulk_send_jobs.get(job_id)
    
    if not job:
        print(f"❌ [JOB {job_id[:8]}] Job não encontrado!")
        return
    
    # Função auxiliar para verificar status da Evolution API
    async def check_evolution_status(evolution_service):
        """Verifica se Evolution API está online e operacional"""
        try:
            # check_instance_status() retorna um booleano diretamente
            is_online = await evolution_service.check_instance_status()
            return is_online
        except Exception as e:
            print(f"⚠️ Erro ao verificar status da Evolution API: {e}")
            return False
    
    try:
        # Importar serviço Evolution API
        sys.path.append(os.path.dirname(__file__))
        from app.services.evolution_api import EvolutionAPIService
        evolution_service = EvolutionAPIService()
        
        # Verificar configuração
        if not evolution_service.server_url or not evolution_service.api_key:
            job.status = 'failed'
            job.error_message = 'Evolution API não está configurada. Verifique o arquivo .env'
            job.end_time = datetime.now()
            print(f"❌ [JOB {job_id[:8]}] Evolution API não configurada")
            return
        
        # Criar event loop para thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Verificar se Evolution API está online antes de iniciar
        print(f"🔍 [JOB {job_id[:8]}] Verificando status da Evolution API...")
        is_online = loop.run_until_complete(check_evolution_status(evolution_service))
        if not is_online:
            job.status = 'failed'
            job.error_message = 'Evolution API está offline ou instância não conectada'
            job.end_time = datetime.now()
            print(f"❌ [JOB {job_id[:8]}] Evolution API offline!")
            return
        print(f"✅ [JOB {job_id[:8]}] Evolution API online e pronta")
        
        # Processar cada arquivo
        for idx, file_info in enumerate(selected_files):
            # ===== SISTEMA ANTI-SOFTBAN AVANÇADO =====
            if idx > 0:
                # Verificar se Evolution API ainda está online
                print(f"🔍 [JOB {job_id[:8]}] Verificando Evolution API antes do envio #{idx+1}...")
                is_online = loop.run_until_complete(check_evolution_status(evolution_service))
                if not is_online:
                    print(f"⚠️ [JOB {job_id[:8]}] Evolution API OFFLINE detectado! Pausando envios...")
                    job.status = 'paused'
                    job.error_message = 'Evolution API ficou offline durante o envio. Aguardando reconexão...'
                    
                    # Tentar reconectar a cada 2 minutos por até 30 minutos
                    max_wait_time = 30 * 60  # 30 minutos
                    wait_interval = 2 * 60   # 2 minutos
                    total_waited = 0
                    
                    while total_waited < max_wait_time:
                        print(f"⏳ [JOB {job_id[:8]}] Aguardando {wait_interval}s para verificar reconexão...")
                        time.sleep(wait_interval)
                        total_waited += wait_interval
                        
                        is_online = loop.run_until_complete(check_evolution_status(evolution_service))
                        if is_online:
                            print(f"✅ [JOB {job_id[:8]}] Evolution API voltou! Retomando envios...")
                            job.status = 'running'
                            job.error_message = None
                            break
                        else:
                            print(f"❌ [JOB {job_id[:8]}] Ainda offline. Tentando novamente em {wait_interval}s...")
                    
                    if not is_online:
                        job.status = 'failed'
                        job.error_message = f'Evolution API permaneceu offline por mais de {max_wait_time/60} minutos'
                        job.end_time = datetime.now()
                        print(f"❌ [JOB {job_id[:8]}] Abortando job - Evolution API não reconectou")
                        return
                
                # Delay maior a cada 20 envios (pausa estratégica)
                if idx % 20 == 0:
                    long_delay = round(random.uniform(600.00, 900.00), 2)  # 10-15 minutos
                    minutes = int(long_delay // 60)
                    seconds = int(long_delay % 60)
                    print(f"\n🛡️ [JOB {job_id[:8]}] ⏸️  PAUSA ESTRATÉGICA #{idx//20} - 20 ENVIOS COMPLETADOS")
                    print(f"⏳ Aguardando {long_delay:.2f}s ({minutes}min {seconds}s) para simular comportamento humano...")
                    print(f"⏰ Início da pausa: {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Dormir em chunks de 60s para permitir verificações intermediárias
                    remaining = long_delay
                    while remaining > 0:
                        sleep_time = min(60, remaining)
                        time.sleep(sleep_time)
                        remaining -= sleep_time
                        if remaining > 0:
                            print(f"   ⏳ Restam {int(remaining)}s da pausa estratégica...")
                    
                    print(f"✅ Pausa concluída: {datetime.now().strftime('%H:%M:%S')}\n")
                else:
                    # Delay normal: 2-3 minutos (120-180 segundos)
                    delay = round(random.uniform(120.00, 180.00), 2)
                    minutes = int(delay // 60)
                    seconds = int(delay % 60)
                    time_str = f"{minutes}m{seconds}s"
                    print(f"\n⏳ [JOB {job_id[:8]}] AGUARDANDO {delay:.2f}s ({time_str}) antes do envio #{idx+1}...")
                    print(f"⏰ Início do delay: {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(delay)
                    print(f"✅ Delay concluído: {datetime.now().strftime('%H:%M:%S')}\n")
            else:
                print(f"⚡ [JOB {job_id[:8]}] Primeiro holerite - SEM DELAY")
            
            filename = file_info.get('filename')
            employee = file_info.get('employee', {})
            month_year = file_info.get('month_year', 'desconhecido')
            
            employee_name = employee.get('full_name', 'Colaborador')
            phone_number = employee.get('phone_number', '')
            employee_id = employee.get('id')
            
            # Atualizar status do job
            job.current_file = filename
            
            # Sortear template de mensagem
            selected_template = random.choice(message_templates) if message_templates else None
            template_num = message_templates.index(selected_template) + 1 if selected_template in message_templates else 0
            
            print(f"\n📄 [JOB {job_id[:8]}] [{idx + 1}/{len(selected_files)}] Enviando {filename} para {employee_name}...")
            if selected_template:
                print(f"📝 Usando Template {template_num} para este envio")
            
            # Validar telefone
            if not phone_number or len(phone_number) < 10:
                print(f"⚠️ [JOB {job_id[:8]}] Telefone inválido para {employee_name}")
                job.failed_sends += 1
                job.failed_employees.append({
                    'filename': filename,
                    'employee': employee_name,
                    'reason': 'Telefone inválido'
                })
                job.processed_files += 1
                continue
            
            # Construir caminho do arquivo
            file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'holerites_formatados_final',
                filename
            )
            
            if not os.path.exists(file_path):
                print(f"⚠️ [JOB {job_id[:8]}] Arquivo não encontrado: {file_path}")
                job.failed_sends += 1
                job.failed_employees.append({
                    'filename': filename,
                    'employee': employee_name,
                    'reason': 'Arquivo não encontrado'
                })
                job.processed_files += 1
                continue
            
            # Enviar via Evolution API
            try:
                # 🎭 SIMULAR PRESENÇA "DIGITANDO" - Comportamento humano
                print(f"📝 [JOB {job_id[:8]}] Simulando digitação para {employee_name}...")
                try:
                    presence_result = loop.run_until_complete(
                        evolution_service.send_presence(
                            phone=phone_number,
                            presence_type="composing",
                            delay=5000  # 5 segundos
                        )
                    )
                    
                    if presence_result.get('success'):
                        print(f"✍️ [JOB {job_id[:8]}] Presença 'digitando' ativada por 5s")
                        time.sleep(5.5)  # Aguardar os 5s + margem de 0.5s
                    else:
                        print(f"⚠️ [JOB {job_id[:8]}] Não foi possível enviar presença: {presence_result.get('message')}")
                        # Continuar mesmo se presença falhar
                
                except Exception as presence_error:
                    print(f"⚠️ [JOB {job_id[:8]}] Erro ao simular presença: {presence_error}")
                    # Continuar o envio normalmente mesmo se presença falhar
                
                # Enviar mensagem após simulação de digitação
                result = loop.run_until_complete(
                    evolution_service.send_payroll_message(
                        phone=phone_number,
                        employee_name=employee_name,
                        file_path=file_path,
                        month_year=month_year,
                        message_template=selected_template
                    )
                )
                
                if result['success']:
                    print(f"✅ [JOB {job_id[:8]}] Holerite enviado para {employee_name}")
                    job.successful_sends += 1
                    
                    # Registrar no banco de dados
                    try:
                        from app.models.base import get_db
                        from app.models.payroll_send import PayrollSend
                        
                        # Converter month_year para formato YYYY-MM
                        month_for_db = month_year
                        if '_' in month_year:
                            month_name, year = month_year.split('_')
                            month_map = {
                                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
                                'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
                                'agosto': '08', 'setembro': '09', 'outubro': '10',
                                'novembro': '11', 'dezembro': '12'
                            }
                            month_num = month_map.get(month_name.lower(), '00')
                            month_for_db = f"{year}-{month_num}"
                        
                        db = next(get_db())
                        try:
                            payroll_send = PayrollSend(
                                employee_id=employee_id,
                                month=month_for_db,
                                file_path=filename,
                                status='sent',
                                sent_at=datetime.now(),
                                user_id=user_id
                            )
                            db.add(payroll_send)
                            db.commit()
                            print(f"💾 [JOB {job_id[:8]}] Registrado no banco (employee_id={employee_id})")
                        finally:
                            db.close()
                    except Exception as db_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao salvar no banco: {db_error}")
                    
                    # Mover arquivo para pasta 'enviados'
                    try:
                        enviados_dir = os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            'enviados'
                        )
                        if not os.path.exists(enviados_dir):
                            os.makedirs(enviados_dir, exist_ok=True)
                        
                        dest_path = os.path.join(enviados_dir, filename)
                        import shutil
                        shutil.move(file_path, dest_path)
                        print(f"📦 [JOB {job_id[:8]}] Arquivo movido para enviados/")
                    except Exception as move_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao mover arquivo: {move_error}")
                    
                    # Registrar log do sistema
                    try:
                        log_system_event(
                            event_type='payroll_sent',
                            description=f"Holerite enviado para {employee_name}",
                            details={
                                'job_id': job_id,
                                'filename': filename,
                                'employee_name': employee_name,
                                'phone_number': phone_number,
                                'month_year': month_year
                            },
                            severity='info',
                            user_id=user_id
                        )
                    except Exception as log_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao registrar log: {log_error}")
                
                else:
                    print(f"❌ [JOB {job_id[:8]}] Falha ao enviar para {employee_name}: {result['message']}")
                    job.failed_sends += 1
                    job.failed_employees.append({
                        'filename': filename,
                        'employee': employee_name,
                        'reason': result['message']
                    })
                    
                    # Registrar falha no banco
                    try:
                        from app.models.base import get_db
                        from app.models.payroll_send import PayrollSend
                        
                        month_for_db = month_year
                        if '_' in month_year:
                            month_name, year = month_year.split('_')
                            month_map = {
                                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
                                'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07',
                                'agosto': '08', 'setembro': '09', 'outubro': '10',
                                'novembro': '11', 'dezembro': '12'
                            }
                            month_num = month_map.get(month_name.lower(), '00')
                            month_for_db = f"{year}-{month_num}"
                        
                        db = next(get_db())
                        try:
                            payroll_send = PayrollSend(
                                employee_id=employee_id,
                                month=month_for_db,
                                file_path=filename,
                                status='failed',
                                error_message=result['message'],
                                sent_at=datetime.now(),
                                user_id=user_id
                            )
                            db.add(payroll_send)
                            db.commit()
                            print(f"💾 [JOB {job_id[:8]}] Falha registrada no banco")
                        finally:
                            db.close()
                    except Exception as db_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao salvar falha: {db_error}")
            
            except Exception as send_error:
                print(f"❌ [JOB {job_id[:8]}] Erro no envio para {employee_name}: {send_error}")
                job.failed_sends += 1
                job.failed_employees.append({
                    'filename': filename,
                    'employee': employee_name,
                    'reason': f'Erro na API: {str(send_error)}'
                })
            
            # Incrementar contador de processados
            job.processed_files += 1
        
        # Finalizar job
        job.status = 'completed'
        job.end_time = datetime.now()
        job.current_file = None
        
        elapsed = (job.end_time - job.start_time).total_seconds()
        print(f"\n✅ [JOB {job_id[:8]}] CONCLUÍDO!")
        print(f"📊 Resultado: {job.successful_sends}/{job.total_files} enviados com sucesso")
        print(f"⏱️ Tempo total: {int(elapsed)}s ({elapsed/60:.1f}min)")
        
    except Exception as e:
        print(f"❌ [JOB {job_id[:8]}] Erro fatal na thread: {e}")
        import traceback
        traceback.print_exc()
        
        job.status = 'failed'
        job.error_message = str(e)
        job.end_time = datetime.now()

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
        elif path == '/api/v1/employees/cache/status':
            self.handle_cache_status()
        
        # ===== ROTAS MIGRADAS PARA ESTRUTURA MODULAR =====
        elif path == '/api/v1/auth/me':
            from app.routes import AuthRouter
            AuthRouter(self).handle_auth_me()
        elif path == '/api/v1/dashboard/stats':
            from app.routes import DashboardRouter
            DashboardRouter(self).handle_dashboard_stats()
        elif path == '/api/v1/evolution/status':
            from app.routes import SystemRouter
            SystemRouter(self).handle_evolution_status()
        elif path == '/api/v1/system/status':
            from app.routes import SystemRouter
            SystemRouter(self).handle_system_status()
        elif path == '/api/v1/database/health':
            from app.routes import SystemRouter
            SystemRouter(self).handle_database_health()
        elif path == '/api/v1/system/logs':
            from app.routes import SystemRouter
            SystemRouter(self).handle_system_logs()
        # ==================================================
        
        elif path == '/api/v1/payrolls/processed':
            self.handle_payrolls_processed()
        
        # ===== ROTAS DE JOBS EM BACKGROUND =====
        elif path.startswith('/api/v1/payrolls/bulk-send/') and path.endswith('/status'):
            self.handle_bulk_send_status()
        # =======================================
        
        # ===== ROTAS DE REPORTS (MODULAR) =====
        elif path == '/api/v1/reports/recent':
            from app.routes.reports import ReportsRouter
            ReportsRouter(self).handle_recent_activity()
        elif path == '/api/v1/reports/statistics':
            from app.routes.reports import ReportsRouter
            ReportsRouter(self).handle_statistics()
        # ======================================
        
        # ===== ROTAS DE ENDOMARKETING =====
        elif path == '/api/v1/endomarketing/summary':
            self.handle_endomarketing_summary()
        elif path.startswith('/api/v1/endomarketing/birthdays'):
            # Extrair período da query string (week ou month)
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            period = query_params.get('period', ['month'])[0]
            self.handle_endomarketing_birthdays(period)
        elif path.startswith('/api/v1/endomarketing/work-anniversaries'):
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            period = query_params.get('period', ['month'])[0]
            self.handle_endomarketing_work_anniversaries(period)
        elif path.startswith('/api/v1/endomarketing/probation'):
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            phase = int(query_params.get('phase', ['1'])[0])
            self.handle_endomarketing_probation(phase)
        # ===================================
        
        # ===== ROTAS DE GERENCIAMENTO DE FILAS =====
        elif path == '/api/v1/queue/active':
            self.handle_get_active_queues()
        elif path == '/api/v1/queue/list':
            self.handle_get_all_queues()
        elif path == '/api/v1/queue/statistics':
            self.handle_get_queue_statistics()
        elif path.startswith('/api/v1/queue/') and path.endswith('/details'):
            queue_id = path.split('/')[-2]
            self.handle_get_queue_details(queue_id)
        # ===========================================
        
        # ===== ROTAS DE SCRIPTS ÚTEIS =====
        elif path.startswith('/api/v1/scripts/') and path.endswith('/preview'):
            script_id = path.split('/')[-2]
            self.handle_script_preview(script_id)
        # ==================================
        
        else:
            self.send_error(404, "Endpoint não encontrado")
    
    def do_POST(self):
        """Handle POST requests"""
        path = urllib.parse.urlparse(self.path).path
        print(f"🔥 POST recebido: {path}")
        
        # ===== ROTAS MIGRADAS PARA ESTRUTURA MODULAR =====
        if path == '/api/v1/auth/login':
            from app.routes import AuthRouter
            AuthRouter(self).handle_login()
            return
        # ==================================================
        
        if path == '/api/v1/employees':
            self.handle_create_employee()
        elif path == '/api/v1/employees/import' or path == '/api/v1/import/employees':
            self.handle_import_employees()
        elif path == '/api/v1/employees/cache/invalidate':
            self.handle_cache_invalidate()
        elif path == '/api/v1/users':
            self.handle_create_user()
        elif path == '/api/v1/users/permissions':
            self.handle_update_user_permissions()
        elif path == '/api/v1/payroll/periods':
            self.handle_create_payroll_period()
        elif path == '/api/v1/payroll/templates':
            self.handle_create_payroll_template()
        elif path == '/api/v1/payroll/process' or path == '/api/v1/payrolls/process':
            self.handle_process_payroll_file()
        elif path == '/api/v1/payrolls/bulk-send':
            self.handle_bulk_send_payrolls()
        elif path == '/api/v1/payrolls/delete-file':
            self.handle_delete_payroll_file()
        elif path == '/api/v1/files/upload':
            self.handle_file_upload()
        elif path == '/api/v1/communications/send':
            self.handle_send_communication()
        elif path == '/api/v1/evolution/test-message':
            self.handle_test_evolution_message()
        elif path.startswith('/api/v1/scripts/'):
            script_id = path.split('/')[-1]
            self.handle_execute_script(script_id)
        elif path.startswith('/api/v1/queue/') and path.endswith('/cancel'):
            queue_id = path.split('/')[-2]
            self.handle_cancel_queue(queue_id)
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
                    
                    print(f"🔑 Preparando token para usuário: {user.username} (ID: {user.id})")
                    
                    # Gerar JWT token real com user_id
                    token_data = {
                        "sub": user.username,
                        "user_id": user.id,  # ✅ Adicionar user_id ao payload
                        "email": user.email,
                        "is_admin": user.is_admin
                    }
                    print(f"🔐 Dados do token JWT: {token_data}")
                    access_token = create_access_token(data=token_data)
                    print(f"✅ Token gerado com sucesso!")
                    
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
            import os
            import glob
            
            # Diretório onde os holerites processados são salvos
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'holerites_formatados_final')
            
            if not os.path.exists(output_dir):
                self.send_json_response({
                    "files": [],
                    "statistics": {
                        "total": 0,
                        "ready": 0,
                        "orphan": 0,
                        "associated": 0
                    }
                })
                return
            
            # Buscar todos os PDFs no diretório
            pdf_files = glob.glob(os.path.join(output_dir, '*.pdf'))
            
            # Carregar dados dos colaboradores
            employees_data = load_employees_data()
            employees = employees_data.get('employees', [])
            
            # Criar dicionário de colaboradores por unique_id para busca rápida
            employees_by_id = {emp.get('unique_id'): emp for emp in employees}
            
            files_list = []
            stats = {
                "total": 0,
                "ready": 0,  # Com telefone e associado
                "orphan": 0,  # Sem colaborador cadastrado
                "associated": 0  # Associado a um colaborador
            }
            
            for pdf_path in pdf_files:
                filename = os.path.basename(pdf_path)
                
                # Extrair unique_id do nome do arquivo (formato: XXXXXXXXX_holerite_mes_ano.pdf)
                parts = filename.split('_')
                unique_id = parts[0] if parts else 'unknown'
                
                # Extrair mês/ano no formato YYYY-MM (banco aceita apenas 7 caracteres)
                month_year = 'desconhecido'
                if len(parts) >= 4:  # XXXXXXXXX_holerite_mes_ano.pdf
                    month_name = parts[2].lower()
                    year = parts[3].replace('.pdf', '')
                    
                    # Converter nome do mês para número
                    month_map = {
                        'janeiro': '01', 'fevereiro': '02', 'marco': '03', 'abril': '04',
                        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                    }
                    month_num = month_map.get(month_name, '00')
                    month_year = f"{year}-{month_num}"  # Formato YYYY-MM (7 caracteres)
                
                # Buscar colaborador associado
                employee = employees_by_id.get(unique_id)
                
                file_info = {
                    "filename": filename,
                    "unique_id": unique_id,
                    "month_year": month_year,
                    "size": os.path.getsize(pdf_path),
                    "created_at": datetime.fromtimestamp(os.path.getctime(pdf_path)).isoformat(),
                    "is_orphan": employee is None,
                    "can_send": False,
                    "associated_employee": None
                }
                
                if employee:
                    stats["associated"] += 1
                    phone = employee.get('phone_number', '').strip()
                    
                    file_info["associated_employee"] = {
                        "id": employee.get('id'),  # PRIMARY KEY para o banco
                        "unique_id": employee.get('unique_id'),
                        "full_name": employee.get('full_name'),
                        "phone_number": phone
                    }
                    
                    # Pode enviar se tem telefone
                    if phone and len(phone) >= 10:
                        file_info["can_send"] = True
                        stats["ready"] += 1
                else:
                    stats["orphan"] += 1
                
                files_list.append(file_info)
                stats["total"] += 1
            
            # Ordenar por data de criação (mais recentes primeiro)
            files_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            print(f"📊 Holerites processados: {stats['total']} total, {stats['ready']} prontos, {stats['orphan']} órfãos")
            
            self.send_json_response({
                "files": files_list,
                "statistics": stats
            })
            
        except Exception as e:
            print(f"❌ Erro ao listar holerites: {e}")
            import traceback
            traceback.print_exc()
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

    def parse_multipart_data(self, body, boundary):
        """Parse multipart form data to extract file and filename"""
        try:
            boundary_bytes = boundary.encode('utf-8')
            parts = body.split(b'--' + boundary_bytes)
            
            print(f"🔍 Parse multipart: {len(parts)} partes encontradas")
            
            for idx, part in enumerate(parts):
                if b'Content-Disposition' in part:
                    print(f"📦 Parte {idx} tem Content-Disposition")
                    
                    # Extrair todas as linhas do header
                    lines = part.split(b'\r\n')
                    print(f"   Primeira linha: {lines[0][:200]}")  # Primeiros 200 bytes
                    
                    filename = None
                    
                    # Procurar filename em qualquer linha do header
                    for line in lines[:5]:  # Verificar primeiras 5 linhas
                        if b'filename=' in line:
                            # Tentar extrair filename com aspas
                            if b'filename="' in line:
                                filename_start = line.find(b'filename="') + 10
                                filename_end = line.find(b'"', filename_start)
                                if filename_end != -1:
                                    filename = line[filename_start:filename_end].decode('utf-8')
                                    break
                            # Tentar sem aspas
                            elif b'filename=' in line:
                                filename_start = line.find(b'filename=') + 9
                                # Procurar próximo espaço ou ponto e vírgula
                                filename_end = line.find(b';', filename_start)
                                if filename_end == -1:
                                    filename_end = line.find(b'\r', filename_start)
                                if filename_end == -1:
                                    filename_end = len(line)
                                filename = line[filename_start:filename_end].strip().decode('utf-8')
                                break
                    
                    if filename:
                        print(f"   ✅ Filename encontrado: {filename}")
                        
                        # Find the start of file data (after headers)
                        header_end = part.find(b'\r\n\r\n')
                        if header_end != -1:
                            file_data = part[header_end + 4:]
                            # Remove trailing boundary markers
                            if file_data.endswith(b'\r\n'):
                                file_data = file_data[:-2]
                            return file_data, filename
                    else:
                        print(f"   ⚠️ Filename não encontrado nesta parte")
            
            print("❌ Nenhum arquivo encontrado no multipart")
            return None, None
        except Exception as e:
            print(f"❌ Erro ao parsear multipart data: {e}")
            import traceback
            traceback.print_exc()
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
                
                # SEMPRE invalidar cache após importação (mesmo com erros)
                # Garante que o frontend vai buscar dados atualizados
                print("🔄 Invalidando cache de employees (FORÇADO)...")
                invalidate_employees_cache()
                print("✅ Cache invalidado com sucesso!")
                
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
    
    def handle_file_upload(self):
        """Upload de arquivo PDF de holerites"""
        try:
            print("📤 Iniciando upload de arquivo...")
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            print(f"Content-Type: {content_type}")
            
            if not content_type.startswith('multipart/form-data'):
                print(f"❌ Content-Type inválido: {content_type}")
                self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                return
            
            # Get boundary
            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break
            
            print(f"Boundary: {boundary}")
            
            if not boundary:
                print("❌ Boundary não encontrado")
                self.send_json_response({"error": "Boundary não encontrado"}, 400)
                return
            
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            print(f"Content-Length: {content_length}")
            body = self.rfile.read(content_length)
            print(f"Body recebido: {len(body)} bytes")
            
            # Parse multipart data
            file_data, filename = self.parse_multipart_data(body, boundary)
            print(f"Parse result - file_data: {len(file_data) if file_data else 0} bytes, filename: {filename}")
            
            if not file_data:
                print("❌ Arquivo não encontrado no parse")
                self.send_json_response({"error": "Arquivo não encontrado no upload"}, 400)
                return
            
            # Validar que é PDF
            if not filename.lower().endswith('.pdf'):
                print(f"❌ Arquivo não é PDF: {filename}")
                self.send_json_response({"error": "Apenas arquivos PDF são aceitos"}, 400)
                return
            
            # Salvar arquivo temporariamente
            import os
            import time
            upload_dir = 'uploads'
            os.makedirs(upload_dir, exist_ok=True)
            
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(upload_dir, safe_filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            print(f"✅ Arquivo salvo: {filepath} ({len(file_data)} bytes)")
            
            self.send_json_response({
                "success": True,
                "filename": safe_filename,
                "original_filename": filename,
                "filepath": filepath,
                "size": len(file_data)
            })
            
        except Exception as e:
            print(f"❌ Erro no upload: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro ao fazer upload: {str(e)}"}, 500)

    def handle_process_payroll_file(self):
        """Processar arquivo de folha de pagamento - segmenta PDF e protege com senha"""
        try:
            print("📄 Iniciando processamento de holerites...")
            
            # Obter dados da requisição
            data = self.get_request_data()
            uploaded_file = data.get('uploadedFile', {})
            
            if not uploaded_file:
                self.send_json_response({"error": "Nenhum arquivo foi enviado"}, 400)
                return
            
            filepath = uploaded_file.get('filepath')
            filename = uploaded_file.get('filename')
            
            if not filepath or not filename:
                self.send_json_response({"error": "Dados do arquivo incompletos"}, 400)
                return
            
            print(f"📂 Processando arquivo: {filepath}")
            
            # Verificar se arquivo existe
            import os
            if not os.path.exists(filepath):
                self.send_json_response({"error": f"Arquivo não encontrado: {filepath}"}, 404)
                return
            
            # Criar diretório de saída se não existir
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'holerites_formatados_final')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"✅ Diretório criado: {output_dir}")
            
            # Processar PDF
            result = self.split_pdf_by_employee(filepath, output_dir)
            
            if result['success']:
                # Registrar processamento no banco de dados
                try:
                    # Extrair mês/ano do primeiro arquivo processado
                    month_year = 'desconhecido'
                    if result['files'] and len(result['files']) > 0:
                        month_year = result['files'][0].get('month_year', 'desconhecido')
                    
                    # Log de processamento bem-sucedido
                    log_system_event(
                        event_type='payroll_processing',
                        description=f"PDF processado: {filename}",
                        details={
                            'original_file': filename,
                            'processed_count': result['processed_count'],
                            'month_year': month_year,
                            'files_generated': [f['filename'] for f in result['files'][:10]],  # Primeiros 10
                            'warnings': result.get('warnings', [])
                        },
                        severity='info',
                        user_id=None  # TODO: Pegar do token JWT
                    )
                    
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log: {log_error}")
                
                print(f"✅ Processamento concluído: {result['processed_count']} holerites gerados")
                self.send_json_response({
                    "success": True,
                    "message": f"PDF processado com sucesso",
                    "processed_count": result['processed_count'],
                    "files": result['files'],
                    "warnings": result.get('warnings', []),
                    "month_year": month_year if 'month_year' in locals() else 'desconhecido'
                }, 200)
            else:
                print(f"❌ Erro no processamento: {result['error']}")
                
                # Registrar erro no log
                try:
                    log_system_event(
                        event_type='payroll_processing_error',
                        description=f"Erro ao processar PDF: {filename}",
                        details={
                            'original_file': filename,
                            'error': result['error']
                        },
                        severity='error',
                        user_id=None
                    )
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log de erro: {log_error}")
                
                self.send_json_response({
                    "error": result['error']
                }, 500)
                
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def split_pdf_by_employee(self, input_pdf_path, output_dir):
        """Segmenta PDF em holerites individuais e protege com senha
        
        NOVO: Suporta múltiplas páginas por colaborador.
        Agrupa páginas consecutivas com o mesmo cadastro/matrícula antes de gerar o PDF.
        """
        import re
        
        if not PDF_PROCESSING_AVAILABLE:
            return {
                'success': False,
                'error': 'PyPDF2 não está disponível. Instale com: pip install PyPDF2'
            }
        
        try:
            files_created = []
            unprotected_pdfs = []
            
            with open(input_pdf_path, 'rb') as infile:
                reader = PyPDF2.PdfReader(infile)
                num_pages = len(reader.pages)
                
                print(f"📖 PDF contém {num_pages} páginas")
                
                # ========== FASE 1: ANALISAR TODAS AS PÁGINAS ==========
                # Extrair informações de cada página antes de processar
                page_info = []
                
                for i in range(num_pages):
                    page = reader.pages[i]
                    text = page.extract_text()
                    
                    # Regex para encontrar o número de cadastro
                    cadastro_match = re.search(r'Cadastro\s*Nome\s*do\s*Funcionário\s*CBO\s*Empresa\s*Local\s*Departamento\s*FL\s*\n\s*(\d+)', text)
                    cadastro_num = cadastro_match.group(1) if cadastro_match else 'UNKNOWN_CAD'
                    
                    # Regex para encontrar o número da empresa
                    empresa_field_match = re.search(r'(\d+)\s+[A-ZÀ-Ú\s]+\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+\d+', text)
                    empresa_num = empresa_field_match.group(3) if empresa_field_match else 'UNKNOWN_EMP'
                    
                    # Formatação do identificador único: XXXXYYYYY
                    if empresa_num != 'UNKNOWN_EMP' and cadastro_num != 'UNKNOWN_CAD':
                        empresa_formatted = str(empresa_num).zfill(4)
                        cadastro_formatted = str(cadastro_num).zfill(5)
                        file_identifier = f'{empresa_formatted}{cadastro_formatted}'
                    else:
                        file_identifier = f'UNKNOWN_{i+1}'
                    
                    # Regex para encontrar o CPF
                    cpf_match = re.search(r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
                    employee_cpf = ''
                    if cpf_match:
                        employee_cpf_full = cpf_match.group(1).replace('.', '').replace('-', '')
                        employee_cpf = employee_cpf_full[:4]
                    
                    # Regex para encontrar o mês e ano de referência
                    month_year_match = re.search(r"(\d{2})\s*/\s*(\d{4})\s*(?:Mensal|13o?\s+Sal[aá]rio)", text, re.IGNORECASE)
                    
                    if month_year_match:
                        month_year = f"{month_year_match.group(1)}/{month_year_match.group(2)}"
                    else:
                        month_year = "UNKNOWN_DATE"
                        print(f"⚠️ Página {i+1}: Não foi possível extrair mês/ano")
                    
                    page_info.append({
                        'page_index': i,
                        'identifier': file_identifier,
                        'cpf': employee_cpf,
                        'month_year': month_year,
                        'page': page
                    })
                    
                    print(f"📄 Página {i+1}: {file_identifier} (CPF: {'****' if employee_cpf else 'NÃO ENCONTRADO'})")
                
                # ========== FASE 2: AGRUPAR PÁGINAS DO MESMO COLABORADOR ==========
                # Agrupar páginas consecutivas com o mesmo identifier
                grouped_pages = {}
                
                for info in page_info:
                    identifier = info['identifier']
                    
                    # Se já existe um grupo para este identifier, adicionar página
                    if identifier in grouped_pages:
                        grouped_pages[identifier]['pages'].append(info['page'])
                        grouped_pages[identifier]['page_numbers'].append(info['page_index'] + 1)
                    else:
                        # Criar novo grupo
                        grouped_pages[identifier] = {
                            'pages': [info['page']],
                            'page_numbers': [info['page_index'] + 1],
                            'cpf': info['cpf'],
                            'month_year': info['month_year']
                        }
                
                # ========== FASE 3: CRIAR PDFs AGRUPADOS ==========
                # Mapeamento de números de mês para nomes
                month_names = {
                    "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
                    "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
                    "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro"
                }
                
                for identifier, group_data in grouped_pages.items():
                    pages = group_data['pages']
                    employee_cpf = group_data['cpf']
                    month_year = group_data['month_year']
                    page_numbers = group_data['page_numbers']
                    
                    # Formatar mês/ano
                    if month_year != "UNKNOWN_DATE":
                        month_num = month_year.split("/")[0]
                        year = month_year.split("/")[1]
                        formatted_month_year = f"{month_names.get(month_num, 'UNKNOWN')}_{year}"
                    else:
                        formatted_month_year = "UNKNOWN_DATE"
                    
                    output_pdf_path = os.path.join(output_dir, f'{identifier}_holerite_{formatted_month_year}.pdf')
                    
                    # Criar PDF writer e adicionar TODAS as páginas do colaborador
                    writer = PyPDF2.PdfWriter()
                    for page in pages:
                        writer.add_page(page)
                    
                    num_pages_employee = len(pages)
                    page_range = f"{page_numbers[0]}-{page_numbers[-1]}" if num_pages_employee > 1 else str(page_numbers[0])
                    
                    # Proteger com senha (4 primeiros dígitos do CPF)
                    if employee_cpf:
                        try:
                            writer.encrypt(user_password=employee_cpf, owner_password=None)
                            print(f"🔒 Holerite {identifier}: {num_pages_employee} página(s) [pág. {page_range}] - protegido com senha")
                        except Exception as e:
                            print(f"⚠️ Erro ao proteger {identifier}: {e}")
                            unprotected_pdfs.append({
                                'identifier': identifier,
                                'reason': f'Erro ao criptografar: {e}'
                            })
                    else:
                        print(f"⚠️ Holerite {identifier}: {num_pages_employee} página(s) [pág. {page_range}] - CPF não encontrado, PDF NÃO protegido")
                        unprotected_pdfs.append({
                            'identifier': identifier,
                            'reason': 'CPF não encontrado'
                        })
                    
                    # Salvar arquivo
                    with open(output_pdf_path, 'wb') as outfile:
                        writer.write(outfile)
                    
                    files_created.append({
                        'identifier': identifier,
                        'filename': os.path.basename(output_pdf_path),
                        'path': output_pdf_path,
                        'protected': bool(employee_cpf),
                        'month_year': formatted_month_year,
                        'pages_count': num_pages_employee,
                        'page_range': page_range
                    })
                    
                    print(f"✅ Holerite {identifier} salvo: {num_pages_employee} página(s) (senha: {'SIM' if employee_cpf else 'NÃO'})")
            
            # Preparar warnings se houver PDFs não protegidos
            warnings = []
            if unprotected_pdfs:
                warnings.append(f"{len(unprotected_pdfs)} PDF(s) não foram protegidos com senha")
                for pdf in unprotected_pdfs:
                    warnings.append(f"  - {pdf['identifier']}: {pdf['reason']}")
            
            # Estatísticas de páginas múltiplas
            multi_page_count = sum(1 for f in files_created if f.get('pages_count', 1) > 1)
            if multi_page_count > 0:
                print(f"\n📊 Estatística: {multi_page_count} colaborador(es) com múltiplas páginas")
            
            return {
                'success': True,
                'processed_count': len(files_created),
                'files': files_created,
                'warnings': warnings,
                'multi_page_employees': multi_page_count
            }
            
        except Exception as e:
            print(f"❌ Erro ao segmentar PDF: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Erro ao processar PDF: {str(e)}'
            }

    def handle_send_communication(self):
        """Enviar comunicado para colaboradores via WhatsApp"""
        try:
            print("📨 Iniciando envio de comunicado...")
            
            # Obter dados da requisição
            data = self.get_request_data()
            selected_employees = data.get('selectedEmployees', [])
            message = data.get('message', '').strip()
            uploaded_file = data.get('uploadedFile')
            
            if not selected_employees:
                self.send_json_response({"error": "Nenhum colaborador selecionado"}, 400)
                return
            
            if not message and not uploaded_file:
                self.send_json_response({"error": "É necessário enviar uma mensagem ou um arquivo"}, 400)
                return
            
            print(f"📋 Enviando para {len(selected_employees)} colaborador(es)")
            
            # Carregar dados dos colaboradores
            employees_data = load_employees_data()
            employees = employees_data.get('employees', [])
            
            # Criar dicionário para busca rápida por ID
            employees_by_id = {emp.get('id'): emp for emp in employees}
            
            # Pegar user_id do token JWT (se disponível)
            user_id = None
            try:
                auth_header = self.headers.get('Authorization', '')
                print(f"🔑 Authorization header: {auth_header[:50] if auth_header else 'VAZIO'}...")
                if auth_header.startswith('Bearer '):
                    token = auth_header.replace('Bearer ', '')
                    from app.core.auth import decode_token
                    payload = decode_token(token)
                    print(f"📦 Payload completo do JWT: {payload}")
                    user_id = payload.get('user_id')
                    print(f"👤 user_id extraído: {user_id} (tipo: {type(user_id)})")
                else:
                    print(f"⚠️ Token não encontrado no header Authorization")
            except Exception as auth_error:
                print(f"⚠️ Erro ao obter user_id do token: {auth_error}")
                import traceback
                traceback.print_exc()
            
            # Criar registro único de CommunicationSend ANTES dos envios
            comm_send_id = None
            try:
                from app.models.base import get_db
                from app.models.communication_send import CommunicationSend
                from datetime import datetime
                
                db = next(get_db())
                try:
                    # Gerar título descritivo
                    if message and uploaded_file:
                        title = f"Mensagem + Arquivo ({len(selected_employees)} destinatários)"
                    elif message:
                        title = f"{message[:50]}..." if len(message) > 50 else message
                    else:
                        title = f"Arquivo ({len(selected_employees)} destinatários)"
                    
                    comm_send = CommunicationSend(
                        title=title,
                        message=message if message else None,
                        file_path=uploaded_file.get('filepath') if uploaded_file else None,
                        total_recipients=len(selected_employees),
                        successful_sends=0,
                        failed_sends=0,
                        status='sending',
                        started_at=datetime.now(),
                        user_id=user_id
                    )
                    db.add(comm_send)
                    db.commit()
                    comm_send_id = comm_send.id
                    print(f"💾 Lote criado no banco (communication_send_id={comm_send_id})")
                finally:
                    db.close()
            except Exception as db_error:
                print(f"⚠️ Erro ao criar lote no banco: {db_error}")
                import traceback
                traceback.print_exc()
            
            # Listas de controle
            success_count = 0
            failed_employees = []
            
            # Processar cada colaborador
            for idx, emp_id in enumerate(selected_employees):
                # ===== DELAY ANTI-STRIKE DO WHATSAPP =====
                if idx > 0:
                    import random
                    import time
                    from datetime import datetime
                    # Delay entre 47 e 73 segundos (47s a 1m13s) para evitar softban
                    delay = round(random.uniform(47.00, 73.00), 2)
                    minutes = int(delay // 60)
                    seconds = int(delay % 60)
                    time_str = f"{minutes}m{seconds}s" if minutes > 0 else f"{seconds}s"
                    print(f"\n⏳⏳⏳ AGUARDANDO {delay:.2f} SEGUNDOS ({time_str}) antes do envio #{idx+1}...")
                    print(f"⏰ Início do delay: {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(delay)
                    print(f"✅ Delay concluído: {datetime.now().strftime('%H:%M:%S')}\n")
                else:
                    print(f"⚡ Primeiro envio - SEM DELAY (instantâneo)")
                
                employee = employees_by_id.get(emp_id)
                
                if not employee:
                    failed_employees.append({
                        'id': emp_id,
                        'reason': 'Colaborador não encontrado'
                    })
                    continue
                
                phone = employee.get('phone_number', '').strip()
                if not phone or len(phone) < 10:
                    failed_employees.append({
                        'id': emp_id,
                        'name': employee.get('full_name'),
                        'reason': 'Telefone inválido'
                    })
                    continue
                
                # ENVIO REAL via Evolution API
                print(f"📤 Enviando comunicado para {employee.get('full_name')} ({phone})...")
                
                try:
                    import asyncio
                    import sys
                    sys.path.append(os.path.dirname(__file__))
                    from app.services.evolution_api import EvolutionAPIService
                    
                    evolution_service = EvolutionAPIService()
                    
                    # Criar event loop se necessário
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Enviar comunicado (texto + arquivo se houver)
                    file_path = None
                    if uploaded_file:
                        file_path = uploaded_file.get('filepath')
                    
                    result = loop.run_until_complete(
                        evolution_service.send_communication_message(
                            phone=phone,
                            message_text=message,
                            file_path=file_path
                        )
                    )
                    
                    if result['success']:
                        print(f"✅ Comunicado enviado para {employee.get('full_name')}")
                        success_count += 1
                        
                        # Registrar recipient no banco (se temos comm_send_id)
                        if comm_send_id:
                            try:
                                from app.models.base import get_db
                                from app.models.communication_recipient import CommunicationRecipient
                                from datetime import datetime
                                
                                db = next(get_db())
                                try:
                                    recipient = CommunicationRecipient(
                                        communication_send_id=comm_send_id,
                                        employee_id=emp_id,
                                        status='sent',
                                        sent_at=datetime.now()
                                    )
                                    db.add(recipient)
                                    db.commit()
                                finally:
                                    db.close()
                            except Exception as db_error:
                                print(f"⚠️ Erro ao salvar recipient no banco: {db_error}")
                        
                        # Registrar no log
                        try:
                            log_system_event(
                                event_type='communication_sent',
                                description=f"Comunicado enviado para {employee.get('full_name')}",
                                details={
                                    'employee_id': emp_id,
                                    'employee_name': employee.get('full_name'),
                                    'phone_number': phone,
                                    'message_preview': message[:100] if message else '[Arquivo enviado]',
                                    'has_file': uploaded_file is not None,
                                    'evolution_result': result['message']
                                },
                                severity='info',
                                user_id=user_id
                            )
                        except Exception as log_error:
                            print(f"⚠️ Erro ao registrar log: {log_error}")
                    else:
                        print(f"❌ Falha ao enviar para {employee.get('full_name')}: {result['message']}")
                        failed_employees.append({
                            'id': emp_id,
                            'name': employee.get('full_name'),
                            'reason': result['message']
                        })
                        
                        # Registrar falha no banco (se temos comm_send_id)
                        if comm_send_id:
                            try:
                                from app.models.base import get_db
                                from app.models.communication_recipient import CommunicationRecipient
                                from datetime import datetime
                                
                                db = next(get_db())
                                try:
                                    recipient = CommunicationRecipient(
                                        communication_send_id=comm_send_id,
                                        employee_id=emp_id,
                                        status='failed',
                                        error_message=result['message'],
                                        sent_at=datetime.now()
                                    )
                                    db.add(recipient)
                                    db.commit()
                                finally:
                                    db.close()
                            except Exception as db_error:
                                print(f"⚠️ Erro ao salvar falha no banco: {db_error}")
                        
                except Exception as send_error:
                    print(f"❌ Erro no envio para {employee.get('full_name')}: {send_error}")
                    failed_employees.append({
                        'id': emp_id,
                        'name': employee.get('full_name'),
                        'reason': f'Erro na API: {str(send_error)}'
                    })
            
            # Registrar erros no log
            if failed_employees:
                try:
                    log_system_event(
                        event_type='communication_failed',
                        description=f"{len(failed_employees)} envio(s) de comunicado falharam",
                        details={
                            'failed_count': len(failed_employees),
                            'failed_employees': failed_employees
                        },
                        severity='warning',
                        user_id=user_id
                    )
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log de falhas: {log_error}")
            
            # Atualizar status final do CommunicationSend
            if comm_send_id:
                try:
                    from app.models.base import get_db
                    from app.models.communication_send import CommunicationSend
                    from datetime import datetime
                    
                    db = next(get_db())
                    try:
                        comm_send = db.query(CommunicationSend).filter(
                            CommunicationSend.id == comm_send_id
                        ).first()
                        
                        if comm_send:
                            comm_send.successful_sends = success_count
                            comm_send.failed_sends = len(failed_employees)
                            comm_send.status = 'completed' if success_count > 0 else 'failed'
                            comm_send.completed_at = datetime.now()
                            db.commit()
                            print(f"💾 Status atualizado: {comm_send.status} ({success_count} sucessos, {len(failed_employees)} falhas)")
                    finally:
                        db.close()
                except Exception as db_error:
                    print(f"⚠️ Erro ao atualizar status final: {db_error}")
            
            result_message = f"{success_count} comunicado(s) enviado(s) com sucesso"
            if failed_employees:
                result_message += f", {len(failed_employees)} falharam"
            
            print(f"📊 Resultado: {result_message}")
            
            self.send_json_response({
                "success": True,
                "message": result_message,
                "success_count": success_count,
                "failed_count": len(failed_employees),
                "failed_employees": failed_employees
            }, 200)
            
        except Exception as e:
            print(f"❌ Erro ao enviar comunicado: {e}")
            import traceback
            traceback.print_exc()
            
            # Atualizar status como failed em caso de erro
            if 'comm_send_id' in locals() and comm_send_id:
                try:
                    from app.models.base import get_db
                    from app.models.communication_send import CommunicationSend
                    from datetime import datetime
                    
                    db = next(get_db())
                    try:
                        comm_send = db.query(CommunicationSend).filter(
                            CommunicationSend.id == comm_send_id
                        ).first()
                        if comm_send:
                            comm_send.status = 'failed'
                            comm_send.completed_at = datetime.now()
                            db.commit()
                    finally:
                        db.close()
                except:
                    pass
            
            # Registrar erro crítico no log
            try:
                log_system_event(
                    event_type='communication_error',
                    description=f"Erro crítico ao enviar comunicado",
                    details={'error': str(e)},
                    severity='error',
                    user_id=user_id if 'user_id' in locals() else None
                )
            except Exception as log_error:
                print(f"⚠️ Erro ao registrar log de erro: {log_error}")
            
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_delete_payroll_file(self):
        """Excluir arquivo de holerite processado"""
        try:
            print("🗑️ Iniciando exclusão de arquivo de holerite...")
            
            # Obter dados da requisição
            data = self.get_request_data()
            filename = data.get('filename')
            
            if not filename:
                self.send_json_response({"error": "Nome do arquivo não fornecido"}, 400)
                return
            
            print(f"🗑️ Arquivo solicitado para exclusão: {filename}")
            
            # Caminho do arquivo na pasta holerites_formatados_final
            # Usar caminho absoluto a partir do diretório do script (funciona em Windows e Linux)
            import os
            
            # Obter diretório backend (onde está o main_legacy.py)
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            # O diretório holerites_formatados_final fica dentro do backend/
            processed_dir = os.path.join(backend_dir, 'holerites_formatados_final')
            
            # Normalizar o caminho (resolve .., /, \, etc)
            processed_dir = os.path.normpath(processed_dir)
            file_path = os.path.join(processed_dir, filename)
            file_path = os.path.normpath(file_path)
            
            print(f"🔍 Procurando em: {processed_dir}")
            print(f"🔍 Caminho completo: {file_path}")
            
            # Verificar se o diretório existe
            if not os.path.exists(processed_dir):
                print(f"❌ Diretório não encontrado: {processed_dir}")
                self.send_json_response({"error": f"Diretório de holerites não encontrado"}, 500)
                return
            
            # Listar arquivos no diretório para debug
            print(f"📂 Arquivos no diretório:")
            try:
                files_in_dir = os.listdir(processed_dir)
                # Procurar arquivo com nome similar (pode ter _ duplo ou simples)
                matching_files = [f for f in files_in_dir if filename in f or f in filename]
                if matching_files:
                    print(f"   Arquivos similares encontrados: {matching_files}")
                else:
                    print(f"   Nenhum arquivo similar a '{filename}' encontrado")
                    print(f"   Total de arquivos no diretório: {len(files_in_dir)}")
            except Exception as list_error:
                print(f"⚠️ Erro ao listar diretório: {list_error}")
            
            # Verificar se arquivo existe
            if not os.path.exists(file_path):
                print(f"⚠️ Arquivo não encontrado: {file_path}")
                
                # Tentar encontrar com underscore duplo (bug comum)
                alt_filename = filename.replace('_holerite_', '_holerite__')
                alt_file_path = os.path.join(processed_dir, alt_filename)
                
                if os.path.exists(alt_file_path):
                    print(f"✅ Arquivo encontrado com underscore duplo: {alt_filename}")
                    file_path = alt_file_path
                    filename = alt_filename
                else:
                    self.send_json_response({"error": "Arquivo não encontrado"}, 404)
                    return
            
            # Excluir o arquivo
            try:
                os.remove(file_path)
                print(f"✅ Arquivo removido: {filename}")
                
                # Registrar no log do sistema
                try:
                    log_system_event(
                        event_type='payroll_file_deleted',
                        description=f"Arquivo de holerite excluído: {filename}",
                        details={'filename': filename},
                        severity='info',
                        user_id=None  # TODO: pegar user_id da sessão
                    )
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log: {log_error}")
                
                self.send_json_response({
                    "success": True,
                    "message": f"Arquivo {filename} removido com sucesso"
                }, 200)
                
            except PermissionError:
                print(f"❌ Sem permissão para excluir: {filename}")
                self.send_json_response({"error": "Sem permissão para excluir o arquivo"}, 403)
            except Exception as delete_error:
                print(f"❌ Erro ao excluir arquivo: {delete_error}")
                self.send_json_response({"error": f"Erro ao excluir arquivo: {str(delete_error)}"}, 500)
                
        except Exception as e:
            print(f"❌ Erro no handler de exclusão: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_bulk_send_payrolls(self):
        """Iniciar envio em lote em background e retornar job_id imediatamente"""
        try:
            print("📨 Iniciando envio em lote de holerites (background mode)...")
            
            # Obter dados da requisição
            data = self.get_request_data()
            selected_files = data.get('selected_files', [])
            
            # Aceitar array de templates ou template único (retrocompatibilidade)
            message_templates = data.get('message_templates', [])
            if not message_templates:
                # Fallback para o campo antigo
                single_template = data.get('message_template', '').strip()
                if single_template:
                    message_templates = [single_template]
            
            if not selected_files:
                self.send_json_response({"error": "Nenhum arquivo selecionado"}, 400)
                return
            
            # Pegar user_id do token JWT
            user_id = None
            try:
                auth_header = self.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header.replace('Bearer ', '')
                    from app.core.auth import decode_token
                    payload = decode_token(token)
                    user_id = payload.get('user_id')
                    print(f"👤 user_id extraído: {user_id}")
            except Exception as auth_error:
                print(f"⚠️ Erro ao obter user_id do token: {auth_error}")
            
            # Criar job_id único
            job_id = str(uuid.uuid4())
            
            # Registrar job no dicionário global
            with jobs_lock:
                job = BulkSendJob(job_id, len(selected_files))
                bulk_send_jobs[job_id] = job
            
            print(f"🆔 Job criado: {job_id} ({len(selected_files)} arquivos)")
            
            # Iniciar thread em background
            thread = threading.Thread(
                target=process_bulk_send_in_background,
                args=(job_id, selected_files, message_templates, user_id),
                daemon=True
            )
            thread.start()
            
            # Retornar imediatamente com job_id
            self.send_json_response({
                "success": True,
                "message": f"Envio iniciado em background. Use o job_id para acompanhar o progresso.",
                "job_id": job_id,
                "total_files": len(selected_files),
                "status_endpoint": f"/api/v1/payrolls/bulk-send/{job_id}/status"
            }, 202)  # 202 Accepted
            
            print(f"✅ Resposta enviada ao cliente. Thread em background processando...")
            
        except Exception as e:
            print(f"❌ Erro ao iniciar envio em lote: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_bulk_send_status(self):
        """Verificar status de um job de envio em background"""
        try:
            # Extrair job_id da URL: /api/v1/payrolls/bulk-send/{job_id}/status
            path_parts = self.path.split('/')
            if len(path_parts) < 7:
                self.send_json_response({"error": "job_id não informado"}, 400)
                return
            
            job_id = path_parts[5]  # /api/v1/payrolls/bulk-send/{job_id}/status
            
            # Buscar job no dicionário
            with jobs_lock:
                job = bulk_send_jobs.get(job_id)
            
            if not job:
                self.send_json_response({"error": "Job não encontrado"}, 404)
                return
            
            # Retornar status do job
            self.send_json_response(job.to_dict(), 200)
            
        except Exception as e:
            print(f"❌ Erro ao buscar status do job: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_test_evolution_message(self):
        """Testar envio de mensagem via Evolution API"""
        try:
            print("🧪 Testando Evolution API...")
            
            # Obter dados da requisição
            data = self.get_request_data()
            phone_number = data.get('phone_number', '').strip()
            test_message = data.get('message', 'Teste de mensagem da Evolution API - Sistema EnviaFolha funcionando! 🚀')
            
            if not phone_number:
                self.send_json_response({"error": "Número de telefone obrigatório"}, 400)
                return
            
            print(f"📞 Enviando mensagem de teste para: {phone_number}")
            
            # Importar e usar o serviço de Evolution API
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.evolution_api import EvolutionAPIService
                
                evolution_service = EvolutionAPIService()
                
                # Verificar se Evolution API está configurada
                if not evolution_service.server_url or not evolution_service.api_key:
                    self.send_json_response({
                        "success": False,
                        "error": "Evolution API não está configurada no .env"
                    }, 400)
                    return
                
                print(f"🔧 Configuração Evolution API:")
                print(f"   Server: {evolution_service.server_url}")
                print(f"   Instance: {evolution_service.instance_name}")
                print(f"   API Key: {'*' * (len(evolution_service.api_key) - 4)}{evolution_service.api_key[-4:]}")
                
                # Verificar status da instância
                print("🔍 Verificando status da instância...")
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                is_connected = loop.run_until_complete(evolution_service.check_instance_status())
                
                if not is_connected:
                    print("⚠️ Instância não está conectada!")
                    self.send_json_response({
                        "success": False,
                        "warning": "Instância Evolution API não está conectada",
                        "message": "Tentando enviar mesmo assim..."
                    }, 200)
                else:
                    print("✅ Instância está conectada!")
                
                # Enviar mensagem de teste
                print(f"📤 Enviando: {test_message}")
                result = loop.run_until_complete(
                    evolution_service._send_text_message(phone_number, test_message)
                )
                loop.close()
                
                if result['success']:
                    print(f"✅ Mensagem enviada com sucesso!")
                    
                    # Registrar no log
                    try:
                        log_system_event(
                            event_type='evolution_test_message',
                            description=f"Mensagem de teste enviada para {phone_number}",
                            details={
                                'phone_number': phone_number,
                                'message': test_message,
                                'result': result
                            },
                            severity='info',
                            user_id=None
                        )
                    except Exception as log_error:
                        print(f"⚠️ Erro ao registrar log: {log_error}")
                    
                    self.send_json_response({
                        "success": True,
                        "message": "Mensagem de teste enviada com sucesso!",
                        "details": result
                    }, 200)
                else:
                    print(f"❌ Erro ao enviar mensagem: {result['message']}")
                    self.send_json_response({
                        "success": False,
                        "error": result['message']
                    }, 500)
                
            except ImportError as e:
                print(f"❌ Erro ao importar EvolutionAPIService: {e}")
                self.send_json_response({
                    "error": "Serviço Evolution API não está disponível"
                }, 500)
                
        except Exception as e:
            print(f"❌ Erro no teste da Evolution API: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_script_preview(self, script_id):
        """Preview de alterações que um script faria"""
        try:
            print(f"🔍 Preview do script: {script_id}")
            
            # Verificar autenticação
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            # Verificar se é admin
            if not user.is_admin:
                db.close()
                self.send_json_response({
                    "error": "Apenas administradores podem visualizar scripts"
                }, 403)
                return
            
            # Importar serviço de scripts
            import sys
            sys.path.append(os.path.dirname(__file__))
            from app.services.utility_scripts import UtilityScriptsService
            
            try:
                service = UtilityScriptsService(db)
                result = service.preview_script(script_id)
                
                print(f"✅ Preview gerado: {result.get('affected_count', 0)} registros")
                self.send_json_response(result, 200)
                
            except ValueError as e:
                print(f"❌ Script não encontrado: {e}")
                self.send_json_response({"error": str(e)}, 404)
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao gerar preview do script: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_execute_script(self, script_id):
        """Executa um script utilitário"""
        try:
            print(f"⚡ Executando script: {script_id}")
            
            # Verificar autenticação
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            # Verificar se é admin
            if not user.is_admin:
                db.close()
                self.send_json_response({
                    "error": "Apenas administradores podem executar scripts"
                }, 403)
                return
            
            # Importar serviço de scripts
            import sys
            sys.path.append(os.path.dirname(__file__))
            from app.services.utility_scripts import UtilityScriptsService
            
            try:
                service = UtilityScriptsService(db)
                result = service.execute_script(script_id)
                
                print(f"✅ Script executado: {result.get('affected_count', 0)} registros alterados")
                
                # Registrar no log do sistema
                try:
                    log_system_event(
                        event_type='utility_script_executed',
                        description=f"Script '{script_id}' executado por {user.username}",
                        details={
                            'script_id': script_id,
                            'result': result,
                            'user_id': user.id
                        },
                        severity='info',
                        user_id=user.id
                    )
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log: {log_error}")
                
                self.send_json_response(result, 200)
                
            except ValueError as e:
                print(f"❌ Script não encontrado: {e}")
                self.send_json_response({"error": str(e)}, 404)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao executar script: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_endomarketing_summary(self):
        """Retorna resumo dos indicadores de endomarketing"""
        try:
            print("📊 Carregando resumo de endomarketing...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.endomarketing import EndomarketingService
                
                service = EndomarketingService(db)
                summary = service.get_dashboard_summary()
                
                self.send_json_response(summary, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar resumo de endomarketing: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_endomarketing_birthdays(self, period: str):
        """Retorna lista de aniversariantes"""
        try:
            print(f"🎂 Carregando aniversariantes ({period})...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.endomarketing import EndomarketingService
                
                service = EndomarketingService(db)
                result = service.get_birthday_employees(period)
                
                self.send_json_response(result, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar aniversariantes: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_endomarketing_work_anniversaries(self, period: str):
        """Retorna lista de aniversariantes de empresa"""
        try:
            print(f"🏢 Carregando aniversariantes de empresa ({period})...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.endomarketing import EndomarketingService
                
                service = EndomarketingService(db)
                result = service.get_work_anniversary_employees(period)
                
                self.send_json_response(result, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar aniversariantes de empresa: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_endomarketing_probation(self, phase: int):
        """Retorna lista de colaboradores em experiência"""
        try:
            print(f"📋 Carregando colaboradores em experiência (fase {phase})...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.endomarketing import EndomarketingService
                
                service = EndomarketingService(db)
                result = service.get_probation_employees(phase)
                
                self.send_json_response(result, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar colaboradores em experiência: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_get_active_queues(self):
        """Retorna lista de filas ativas"""
        try:
            print("📋 Carregando filas ativas...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.queue_manager import QueueManagerService
                
                service = QueueManagerService(db)
                queues = service.get_active_queues()
                
                self.send_json_response({"queues": queues}, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar filas ativas: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_get_all_queues(self):
        """Retorna lista de todas as filas com filtros"""
        try:
            print("📋 Carregando todas as filas...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.queue_manager import QueueManagerService
                
                # Extrair parâmetros da query string
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                status_filter = query_params.get('status', [None])[0]
                queue_type_filter = query_params.get('type', [None])[0]
                limit = int(query_params.get('limit', ['50'])[0])
                
                service = QueueManagerService(db)
                queues = service.get_all_queues(
                    limit=limit,
                    status_filter=status_filter,
                    queue_type_filter=queue_type_filter
                )
                
                self.send_json_response({"queues": queues}, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar filas: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_get_queue_details(self, queue_id: str):
        """Retorna detalhes completos de uma fila"""
        try:
            print(f"🔍 Carregando detalhes da fila {queue_id}...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.queue_manager import QueueManagerService
                
                service = QueueManagerService(db)
                details = service.get_queue_details(queue_id)
                
                if details is None:
                    self.send_json_response({"error": "Fila não encontrada"}, 404)
                else:
                    self.send_json_response(details, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar detalhes da fila: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_get_queue_statistics(self):
        """Retorna estatísticas gerais das filas"""
        try:
            print("📊 Carregando estatísticas das filas...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.queue_manager import QueueManagerService
                
                service = QueueManagerService(db)
                stats = service.get_queue_statistics()
                
                self.send_json_response(stats, 200)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar estatísticas: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_cancel_queue(self, queue_id: str):
        """Cancela uma fila em execução"""
        try:
            print(f"🛑 Cancelando fila {queue_id}...")
            
            db = SessionLocal()
            user = self.get_authenticated_user(db)
            if not user:
                db.close()
                self.send_json_response({"error": "Autenticação necessária"}, 401)
                return
            
            try:
                import sys
                sys.path.append(os.path.dirname(__file__))
                from app.services.queue_manager import QueueManagerService
                
                service = QueueManagerService(db)
                success = service.cancel_queue(queue_id, user.id)
                
                if success:
                    self.send_json_response({"message": "Fila cancelada com sucesso"}, 200)
                else:
                    self.send_json_response({"error": "Não foi possível cancelar a fila"}, 400)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao cancelar fila: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_reports_statistics(self):
        """Estatísticas para relatórios de envios"""
        try:
            print("📊 Carregando estatísticas de relatórios...")
            
            # Buscar logs do banco de dados
            if not SessionLocal:
                # Sem banco de dados, retornar dados vazios
                self.send_json_response({
                    "summary": {
                        "total_sent": 0,
                        "total_success": 0,
                        "total_failed": 0,
                        "success_rate": 100
                    },
                    "by_type": {
                        "communications": {"sent": 0, "success": 0, "failed": 0},
                        "payrolls": {"sent": 0, "success": 0, "failed": 0}
                    },
                    "recent_activity": [],
                    "message": "Banco de dados não disponível"
                })
                return
            
            db = SessionLocal()
            try:
                from app.models.system_log import SystemLog, LogCategory
                from sqlalchemy import func, desc
                from datetime import datetime, timedelta
                
                # Estatísticas de comunicados (buscar por category=COMMUNICATION e message contendo sucesso/falha)
                comm_logs = db.query(SystemLog).filter(
                    SystemLog.category == LogCategory.COMMUNICATION
                ).all()
                
                comm_sent = sum(1 for log in comm_logs if 'enviado' in log.message.lower() or 'sucesso' in log.message.lower())
                comm_failed = sum(1 for log in comm_logs if 'falha' in log.message.lower() or 'erro' in log.message.lower())
                
                # Estatísticas de holerites (buscar por category=PAYROLL)
                payroll_logs = db.query(SystemLog).filter(
                    SystemLog.category == LogCategory.PAYROLL
                ).all()
                
                payroll_processed = sum(1 for log in payroll_logs if 'enviado' in log.message.lower() or 'sucesso' in log.message.lower())
                payroll_failed = sum(1 for log in payroll_logs if 'falha' in log.message.lower() or 'erro' in log.message.lower())
                
                # Total geral
                total_sent = comm_sent + payroll_processed
                total_success = comm_sent + payroll_processed
                total_failed = comm_failed + payroll_failed
                
                success_rate = 100
                if (total_success + total_failed) > 0:
                    success_rate = round((total_success / (total_success + total_failed)) * 100, 2)
                
                # Atividades recentes (últimos 50 registros de comunicações e holerites)
                recent_logs = db.query(SystemLog).filter(
                    SystemLog.category.in_([
                        LogCategory.COMMUNICATION,
                        LogCategory.PAYROLL,
                        LogCategory.WHATSAPP
                    ])
                ).order_by(desc(SystemLog.created_at)).limit(50).all()
                
                recent_activity = []
                for log in recent_logs:
                    # Determinar tipo e status da atividade
                    activity_type = 'communication' if log.category == LogCategory.COMMUNICATION else 'payroll'
                    status = 'success' if ('enviado' in log.message.lower() or 'sucesso' in log.message.lower()) else 'error'
                    
                    activity = {
                        "id": log.id,
                        "type": activity_type,
                        "description": log.message,
                        "timestamp": log.created_at.strftime('%d/%m/%Y %H:%M:%S') if log.created_at else 'N/A',
                        "status": status,
                        "details": log.details or ''
                    }
                    recent_activity.append(activity)
                
                result = {
                    "summary": {
                        "total_sent": total_sent,
                        "total_success": total_success,
                        "total_failed": total_failed,
                        "success_rate": success_rate
                    },
                    "by_type": {
                        "communications": {
                            "sent": comm_sent,
                            "success": comm_sent,
                            "failed": comm_failed
                        },
                        "payrolls": {
                            "sent": payroll_processed,
                            "success": payroll_processed,
                            "failed": payroll_failed
                        }
                    },
                    "recent_activity": recent_activity
                }
                
                print(f"✅ Estatísticas carregadas: {total_sent} envios, {success_rate}% sucesso")
                self.send_json_response(result)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar estatísticas: {e}")
            import traceback
            traceback.print_exc()
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
    
    def handle_cache_status(self):
        """Endpoint para verificar status do cache de employees"""
        try:
            import time
            global employees_cache
            
            current_time = time.time()
            cache_age = current_time - employees_cache['last_update']
            is_valid = employees_cache['data'] is not None and cache_age < employees_cache['ttl']
            
            self.send_json_response({
                "cache_valid": is_valid,
                "cache_age_seconds": round(cache_age, 2),
                "cache_ttl_seconds": employees_cache['ttl'],
                "has_data": employees_cache['data'] is not None,
                "employee_count": len(employees_cache['data']['employees']) if employees_cache['data'] else 0,
                "last_update": employees_cache['last_update']
            })
        except Exception as e:
            print(f"❌ Erro ao verificar cache: {e}")
            self.send_json_response({"error": str(e)}, 500)
    
    def handle_cache_invalidate(self):
        """Endpoint para invalidar cache manualmente"""
        try:
            authenticated_user = self.get_authenticated_user()
            if not authenticated_user:
                self.send_json_response({"error": "Usuário não autenticado"}, 401)
                return
            
            print(f"🔄 Cache invalidado manualmente por: {authenticated_user.username}")
            invalidate_employees_cache()
            
            self.send_json_response({
                "success": True,
                "message": "Cache invalidado com sucesso",
                "invalidated_by": authenticated_user.username
            })
        except Exception as e:
            print(f"❌ Erro ao invalidar cache: {e}")
            self.send_json_response({"error": str(e)}, 500)

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
