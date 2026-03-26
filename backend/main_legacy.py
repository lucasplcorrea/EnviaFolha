#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Envio RH - Servidor com PostgreSQL (Versão Corrigida)
"""

import http.server
import socketserver
import json
import os
import shutil
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
                    "cpf": emp.cpf or "",
                    "phone_number": emp.phone or "",
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
    
    # Inicializar queue_id como None (será atribuído se fila for criada com sucesso)
    queue_id = None
    
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
        # Importar serviços
        sys.path.append(os.path.dirname(__file__))
        from app.services.evolution_api import EvolutionAPIService
        from app.services.queue_manager import QueueManagerService
        from app.services.instance_manager import InstanceManager
        from app.models.base import get_db
        
        # Criar sessão do banco de dados para a thread
        db = SessionLocal()
        
        # Inicializar gerenciador de instâncias
        instance_manager = InstanceManager()
        
        # Não criar evolution_service aqui - será criado a cada envio para round-robin efetivo
        evolution_service = None  # Placeholder, será atribuído no loop
        queue_service = QueueManagerService(db)
        
        # Verificar configuração básica
        from app.core.config import settings
        if not settings.EVOLUTION_SERVER_URL or not settings.EVOLUTION_API_KEY:
            job.status = 'failed'
            job.error_message = 'Evolution API não está configurada. Verifique o arquivo .env'
            job.end_time = datetime.now()
            print(f"❌ [JOB {job_id[:8]}] Evolution API não configurada")
            return
        
        # Criar event loop para thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Verificar se há pelo menos UMA instância online antes de iniciar
        print(f"🔍 [JOB {job_id[:8]}] Verificando instâncias disponíveis...")
        all_instances_status = loop.run_until_complete(instance_manager.check_all_instances_status())
        online_count = sum(1 for is_online in all_instances_status.values() if is_online)
        
        if online_count == 0:
            job.status = 'failed'
            job.error_message = 'Nenhuma instância WhatsApp está conectada'
            job.end_time = datetime.now()
            print(f"❌ [JOB {job_id[:8]}] Nenhuma instância online!")
            return
        
        print(f"✅ [JOB {job_id[:8]}] {online_count} instância(s) online disponível(is)")
        
        # 🎯 CRIAR FILA NO SISTEMA DE GESTÃO DE ENVIOS
        db = next(get_db())
        try:
            # Obter informações do usuário e computador
            import socket
            computer_name = socket.gethostname()
            ip_address = socket.gethostbyname(computer_name)
            
            # Criar fila
            queue_id = queue_service.create_queue(
                user_id=user_id,
                queue_type='holerite',
                description=f'Envio de {len(selected_files)} holerites',
                total_items=len(selected_files),
                computer_name=computer_name,
                ip_address=ip_address,
                metadata={
                    'job_id': job_id,
                    'templates_count': len(message_templates),
                    'anti_softban': True
                }
            )
            print(f"📋 [JOB {job_id[:8]}] Fila criada: {queue_id}")
            
            # Adicionar itens à fila e mapear IDs
            queue_item_map = {}  # filename -> item_id
            for file_info in selected_files:
                employee = file_info.get('employee', {})
                filename = file_info.get('filename', '')
                item = queue_service.add_queue_item(
                    queue_id=queue_id,
                    employee_id=employee.get('id'),
                    phone_number=employee.get('phone_number', ''),
                    file_path=filename,
                    metadata={
                        'employee_name': employee.get('full_name', ''),
                        'month_year': file_info.get('month_year', '')
                    }
                )
                queue_item_map[filename] = item.id
                print(f"🗺️ [JOB {job_id[:8]}] Mapeado: {filename} -> item_id={item.id}")
            db.commit()
            print(f"✅ [JOB {job_id[:8]}] {len(selected_files)} itens adicionados à fila")
            print(f"📋 [JOB {job_id[:8]}] Mapa de itens: {list(queue_item_map.keys())}")
        except Exception as queue_error:
            print(f"⚠️ [JOB {job_id[:8]}] Erro ao criar fila: {queue_error}")
            # Continuar mesmo se fila falhar
            queue_id = None
            queue_item_map = {}
        finally:
            db.close()
        
        # Processar cada arquivo
        last_selected_instance = None
        for idx, file_info in enumerate(selected_files):
            # 🛑 VERIFICAR SE FILA FOI CANCELADA OU PAUSADA
            if queue_id:
                try:
                    from app.models.send_queue import SendQueue
                    temp_db = SessionLocal()
                    try:
                        queue = temp_db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
                        
                        # Cancelamento
                        if queue and queue.status == 'cancelled':
                            print(f"🛑 [JOB {job_id[:8]}] Fila cancelada pelo usuário. Interrompendo envios...")
                            job.status = 'cancelled'
                            job.end_time = datetime.now()
                            temp_db.close()
                            return
                        
                        # Pausa - aguardar até retomar
                        while queue and queue.status == 'paused':
                            print(f"⏸️  [JOB {job_id[:8]}] Fila pausada. Aguardando retomada...")
                            time.sleep(5)  # Verificar a cada 5 segundos
                            temp_db.refresh(queue)
                            
                            # Verificar se foi cancelada durante a pausa
                            if queue.status == 'cancelled':
                                print(f"🛑 [JOB {job_id[:8]}] Fila cancelada durante pausa. Interrompendo...")
                                job.status = 'cancelled'
                                job.end_time = datetime.now()
                                temp_db.close()
                                return
                        
                        if queue and queue.status == 'processing':
                            print(f"▶️  [JOB {job_id[:8]}] Fila retomada. Continuando envios...")
                    finally:
                        temp_db.close()
                except Exception as e:
                    print(f"⚠️ [JOB {job_id[:8]}] Erro ao verificar status da fila: {e}")
            
            # ===== SISTEMA ANTI-SOFTBAN AVANÇADO COM OTIMIZAÇÃO MULTI-INSTÂNCIA =====
            if idx > 0:
                # 🎯 DELAY INTELIGENTE POR INSTÂNCIA
                # Cada instância tem seu próprio cooldown, permitindo envios paralelos
                
                # Descobrir qual será a próxima instância
                next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
                
                if not next_instance:
                    print(f"⚠️ [JOB {job_id[:8]}] TODAS as instâncias estão OFFLINE! Pausando envios...")
                    job.status = 'paused'
                    job.error_message = 'Todas as instâncias WhatsApp estão offline. Aguardando reconexão...'
                    
                    # Tentar reconectar a cada 2 minutos por até 30 minutos
                    max_wait_time = 30 * 60  # 30 minutos
                    wait_interval = 2 * 60   # 2 minutos
                    total_waited = 0
                    
                    while total_waited < max_wait_time:
                        print(f"⏳ [JOB {job_id[:8]}] Aguardando {wait_interval}s para verificar reconexão...")
                        time.sleep(wait_interval)
                        total_waited += wait_interval
                        
                        all_status = loop.run_until_complete(instance_manager.check_all_instances_status())
                        online_count = sum(1 for status in all_status.values() if status)
                        
                        if online_count > 0:
                            print(f"✅ [JOB {job_id[:8]}] {online_count} instância(s) voltaram online! Retomando envios...")
                            job.status = 'running'
                            job.error_message = None
                            next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
                            break
                        else:
                            print(f"❌ [JOB {job_id[:8]}] Todas ainda offline. Tentando novamente em {wait_interval}s...")
                    
                    if not next_instance:
                        job.status = 'failed'
                        job.error_message = f'Todas as instâncias permaneceram offline por mais de {max_wait_time/60} minutos'
                        job.end_time = datetime.now()
                        print(f"❌ [JOB {job_id[:8]}] Abortando job - Nenhuma instância reconectou")
                        return
                
                # Verificar quanto tempo passou desde último envio NESTA instância
                instance_delay = instance_manager.get_instance_delay(next_instance)
                min_delay_per_instance = 30  # Mínimo 30s entre envios da mesma instância
                
                if instance_delay < min_delay_per_instance:
                    # Precisa aguardar para esta instância
                    wait_time = min_delay_per_instance - instance_delay
                    print(f"⏳ [JOB {job_id[:8]}] Instância {next_instance} precisa aguardar {wait_time:.1f}s (último envio há {instance_delay:.1f}s)")
                    print(f"⏰ Início do delay: {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(wait_time)
                    print(f"✅ Delay concluído: {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print(f"⚡ [JOB {job_id[:8]}] Instância {next_instance} pronta (último envio há {instance_delay:.1f}s) - SEM DELAY")
                
                # Pausa estratégica a cada 20 envios (independente de instância)
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
                # Primeiro envio - SEM DELAY
                print(f"⚡ [JOB {job_id[:8]}] Primeiro envio - SEM DELAY")
            
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
                
                # 📊 ATUALIZAR FILA - TELEFONE INVÁLIDO
                if queue_id:
                    try:
                        queue_service.update_queue_progress(queue_id=queue_id, failed=1)
                    except Exception as e:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao atualizar fila: {e}")
                
                continue
            
            # NOVO: Usar caminho do arquivo (filepath) se fornecido, senão construir caminho antigo
            file_path = file_info.get('filepath')
            
            if not file_path:
                # Fallback: formato atual (processed/)
                file_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    'processed',
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
                
                # 📊 ATUALIZAR FILA - ARQUIVO NÃO ENCONTRADO
                if queue_id:
                    try:
                        queue_service.update_queue_progress(queue_id=queue_id, failed=1)
                    except Exception as e:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao atualizar fila: {e}")
                
                continue
            
            # Enviar via Evolution API
            try:
                # 🔄 SELECIONAR PRÓXIMA INSTÂNCIA ONLINE (ROUND-ROBIN INTELIGENTE)
                # Se já foi selecionada no delay check, usar a mesma; senão, selecionar nova
                if idx == 0 or 'next_instance' not in locals():
                    next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
                # Senão, next_instance já foi definida no bloco de delay acima
                
                if not next_instance:
                    print(f"❌ [JOB {job_id[:8]}] Nenhuma instância online disponível")
                    job.failed_sends += 1
                    job.failed_employees.append({
                        'filename': filename,
                        'employee': employee_name,
                        'reason': 'Nenhuma instância WhatsApp online'
                    })
                    job.processed_files += 1
                    
                    # Atualizar fila
                    if queue_id:
                        try:
                            queue_service.update_queue_progress(queue_id=queue_id, failed=1)
                        except Exception as e:
                            print(f"⚠️ [JOB {job_id[:8]}] Erro ao atualizar fila: {e}")
                    continue
                
                previous_instance = last_selected_instance
                print(f"🔄 [JOB {job_id[:8]}] Round-robin (holerite): {previous_instance or 'N/A'} -> {next_instance}")
                print(f"📱 [JOB {job_id[:8]}] Usando instância: {next_instance}")
                
                # Criar serviço com a instância selecionada
                evolution_service = EvolutionAPIService(instance_name=next_instance)
                
                print(f"📄 [JOB {job_id[:8]}] Enviando documento para {employee_name}...")
                
                result = loop.run_until_complete(
                    evolution_service.send_payroll_message(
                        phone=phone_number,
                        employee_name=employee_name,
                        file_path=file_path,
                        month_year=month_year,
                        message_template=selected_template
                    )
                )
                
                # Registrar envio na instância (para tracking de delays)
                instance_manager.register_send(next_instance)
                last_selected_instance = next_instance
                print(f"✅ [JOB {job_id[:8]}] Envio registrado para instância: {next_instance}")
                
                # Verificar resultado
                if result['success']:
                    print(f"✅ [JOB {job_id[:8]}] ✨ SUCESSO com instância {next_instance}")
                    job.successful_sends += 1
                    
                    # 📊 ATUALIZAR FILA DE ENVIOS E ITEM
                    if queue_id:
                        try:
                            queue_service.update_queue_progress(
                                queue_id=queue_id,
                                processed=1,
                                successful=1
                            )
                            # Atualizar status do item individual
                            item_id = queue_item_map.get(filename)
                            print(f"🔍 [JOB {job_id[:8]}] Procurando item para {filename}: item_id={item_id}")
                            if item_id:
                                queue_service.update_item_status(item_id, 'sent')
                                print(f"✅ [JOB {job_id[:8]}] Item {item_id} marcado como 'sent'")
                            else:
                                print(f"⚠️ [JOB {job_id[:8]}] Item não encontrado no mapa para {filename}")
                        except Exception as queue_update_error:
                            print(f"⚠️ [JOB {job_id[:8]}] Erro ao atualizar fila: {queue_update_error}")
                    
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
                            os.makedirs(enviados_dir)
                        
                        dest_path = os.path.join(enviados_dir, filename)
                        shutil.move(file_path, dest_path)
                        print(f"📦 [JOB {job_id[:8]}] Arquivo movido para enviados/")
                    except Exception as move_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao mover arquivo: {move_error}")
                    
                    # 📝 REGISTRAR LOG DO SISTEMA - ENVIO SUCESSO
                    try:
                        from app.models.system_log import SystemLog, LogLevel, LogCategory
                        log_db = SessionLocal()
                        try:
                            log_details = {
                                'job_id': job_id,
                                'queue_id': queue_id,
                                'filename': filename,
                                'month_year': month_year,
                                'employee_name': employee_name,
                                'employee_id': employee_id,
                                'phone_number': phone_number,
                                'instance': next_instance,
                                'round_robin_previous': previous_instance,
                                'message_id': result.get('message_id'),
                                'send_type': 'payroll',
                                'status': 'success'
                            }
                            log_entry = SystemLog(
                                level=LogLevel.INFO,
                                category=LogCategory.PAYROLL,
                                message=f"Holerite enviado com sucesso: {employee_name} ({month_year})",
                                details=json.dumps(log_details, ensure_ascii=False),
                                user_id=user_id,
                                entity_type='Employee',
                                entity_id=str(employee_id)
                            )
                            log_db.add(log_entry)
                            log_db.commit()
                            print(f"📝 [JOB {job_id[:8]}] Log de sucesso registrado")
                        finally:
                            log_db.close()
                    except Exception as log_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao registrar log: {log_error}")
                
                else:
                    # Falha no envio
                    error_msg = result.get('message', 'Erro desconhecido')
                    print(f"❌ [JOB {job_id[:8]}] Falha ao enviar para {employee_name}: {error_msg}")
                    job.failed_sends += 1
                    job.failed_employees.append({
                        'filename': filename,
                        'employee': employee_name,
                        'reason': error_msg
                    })
                    job.processed_files += 1
                    
                    # 📊 ATUALIZAR FILA - FALHA E ITEM
                    if queue_id:
                        try:
                            queue_service.update_queue_progress(
                                queue_id=queue_id,
                                processed=1,
                                failed=1
                            )
                            # Atualizar status do item individual
                            item_id = queue_item_map.get(filename)
                            print(f"🔍 [JOB {job_id[:8]}] Procurando item (falha) para {filename}: item_id={item_id}")
                            if item_id:
                                queue_service.update_item_status(item_id, 'failed', error_msg)
                                print(f"❌ [JOB {job_id[:8]}] Item {item_id} marcado como 'failed'")
                            else:
                                print(f"⚠️ [JOB {job_id[:8]}] Item não encontrado no mapa para {filename}")
                        except Exception as queue_update_error:
                            print(f"⚠️ [JOB {job_id[:8]}] Erro ao atualizar fila: {queue_update_error}")
                    
                    # Salvar falha no banco de dados
                    try:
                        from app.models.base import get_db
                        from app.models.payroll_send import PayrollSend
                        
                        month_for_db = month_year
                        if '_' in month_year:
                            parts = month_year.split('_')
                            month_name = parts[0]
                            year = parts[1]
                            month_map = {
                                'janeiro': '01', 'fevereiro': '02', 'março': '03',
                                'abril': '04', 'maio': '05', 'junho': '06',
                                'julho': '07', 'agosto': '08', 'setembro': '09',
                                'outubro': '10', 'novembro': '11', 'dezembro': '12'
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
                                error_message=error_msg,
                                user_id=user_id
                            )
                            db.add(payroll_send)
                            db.commit()
                            print(f"💾 [JOB {job_id[:8]}] Falha registrada no banco (employee_id={employee_id})")
                        finally:
                            db.close()
                    except Exception as db_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao salvar falha no banco: {db_error}")
                    
                    # 📝 REGISTRAR LOG DO SISTEMA - ENVIO FALHA
                    try:
                        from app.models.system_log import SystemLog, LogLevel, LogCategory
                        log_db = SessionLocal()
                        try:
                            log_details = {
                                'job_id': job_id,
                                'queue_id': queue_id,
                                'filename': filename,
                                'month_year': month_year,
                                'employee_name': employee_name,
                                'employee_id': employee_id,
                                'phone_number': phone_number,
                                'instance': next_instance,
                                'round_robin_previous': previous_instance,
                                'send_type': 'payroll',
                                'status': 'failed',
                                'error': error_msg
                            }
                            log_entry = SystemLog(
                                level=LogLevel.ERROR,
                                category=LogCategory.PAYROLL,
                                message=f"Falha ao enviar holerite: {employee_name} ({month_year})",
                                details=json.dumps(log_details, ensure_ascii=False),
                                user_id=user_id,
                                entity_type='Employee',
                                entity_id=str(employee_id)
                            )
                            log_db.add(log_entry)
                            log_db.commit()
                            print(f"📝 [JOB {job_id[:8]}] Log de falha registrado")
                        finally:
                            log_db.close()
                    except Exception as log_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao registrar log: {log_error}")
                    
                    # Registrar log do sistema (antigo)
                    try:
                        log_system_event(
                            event_type='payroll_sent_failed',
                            description=f"Falha ao enviar holerite para {employee_name}",
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
            
            except Exception as send_error:
                print(f"❌ [JOB {job_id[:8]}] Erro no envio para {employee_name}: {send_error}")
                job.failed_sends += 1
                job.failed_employees.append({
                    'filename': filename,
                    'employee': employee_name,
                    'reason': f'Erro na API: {str(send_error)}'
                })
                
                # 📊 ATUALIZAR FILA DE ENVIOS COM EXCEÇÃO E ITEM
                if queue_id:
                    try:
                        queue_service.update_queue_progress(
                            queue_id=queue_id,
                            processed=1,
                            failed=1
                        )
                        # Atualizar status do item individual
                        item_id = queue_item_map.get(filename)
                        if item_id:
                            queue_service.update_item_status(item_id, 'failed', str(send_error))
                    except Exception as queue_update_error:
                        print(f"⚠️ [JOB {job_id[:8]}] Erro ao atualizar fila: {queue_update_error}")
            
            # Incrementar contador de processados
            job.processed_files += 1
        
        # Finalizar job
        job.status = 'completed'
        job.end_time = datetime.now()
        job.current_file = None
        
        # 🎯 FINALIZAR FILA NO SISTEMA DE GESTÃO
        if queue_id:
            try:
                # A função update_queue_progress marca automaticamente como 'completed'
                # quando processed_items == total_items
                from app.models.send_queue import SendQueue
                queue = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
                if queue and queue.status != 'completed':
                    queue.status = 'completed'
                    db.commit()
                print(f"✅ [JOB {job_id[:8]}] Fila marcada como concluída")
            except Exception as queue_final_error:
                print(f"⚠️ [JOB {job_id[:8]}] Erro ao finalizar fila: {queue_final_error}")
        
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
        
        # 🎯 MARCAR FILA COMO FALHA
        if queue_id:
            try:
                from app.models.send_queue import SendQueue
                queue = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
                if queue:
                    queue.status = 'failed'
                    queue.error_message = str(e)
                    db.commit()
                print(f"❌ [JOB {job_id[:8]}] Fila marcada como falha")
            except Exception as queue_fail_error:
                print(f"⚠️ [JOB {job_id[:8]}] Erro ao marcar fila como falha: {queue_fail_error}")
    finally:
        # Fechar sessão principal do banco
        if 'db' in locals():
            db.close()
            print(f"🔒 [JOB {job_id[:8]}] Sessão do banco fechada")

class EnviaFolhaHandler(http.server.SimpleHTTPRequestHandler):
    
    # Rotas silenciosas (não aparecerão nos logs)
    SILENT_ROUTES = [
        '/api/v1/database/health',      # Healthcheck do banco (a cada 5s)
        '/api/v1/queue/active',          # Polling de filas ativas (a cada 3s)
        '/api/v1/queue/list',            # Listagem de todas as filas (a cada 5s)
        '/api/v1/payrolls/bulk-send/',   # Polling de status de jobs (a cada 2s)
        '/api/v1/evolution/instances',   # Polling de status WhatsApp (a cada 5s)
        '/favicon.ico',                   # Navegador pedindo favicon
    ]
    
    def log_message(self, format, *args):
        """
        Sobrescreve log_message para filtrar rotas de healthcheck/polling
        Reduz ruído nos logs mantendo apenas requisições importantes
        """
        # Pegar a mensagem que seria logada
        message = format % args
        
        # Verificar se é uma rota silenciosa
        for route in self.SILENT_ROUTES:
            if route in self.path:
                return  # Não logar esta requisição
        
        # Logar normalmente para rotas importantes
        super().log_message(format, *args)
    
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
        elif path == '/api/v1/payroll/period-comparison':
            self.handle_period_comparison()
        elif path == '/api/v1/payroll/templates':
            self.handle_payroll_templates_list()
        elif path.startswith('/api/v1/payroll/periods/'):
            period_id = path.split('/')[-1]
            self.handle_payroll_period_summary(period_id)
        
        # Rotas de benefícios
        elif path == '/api/v1/benefits/periods':
            self.handle_benefits_periods_list()
        elif path == '/api/v1/benefits/processing-logs':
            self.handle_benefits_processing_logs()
        elif path.startswith('/api/v1/benefits/periods/'):
            period_id = path.split('/')[-1]
            self.handle_benefits_period_detail(period_id)
        
        # Rotas de cartão ponto
        elif path == '/api/v1/timecard/periods':
            self.handle_timecard_periods_list()
        elif path == '/api/v1/timecard/processing-logs':
            self.handle_timecard_processing_logs()
        elif path.startswith('/api/v1/timecard/periods/'):
            period_id = path.split('/')[-1]
            self.handle_timecard_period_detail(period_id)
        elif path == '/api/v1/timecard/stats':
            self.handle_timecard_stats()
        elif path.startswith('/api/v1/employees/'):
            # IMPORTANTE: Verificar PRIMEIRO se é rota de leaves
            parts = path.split('/')
            print(f"🔍 DEBUG: parts = {parts}, len = {len(parts)}")
            
            if len(parts) >= 6 and parts[5] == 'leaves':
                employee_id = parts[4]
                print(f"✅ Rota de leaves detectada para employee_id: {employee_id}")
                if len(parts) == 6:
                    # GET /api/v1/employees/{id}/leaves - lista todos os afastamentos
                    self.handle_get_employee_leaves(employee_id)
                else:
                    # GET /api/v1/employees/{id}/leaves/{leave_id} - detalhes de um afastamento
                    leave_id = parts[6]
                    self.handle_get_employee_leave_detail(employee_id, leave_id)
                return  # IMPORTANTE: Return aqui para não cair na rota padrão
            
            # Rota padrão de detalhes do employee
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
        elif path == '/api/v1/evolution/instances':
            from app.routes import SystemRouter
            SystemRouter(self).handle_evolution_instances_status()
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
        
        # ===== ROTAS DE INDICADORES RH =====
        elif path == '/api/v1/indicators/overview':
            self.handle_indicators_overview()
        elif path == '/api/v1/indicators/headcount':
            self.handle_indicators_headcount()
        elif path == '/api/v1/indicators/turnover':
            self.handle_indicators_turnover()
        elif path == '/api/v1/indicators/demographics':
            self.handle_indicators_demographics()
        elif path == '/api/v1/indicators/tenure':
            self.handle_indicators_tenure()
        elif path == '/api/v1/indicators/leaves':
            self.handle_indicators_leaves()
        elif path == '/api/v1/reports/generate':
            self.handle_report_generate()
        # ===================================
        
        elif path == '/api/v1/payrolls/processed':
            self.handle_payrolls_processed()
        elif path == '/api/v1/tax-statements':
            self.handle_list_tax_statements()
        elif path == '/api/v1/payrolls/periods':
            self.handle_list_payroll_periods()
        elif path == '/api/v1/payroll/statistics':
            self.handle_payroll_statistics()  # 🆕 Estatísticas dos dados CSV
        elif path == '/api/v1/payroll/employees':
            self.handle_payroll_employees()  # 🆕 Lista colaboradores
        elif path == '/api/v1/payroll/divisions':
            self.handle_payroll_divisions()  # 🆕 Lista setores
        elif path == '/api/v1/payroll/companies':
            self.handle_payroll_companies()  # 🆕 Lista empresas
        elif path == '/api/v1/payroll/years':
            self.handle_payroll_years()  # 🆕 Lista anos disponíveis
        elif path == '/api/v1/payroll/months':
            self.handle_payroll_months()  # 🆕 Lista meses disponíveis
        elif path == '/api/v1/payroll/processing-history':
            self.handle_payroll_processing_history()  # 🆕 Histórico de processamento
        elif path.startswith('/api/v1/payroll/statistics-debug'):
            self.handle_payroll_statistics_debug()  # 🆕 DEBUG - Lista nomes dos colaboradores
        elif path.startswith('/api/v1/payroll/statistics-filtered'):
            self.handle_payroll_statistics_filtered()  # 🆕 Estatísticas com filtros
        
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
        elif path.startswith('/api/v1/employees/'):
            # Verificar se é rota de leaves
            parts = path.split('/')
            if len(parts) >= 6 and parts[5] == 'leaves':
                employee_id = parts[4]
                print(f"✅ POST para leaves do employee_id: {employee_id}")
                self.handle_create_employee_leave(employee_id)
                return
            # Se não for leaves, continuar verificando outras rotas
        
        if path == '/api/v1/employees/import' or path == '/api/v1/import/employees':
            self.handle_import_employees()
        elif path == '/api/v1/employees/cache/invalidate':
            self.handle_cache_invalidate()
        elif path == '/api/v1/indicators/cache/invalidate':
            self.handle_indicators_invalidate_cache()
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
        elif path == '/api/v1/tax-statements/process':
            self.handle_process_tax_statement_file()
            return
        elif path == '/api/v1/payroll/upload-csv':
            self.handle_upload_payroll_csv()  # 🆕 Novo endpoint para CSVs da pasta Analiticos
            return
        elif path == '/api/v1/benefits/upload-xlsx':
            self.handle_upload_benefits_xlsx()  # Upload de XLSX de benefícios
            return
        elif path == '/api/v1/timecard/upload-xlsx':
            self.handle_upload_timecard_xlsx()  # Upload de XLSX de cartão ponto
            return
        elif path == '/api/v1/uploads/csv':
            self.handle_csv_file_upload()  # 🆕 Upload de arquivo CSV
            return
        elif path == '/api/v1/payrolls/periods':
            self.handle_list_payroll_periods()
        elif path == '/api/v1/payrolls/export-batch':
            self.handle_export_payroll_batch()
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
        elif path.startswith('/api/v1/queue/') and path.endswith('/pause'):
            queue_id = path.split('/')[-2]
            self.handle_pause_queue(queue_id)
        elif path.startswith('/api/v1/queue/') and path.endswith('/resume'):
            queue_id = path.split('/')[-2]
            self.handle_resume_queue(queue_id)
        else:
            self.send_json_response({"error": "Endpoint não encontrado"}, 404)
    
    def do_PUT(self):
        """Handle PUT requests"""
        path = urllib.parse.urlparse(self.path).path
        print(f"🔄 PUT recebido: {path}")
        
        if path.startswith('/api/v1/employees/'):
            # Verificar primeiro se é rota de leaves
            parts = path.split('/')
            if len(parts) >= 7 and parts[5] == 'leaves':
                employee_id = parts[4]
                leave_id = parts[6]
                print(f"✅ PUT para leaves/{leave_id} do employee_id: {employee_id}")
                self.handle_update_employee_leave(employee_id, leave_id)
                return
            
            # Senão, é update de employee
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
            # Verificar primeiro se é rota de leaves
            parts = path.split('/')
            if len(parts) >= 7 and parts[5] == 'leaves':
                employee_id = parts[4]
                leave_id = parts[6]
                print(f"✅ DELETE para leaves/{leave_id} do employee_id: {employee_id}")
                self.handle_delete_employee_leave(employee_id, leave_id)
                return
            
            # Senão, é delete de employee
            employee_id = path.split('/')[-1]
            self.handle_delete_employee(employee_id)
        elif path.startswith('/api/v1/users/'):
            user_id = path.split('/')[-1]
            self.handle_delete_user(user_id)
        elif path.startswith('/api/v1/payroll/periods/'):
            period_id = path.split('/')[-1]
            self.handle_delete_payroll_period(period_id)
        elif path.startswith('/api/v1/benefits/periods/'):
            period_id = path.split('/')[-1]
            self.handle_delete_benefits_period(period_id)
        elif path.startswith('/api/v1/timecard/periods/'):
            period_id = path.split('/')[-1]
            self.handle_delete_timecard_period(period_id)
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
        """Lista de holerites processados (NOVO: busca em processed/ e subpastas)"""
        try:
            import os
            import glob
            
            # NOVO: Diretório processed/ com subpastas organizadas
            processed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed')
            
            # Fallback: pasta antiga para compatibilidade
            legacy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'holerites_formatados_final')
            
            if not os.path.exists(processed_dir) and not os.path.exists(legacy_dir):
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
            
            # Buscar todos os PDFs recursivamente (processed/** e legacy)
            pdf_files = []
            if os.path.exists(processed_dir):
                pdf_files.extend(glob.glob(os.path.join(processed_dir, '**', '*.pdf'), recursive=True))
            if os.path.exists(legacy_dir):
                pdf_files.extend(glob.glob(os.path.join(legacy_dir, '*.pdf')))
            
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
                folder_name = os.path.basename(os.path.dirname(pdf_path))
                
                # Extrair unique_id e month_year baseado no formato
                if filename.startswith('EN_'):  # NOVO FORMATO: EN_MATRICULA_TIPO_MES_ANO.pdf
                    parts = filename.replace('.pdf', '').split('_')
                    unique_id = parts[1] if len(parts) > 1 else 'unknown'  # Matrícula (sem zeros à esquerda)
                    
                    # Adicionar zeros à esquerda para busca (formato completo: 005900169)
                    if unique_id.isdigit() and len(unique_id) < 9:
                        unique_id = unique_id.zfill(9)
                    
                    # Extrair mês/ano: EN_MATRICULA_TIPO_MES_ANO.pdf
                    if len(parts) >= 5:
                        month_num = parts[3].zfill(2)  # Mês
                        year = parts[4]  # Ano
                        month_year = f"{year}-{month_num}"  # Formato YYYY-MM
                    else:
                        month_year = 'desconhecido'
                else:  # FORMATO ANTIGO: XXXXXXXXX_holerite_mes_ano.pdf
                    parts = filename.split('_')
                    unique_id = parts[0] if parts else 'unknown'
                    
                    month_year = 'desconhecido'
                    if len(parts) >= 4:
                        month_name = parts[2].lower()
                        year = parts[3].replace('.pdf', '')
                        
                        month_map = {
                            'janeiro': '01', 'fevereiro': '02', 'marco': '03', 'abril': '04',
                            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                        }
                        month_num = month_map.get(month_name, '00')
                        month_year = f"{year}-{month_num}"
                
                # Buscar colaborador associado
                employee = employees_by_id.get(unique_id)
                
                file_info = {
                    "filename": filename,
                    "unique_id": unique_id,
                    "month_year": month_year,
                    "folder": folder_name,  # Pasta onde está (ex: Mensal_11_2025)
                    "filepath": pdf_path,  # Caminho completo para envio
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

    # ===== HANDLERS DE AFASTAMENTOS (LEAVES) =====
    
    def handle_get_employee_leaves(self, employee_id):
        """Listar todos os afastamentos de um funcionário"""
        try:
            print(f"📋 Buscando afastamentos do funcionário ID {employee_id}")
            
            if SessionLocal:
                from app.models import LeaveRecord, Employee
                
                db = SessionLocal()
                
                # Buscar funcionário
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Buscar afastamentos
                leaves = db.query(LeaveRecord).filter(
                    LeaveRecord.employee_id == employee.id
                ).order_by(LeaveRecord.start_date.desc()).all()
                
                leaves_data = [{
                    'id': leave.id,
                    'leave_type': leave.leave_type,
                    'start_date': leave.start_date.isoformat() if leave.start_date else None,
                    'end_date': leave.end_date.isoformat() if leave.end_date else None,
                    'days': leave.days,
                    'notes': leave.notes,
                    'created_at': leave.created_at.isoformat() if leave.created_at else None
                } for leave in leaves]
                
                db.close()
                
                self.send_json_response(leaves_data, 200)
                print(f"✅ Retornados {len(leaves_data)} afastamentos")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar afastamentos: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_get_employee_leave_detail(self, employee_id, leave_id):
        """Buscar detalhes de um afastamento específico"""
        try:
            print(f"📄 Buscando afastamento ID {leave_id} do funcionário {employee_id}")
            
            if SessionLocal:
                from app.models import LeaveRecord, Employee
                
                db = SessionLocal()
                
                # Buscar funcionário
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Buscar afastamento
                leave = db.query(LeaveRecord).filter(
                    LeaveRecord.id == leave_id,
                    LeaveRecord.employee_id == employee.id
                ).first()
                
                if not leave:
                    db.close()
                    self.send_json_response({"error": "Afastamento não encontrado"}, 404)
                    return
                
                leave_data = {
                    'id': leave.id,
                    'leave_type': leave.leave_type,
                    'start_date': leave.start_date.isoformat() if leave.start_date else None,
                    'end_date': leave.end_date.isoformat() if leave.end_date else None,
                    'days': leave.days,
                    'notes': leave.notes,
                    'created_at': leave.created_at.isoformat() if leave.created_at else None
                }
                
                db.close()
                
                self.send_json_response(leave_data, 200)
                print(f"✅ Afastamento encontrado")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar afastamento: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_create_employee_leave(self, employee_id):
        """Criar novo afastamento para um funcionário"""
        try:
            data = self.get_request_data()
            print(f"➕ Criando afastamento para funcionário ID {employee_id}: {data}")
            
            if SessionLocal:
                from app.models import LeaveRecord, Employee
                from datetime import datetime
                
                db = SessionLocal()
                
                # Buscar funcionário
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Validar campos obrigatórios
                if not data.get('leave_type') or not data.get('start_date') or not data.get('end_date'):
                    db.close()
                    self.send_json_response({
                        "error": "Campos obrigatórios: leave_type, start_date, end_date"
                    }, 400)
                    return
                
                # Criar afastamento
                leave = LeaveRecord(
                    employee_id=employee.id,
                    unified_code=employee.unique_id,
                    leave_type=data['leave_type'],
                    start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                    end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
                    days=float(data.get('days', 0)) if data.get('days') else None,
                    notes=data.get('notes'),
                    created_at=datetime.now()
                )
                
                db.add(leave)
                db.commit()
                db.refresh(leave)
                
                leave_data = {
                    'id': leave.id,
                    'leave_type': leave.leave_type,
                    'start_date': leave.start_date.isoformat(),
                    'end_date': leave.end_date.isoformat(),
                    'days': leave.days,
                    'notes': leave.notes
                }
                
                db.close()
                
                self.send_json_response(leave_data, 201)
                print(f"✅ Afastamento criado com sucesso ID {leave.id}")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao criar afastamento: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_update_employee_leave(self, employee_id, leave_id):
        """Atualizar afastamento existente"""
        try:
            data = self.get_request_data()
            print(f"🔄 Atualizando afastamento ID {leave_id} do funcionário {employee_id}: {data}")
            
            if SessionLocal:
                from app.models import LeaveRecord, Employee
                from datetime import datetime
                
                db = SessionLocal()
                
                # Buscar funcionário
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Buscar afastamento
                leave = db.query(LeaveRecord).filter(
                    LeaveRecord.id == leave_id,
                    LeaveRecord.employee_id == employee.id
                ).first()
                
                if not leave:
                    db.close()
                    self.send_json_response({"error": "Afastamento não encontrado"}, 404)
                    return
                
                # Atualizar campos
                if 'leave_type' in data:
                    leave.leave_type = data['leave_type']
                if 'start_date' in data:
                    leave.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                if 'end_date' in data:
                    leave.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
                if 'days' in data:
                    leave.days = float(data['days']) if data['days'] else None
                if 'notes' in data:
                    leave.notes = data['notes']
                
                db.commit()
                db.refresh(leave)
                
                leave_data = {
                    'id': leave.id,
                    'leave_type': leave.leave_type,
                    'start_date': leave.start_date.isoformat(),
                    'end_date': leave.end_date.isoformat(),
                    'days': leave.days,
                    'notes': leave.notes
                }
                
                db.close()
                
                self.send_json_response(leave_data, 200)
                print(f"✅ Afastamento atualizado com sucesso")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao atualizar afastamento: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_delete_employee_leave(self, employee_id, leave_id):
        """Deletar afastamento"""
        try:
            print(f"🗑️ Deletando afastamento ID {leave_id} do funcionário {employee_id}")
            
            if SessionLocal:
                from app.models import LeaveRecord, Employee
                
                db = SessionLocal()
                
                # Buscar funcionário
                employee = db.query(Employee).filter(
                    (Employee.id == employee_id) | (Employee.unique_id == employee_id)
                ).first()
                
                if not employee:
                    db.close()
                    self.send_json_response({"error": "Funcionário não encontrado"}, 404)
                    return
                
                # Buscar afastamento
                leave = db.query(LeaveRecord).filter(
                    LeaveRecord.id == leave_id,
                    LeaveRecord.employee_id == employee.id
                ).first()
                
                if not leave:
                    db.close()
                    self.send_json_response({"error": "Afastamento não encontrado"}, 404)
                    return
                
                # Deletar
                db.delete(leave)
                db.commit()
                db.close()
                
                self.send_json_response({"message": "Afastamento excluído com sucesso"}, 200)
                print(f"✅ Afastamento deletado com sucesso")
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar afastamento: {e}")
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    # ===== FIM DOS HANDLERS DE AFASTAMENTOS =====

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
                    # Mapear código da empresa para nome
                    company_name = "Empreendimentos" if period.company == "0060" else "Infraestrutura" if period.company == "0059" else period.company
                    
                    periods_data.append({
                        "id": period.id,
                        "year": period.year,
                        "month": period.month,
                        "period_name": period.period_name,
                        "company": period.company,
                        "company_name": company_name,
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
    
    def handle_delete_payroll_period(self, period_id: str):
        """Deleta um período de folha e todos os dados relacionados"""
        try:
            print(f"🗑️ Deletando período ID: {period_id}")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                # Primeiro, verificar se o período existe e buscar informações
                result = conn.execute(
                    text("SELECT period_name, year, month FROM payroll_periods WHERE id = :period_id"),
                    {"period_id": int(period_id)}
                )
                period_info = result.fetchone()
                
                if not period_info:
                    self.send_json_response({
                        "success": False,
                        "error": f"Período {period_id} não encontrado"
                    }, 404)
                    return
                
                period_name = period_info[0]
                
                # Contar quantos registros serão deletados
                count_result = conn.execute(
                    text("SELECT COUNT(*) FROM payroll_data WHERE period_id = :period_id"),
                    {"period_id": int(period_id)}
                )
                total_records = count_result.fetchone()[0]
                
                # 1. Deletar logs de processamento associados ao período
                logs_result = conn.execute(
                    text("DELETE FROM payroll_processing_logs WHERE period_id = :period_id"),
                    {"period_id": int(period_id)}
                )
                deleted_logs = logs_result.rowcount
                print(f"🗑️ {deleted_logs} log(s) de processamento deletado(s)")
                
                # 2. Deletar os dados de folha (relacionamento cascade)
                conn.execute(
                    text("DELETE FROM payroll_data WHERE period_id = :period_id"),
                    {"period_id": int(period_id)}
                )
                
                # 3. Deletar o período
                conn.execute(
                    text("DELETE FROM payroll_periods WHERE id = :period_id"),
                    {"period_id": int(period_id)}
                )
                
                conn.commit()
                
                print(f"✅ Período '{period_name}' deletado com sucesso ({total_records} registros removidos)")
                
                # 📝 REGISTRAR LOG DO SISTEMA - PERÍODO DELETADO
                try:
                    db = SessionLocal()
                    try:
                        from app.models.system_log import SystemLog, LogLevel, LogCategory
                        
                        # Obter user_id do usuário autenticado
                        user_id = None
                        authenticated_user = self.get_authenticated_user(db)
                        if authenticated_user:
                            user_id = authenticated_user.id
                        
                        log_entry = SystemLog(
                            level=LogLevel.WARNING,
                            category=LogCategory.PAYROLL,
                            message=f"Período de folha deletado: {period_name}",
                            details=f"Registros deletados: {total_records}, Logs removidos: {deleted_logs}",
                            user_id=user_id,
                            entity_type='PayrollPeriod',
                            entity_id=str(period_id)
                        )
                        db.add(log_entry)
                        db.commit()
                        print(f"📝 Log de deleção registrado")
                    finally:
                        db.close()
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log: {log_error}")
                
                self.send_json_response({
                    "success": True,
                    "message": f"Período '{period_name}' deletado com sucesso",
                    "deleted_records": total_records
                })
                
        except Exception as e:
            print(f"❌ Erro ao deletar período: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro ao deletar período: {str(e)}"
            }, 500)
    
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
    
    def handle_period_comparison(self):
        """Retorna comparativo de períodos de folha"""
        try:
            # Obter parâmetros da query string
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            company = query_params.get('company', ['all'])[0]
            period_filter = query_params.get('period', ['all'])[0]  # mensal, 13, all
            start_month = query_params.get('start_month', [None])[0]  # formato: YYYY-MM
            end_month = query_params.get('end_month', [None])[0]  # formato: YYYY-MM
            
            if SessionLocal:
                from app.models.payroll import PayrollPeriod, PayrollData
                from app.models.employee import Employee
                from sqlalchemy import func, or_, and_
                from decimal import Decimal
                from collections import defaultdict
                
                db = SessionLocal()
                
                # Query para buscar todos os períodos
                periods_query = db.query(PayrollPeriod)
                
                # Filtrar por tipo de período se especificado
                if period_filter != 'all':
                    if period_filter == 'mensal':
                        periods_query = periods_query.filter(
                            ~PayrollPeriod.period_name.ilike('%13%')
                        )
                    elif period_filter == '13':
                        periods_query = periods_query.filter(
                            PayrollPeriod.period_name.ilike('%13%')
                        )
                
                # Filtrar por intervalo de datas se especificado
                if start_month:
                    start_year, start_mon = map(int, start_month.split('-'))
                    periods_query = periods_query.filter(
                        or_(
                            PayrollPeriod.year > start_year,
                            and_(
                                PayrollPeriod.year == start_year,
                                PayrollPeriod.month >= start_mon
                            )
                        )
                    )
                
                if end_month:
                    end_year, end_mon = map(int, end_month.split('-'))
                    periods_query = periods_query.filter(
                        or_(
                            PayrollPeriod.year < end_year,
                            and_(
                                PayrollPeriod.year == end_year,
                                PayrollPeriod.month <= end_mon
                            )
                        )
                    )
                
                periods = periods_query.all()
                
                # Agrupar por ano/mês
                grouped_data = defaultdict(lambda: {
                    'employee_count': 0,
                    'total_earnings': Decimal('0'),
                    'total_deductions': Decimal('0'),
                    'total_net': Decimal('0'),
                    'period_names': set(),
                    'employee_ids': set()
                })
                
                for period in periods:
                    key = (period.year, period.month)
                    
                    # Query para dados de folha do período
                    payroll_query = db.query(PayrollData).filter(
                        PayrollData.period_id == period.id
                    )
                    
                    # Filtrar por empresa se especificado
                    if company != 'all':
                        employee_ids = db.query(Employee.id).filter(
                            Employee.company == company
                        ).all()
                        employee_ids = [emp[0] for emp in employee_ids]
                        payroll_query = payroll_query.filter(
                            PayrollData.employee_id.in_(employee_ids)
                        )
                    
                    payroll_records = payroll_query.all()
                    
                    # Adicionar period_name ao grupo
                    grouped_data[key]['period_names'].add(period.period_name)
                    
                    # Calcular totais
                    for record in payroll_records:
                        # Rastrear employees únicos
                        grouped_data[key]['employee_ids'].add(record.employee_id)
                        
                        # Somar valores
                        if record.gross_salary:
                            grouped_data[key]['total_earnings'] += Decimal(str(record.gross_salary))
                        
                        if record.net_salary:
                            grouped_data[key]['total_net'] += Decimal(str(record.net_salary))
                
                # Converter para lista ordenada (mais recente primeiro)
                periods_data = []
                for (year, month), data in sorted(grouped_data.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True):
                    total_deductions = data['total_earnings'] - data['total_net']
                    
                    periods_data.append({
                        "year": year,
                        "month": month,
                        "period_names": ', '.join(sorted(data['period_names'])),
                        "employee_count": len(data['employee_ids']),
                        "total_earnings": float(data['total_earnings']),
                        "total_deductions": float(total_deductions),
                        "total_net": float(data['total_net'])
                    })
                
                db.close()
                self.send_json_response({"periods": periods_data})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar comparativo de períodos: {e}")
            import traceback
            traceback.print_exc()
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
        """Processar arquivo de folha de pagamento - NOVO FORMATO: EN_MATRICULA_TIPO_MES_ANO.pdf"""
        try:
            print("📄 Iniciando processamento de holerites (NOVO FORMATO)...")
            
            # Obter dados da requisição
            data = self.get_request_data()
            uploaded_file = data.get('uploadedFile', {})
            payroll_type = data.get('payrollType', '11')  # Padrão: Mensal
            month = int(data.get('month', datetime.now().month))
            year = int(data.get('year', datetime.now().year))
            
            print(f"📋 NOVO FORMATO - Tipo: {payroll_type}, Mês: {month}, Ano: {year}")
            
            if not uploaded_file:
                self.send_json_response({"error": "Nenhum arquivo foi enviado"}, 400)
                return
            
            filepath = uploaded_file.get('filepath')
            filename = uploaded_file.get('filename')
            
            if not filepath or not filename:
                self.send_json_response({"error": "Dados do arquivo incompletos"}, 400)
                return
            
            print(f"📂 Processando arquivo com novo formato: {filepath}")
            
            # Verificar se arquivo existe
            import os
            if not os.path.exists(filepath):
                self.send_json_response({"error": f"Arquivo não encontrado: {filepath}"}, 404)
                return
            
            # Importar novo serviço de formatação
            from app.services.payroll_formatter import segment_pdf_by_employee
            
            # Carregar dados dos funcionários
            employees_data = load_employees_data()
            employees_list = employees_data.get('employees', [])
            
            if not employees_list:
                self.send_json_response({"error": "Nenhum funcionário encontrado no banco de dados"}, 500)
                return
            
            print(f"👥 {len(employees_list)} funcionários carregados")
            
            # Processar PDF com novo formato
            result = segment_pdf_by_employee(
                pdf_path=filepath,
                employees_data=employees_list,
                payroll_type=payroll_type,
                month=month,
                year=year
            )
            
            if result['success']:
                # Registrar processamento no banco de dados
                try:
                    export_info = result.get('export_info', {})
                    
                    # Log de processamento bem-sucedido
                    log_system_event(
                        event_type='payroll_processing',
                        description=f"PDF processado (Novo Formato): {filename}",
                        details={
                            'original_file': filename,
                            'payroll_type': payroll_type,
                            'month': month,
                            'year': year,
                            'processed_count': result['processed_count'],
                            'folder': export_info.get('folder', ''),
                            'files_generated': [f['filename'] for f in result['files'][:10]],  # Primeiros 10
                            'errors': result.get('errors', [])
                        },
                        severity='info',
                        user_id=None  # TODO: Pegar do token JWT
                    )
                    
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log: {log_error}")
                
                print(f"✅ Processamento concluído: {result['processed_count']} holerites gerados")
                print(f"📁 Pasta: {export_info.get('folder', '')}")
                
                self.send_json_response({
                    "success": True,
                    "message": f"PDF processado com sucesso (Novo Formato)",
                    "processed_count": result['processed_count'],
                    "files": result['files'],
                    "export_info": export_info,
                    "errors": result.get('errors', [])
                }, 200)
            else:
                print(f"❌ Erro no processamento: {result.get('error', 'Erro desconhecido')}")
                
                # Registrar erro no log
                try:
                    log_system_event(
                        event_type='payroll_processing_error',
                        description=f"Erro ao processar PDF (Novo Formato): {filename}",
                        details={
                            'original_file': filename,
                            'payroll_type': payroll_type,
                            'month': month,
                            'year': year,
                            'error': result.get('error', 'Erro desconhecido'),
                            'errors': result.get('errors', [])
                        },
                        severity='error',
                        user_id=None
                    )
                except Exception as log_error:
                    print(f"⚠️ Erro ao registrar log de erro: {log_error}")
                
                self.send_json_response({
                    "error": result.get('error', 'Erro desconhecido'),
                    "errors": result.get('errors', [])
                }, 500)
                
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_upload_payroll_csv(self):
        """
        🆕 Processa CSV de folha de pagamento (formato Analiticos)
        Endpoint: POST /api/v1/payroll/upload-csv
        
        Body: {
            "file_path": "/caminho/para/01-2024.CSV",
            "division_code": "0060",  # 0060=Empreendimentos, 0059=Infraestrutura
            "auto_create_employees": false
        }
        """
        try:
            print("📊 === UPLOAD DE CSV DE FOLHA (ANALITICOS) ===")
            
            # Obter dados da requisição
            data = self.get_request_data()
            file_path = data.get('file_path')
            division_code = data.get('division_code', '0060')
            auto_create_employees = data.get('auto_create_employees', False)
            
            # Validar parâmetros
            if not file_path:
                self.send_json_response({
                    "success": False,
                    "error": "Parâmetro 'file_path' obrigatório"
                }, 400)
                return
            
            # Validar código da divisão
            if division_code not in ['0060', '0059']:
                self.send_json_response({
                    "success": False,
                    "error": "division_code deve ser '0060' (Empreendimentos) ou '0059' (Infraestrutura)"
                }, 400)
                return
            
            print(f"📁 Arquivo: {file_path}")
            print(f"🏢 Divisão: {division_code} ({'Empreendimentos' if division_code == '0060' else 'Infraestrutura'})")
            print(f"👤 Auto-criar funcionários: {auto_create_employees}")
            
            # Criar sessão do banco
            db = SessionLocal()
            
            # Obter user_id do usuário autenticado
            user_id = None
            authenticated_user = self.get_authenticated_user(db)
            if authenticated_user:
                user_id = authenticated_user.id
                print(f"👤 Processado por: {authenticated_user.username} (ID: {user_id})")
            else:
                print("⚠️ Upload sem usuário autenticado (processamento do sistema)")
            
            # Criar serviço de processamento
            from app.services.payroll_csv_processor import PayrollCSVProcessor
            try:
                processor = PayrollCSVProcessor(db, user_id=user_id)
                
                # Processar CSV
                result = processor.process_csv_file(
                    file_path=file_path,
                    division_code=division_code,
                    auto_create_employees=auto_create_employees
                )
                
                # Retornar resultado
                if result['success']:
                    print(f"✅ CSV processado com sucesso!")
                    print(f"   📊 Estatísticas: {result['stats']}")
                    self.send_json_response(result, 200)
                else:
                    print(f"❌ Erro ao processar CSV: {result.get('error')}")
                    self.send_json_response(result, 400)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro crítico ao processar CSV: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }, 500)
    
    def handle_csv_file_upload(self):
        """Upload simples de arquivo CSV para o servidor"""
        print("🚀 INICIANDO handle_csv_file_upload")
        try:
            print("📤 Upload de arquivo CSV...")
            print(f"📋 Headers: {dict(self.headers)}")
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                return
            
            # Get boundary
            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break
            
            if not boundary:
                self.send_json_response({"error": "Boundary não encontrado"}, 400)
                return
            
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Simple multipart parser
            parts = body.split(f'--{boundary}'.encode())
            file_data = None
            filename = None
            
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Extract filename
                    disp_line = part.split(b'\r\n')[1].decode('utf-8', errors='ignore')
                    if 'filename=' in disp_line:
                        filename = disp_line.split('filename=')[1].strip('"').strip()
                    
                    # Extract file data (after double CRLF)
                    if b'\r\n\r\n' in part:
                        file_data = part.split(b'\r\n\r\n', 1)[1]
                        # Remove trailing CRLF
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                    break
            
            if not file_data or not filename:
                self.send_json_response({"error": "Arquivo não encontrado no upload"}, 400)
                return
            
            # Validar extensão
            if not filename.lower().endswith('.csv'):
                self.send_json_response({"error": "Apenas arquivos CSV são aceitos"}, 400)
                return
            
            # Salvar arquivo temporariamente
            import os
            import time
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{filename}"
            upload_dir = 'uploads'
            
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            file_path = os.path.join(upload_dir, safe_filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            print(f"✅ Arquivo salvo: {file_path}")
            
            # Retornar caminho absoluto
            abs_path = os.path.abspath(file_path)
            
            self.send_json_response({
                "success": True,
                "file_path": abs_path,
                "filename": filename,
                "size": len(file_data)
            })
            
        except Exception as e:
            print(f"❌ Erro no upload: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro no upload: {str(e)}"
            }, 500)
    
    def handle_payroll_statistics(self):
        """Retorna estatísticas consolidadas dos dados CSV processados (versão simplificada)"""
        try:
            print("📊 Carregando estatísticas de folha de pagamento...")
            
            from app.services.payroll_statistics import calculate_payroll_statistics
            
            # Usar a variável global SessionLocal
            global SessionLocal
            if not SessionLocal:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            # Parse query parameters (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores)
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            
            # Empresas (0060 = Empreendimentos, 0059 = Infraestrutura)
            companies = None
            if 'companies' in query_params and query_params['companies']:
                comp_str = query_params['companies'][0]
                companies = [c.strip() for c in comp_str.split(',') if c.strip()]
                print(f"   Empresas selecionadas: {companies}")
            
            # Converter anos
            years = None
            if 'years' in query_params and query_params['years']:
                years_str = query_params['years'][0]
                years = [int(y.strip()) for y in years_str.split(',') if y.strip()]
                print(f"   Anos selecionados: {years}")
            
            # Converter meses
            months = None
            if 'months' in query_params and query_params['months']:
                months_str = query_params['months'][0]
                months = [int(m.strip()) for m in months_str.split(',') if m.strip()]
                print(f"   Meses selecionados: {months}")
            
            # Converter período IDs de string para lista de inteiros
            period_ids = None
            if 'periods' in query_params and query_params['periods']:
                periods_str = query_params['periods'][0] if isinstance(query_params['periods'], list) else query_params['periods']
                period_ids = [int(p.strip()) for p in periods_str.split(',') if p.strip()]
                print(f"   Períodos selecionados: {period_ids}")
            
            # Departamentos
            department_ids = None
            if 'departments' in query_params and query_params['departments']:
                dept_str = query_params['departments'][0]
                department_ids = [d.strip() for d in dept_str.split(',') if d.strip()]
                print(f"   Departamentos selecionados: {department_ids}")
            
            # Colaboradores
            employee_ids = None
            if 'employees' in query_params and query_params['employees']:
                emp_str = query_params['employees'][0]
                employee_ids = [int(e.strip()) for e in emp_str.split(',') if e.strip()]
                print(f"   Colaboradores selecionados: {employee_ids}")
            
            # Criar sessão do banco
            db = SessionLocal()
            try:
                # Chamar a nova função simplificada (com ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores)
                result = calculate_payroll_statistics(
                    db_session=db,
                    companies=companies,
                    years=years,
                    months=months,
                    period_ids=period_ids,
                    department_ids=department_ids,
                    employee_ids=employee_ids
                )
                
                print(f"✅ Estatísticas calculadas com sucesso")
                self.send_json_response(result)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao carregar estatísticas: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro ao carregar estatísticas: {str(e)}"
            }, 500)
    
    def handle_payroll_employees(self):
        """Lista colaboradores que têm dados de folha de pagamento"""
        try:
            print("👥 Carregando lista de colaboradores...")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT
                        e.id,
                        e.unique_id,
                        e.name,
                        COALESCE(e.department, e.position, 'Não especificado') as department,
                        e.position,
                        COUNT(DISTINCT pd.period_id) as total_periods
                    FROM employees e
                    INNER JOIN payroll_data pd ON pd.employee_id = e.id
                    GROUP BY e.id, e.unique_id, e.name, e.department, e.position
                    ORDER BY e.name
                """))
                
                employees = []
                for row in result:
                    employees.append({
                        "id": row[0],
                        "unique_id": row[1],
                        "name": row[2],
                        "department": row[3],
                        "position": row[4] or "Não especificado",
                        "total_periods": row[5]
                    })
                
                print(f"✅ {len(employees)} colaboradores encontrados")
                self.send_json_response({
                    "success": True,
                    "employees": employees
                })
                
        except Exception as e:
            print(f"❌ Erro ao listar colaboradores: {e}")
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_divisions(self):
        """Lista departamentos disponíveis"""
        try:
            print("🏢 Carregando departamentos...")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT
                        COALESCE(e.department, 'Sem departamento cadastrado') as dept,
                        COUNT(DISTINCT e.id) as total_employees
                    FROM employees e
                    INNER JOIN payroll_data pd ON pd.employee_id = e.id
                    GROUP BY COALESCE(e.department, 'Sem departamento cadastrado')
                    ORDER BY dept
                """))
                
                departments = []
                for row in result:
                    departments.append({
                        "name": row[0],
                        "total_employees": row[1]
                    })
                
                print(f"✅ {len(departments)} departamentos encontrados")
                self.send_json_response({
                    "success": True,
                    "departments": departments
                })
                
        except Exception as e:
            print(f"❌ Erro ao listar departamentos: {e}")
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_companies(self):
        """Lista empresas disponíveis"""
        try:
            print("🏢 Carregando empresas disponíveis...")
            
            companies = [
                {
                    "code": "0060",
                    "name": "Empreendimentos",
                    "full_name": "0060 - Empreendimentos"
                },
                {
                    "code": "0059",
                    "name": "Infraestrutura",
                    "full_name": "0059 - Infraestrutura"
                }
            ]
            
            print(f"✅ {len(companies)} empresas disponíveis")
            self.send_json_response({
                "success": True,
                "companies": companies
            })
            
        except Exception as e:
            print(f"❌ Erro ao listar empresas: {e}")
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_years(self):
        """Lista anos disponíveis nos períodos de folha"""
        try:
            print("📅 Carregando anos disponíveis...")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT year
                    FROM payroll_periods
                    WHERE year IS NOT NULL
                    ORDER BY year DESC
                """))
                
                years = [row[0] for row in result]
                
                print(f"✅ {len(years)} anos encontrados")
                self.send_json_response({
                    "success": True,
                    "years": years
                })
                
        except Exception as e:
            print(f"❌ Erro ao listar anos: {e}")
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_months(self):
        """Lista meses disponíveis nos períodos de folha"""
        try:
            print("📅 Carregando meses disponíveis...")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            # Mapeamento de meses
            month_names = {
                1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
                5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
            }
            
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT month
                    FROM payroll_periods
                    WHERE month IS NOT NULL
                    ORDER BY month
                """))
                
                months = []
                for row in result:
                    month_num = row[0]
                    months.append({
                        "number": month_num,
                        "name": month_names.get(month_num, f"Mês {month_num}")
                    })
                
                print(f"✅ {len(months)} meses encontrados")
                self.send_json_response({
                    "success": True,
                    "months": months
                })
                
        except Exception as e:
            print(f"❌ Erro ao listar meses: {e}")
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_statistics_filtered(self):
        """Estatísticas de folha com filtros (períodos, setores, colaboradores)"""
        try:
            # Parse query parameters
            from urllib.parse import parse_qs
            query_string = self.path.split('?')[1] if '?' in self.path else ''
            params = parse_qs(query_string)
            
            # Extrair filtros
            period_ids = params.get('periods', [])
            if period_ids and period_ids[0]:
                period_ids = [int(p) for p in period_ids[0].split(',')]
            else:
                period_ids = []
            
            divisions = params.get('divisions', [])
            if divisions and divisions[0]:
                divisions = divisions[0].split(',')
            else:
                divisions = []
            
            employee_ids = params.get('employees', [])
            if employee_ids and employee_ids[0]:
                employee_ids = [int(e) for e in employee_ids[0].split(',')]
            else:
                employee_ids = []
            
            print(f"📊 Filtros aplicados: períodos={period_ids}, setores={divisions}, colaboradores={employee_ids}")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                # Construir WHERE clauses
                where_clauses = []
                query_params = {}
                
                if period_ids:
                    placeholders = ', '.join([f':period_{i}' for i in range(len(period_ids))])
                    where_clauses.append(f"pd.period_id IN ({placeholders})")
                    for i, pid in enumerate(period_ids):
                        query_params[f'period_{i}'] = pid
                
                if divisions:
                    placeholders = ', '.join([f':div_{i}' for i in range(len(divisions))])
                    where_clauses.append(f"COALESCE(e.department, e.position, 'Não especificado') IN ({placeholders})")
                    for i, div in enumerate(divisions):
                        query_params[f'div_{i}'] = div
                
                if employee_ids:
                    placeholders = ', '.join([f':emp_{i}' for i in range(len(employee_ids))])
                    where_clauses.append(f"e.id IN ({placeholders})")
                    for i, eid in enumerate(employee_ids):
                        query_params[f'emp_{i}'] = eid
                
                where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
                
                # Query estatísticas agregadas
                stats_query = f"""
                    SELECT 
                        COUNT(DISTINCT e.id) as total_employees,
                        COUNT(DISTINCT pd.period_id) as total_periods,
                        COALESCE(SUM((additional_data->>'Valor Salário')::numeric), 0) as total_valor_salario,
                        COALESCE(AVG((additional_data->>'Valor Salário')::numeric), 0) as avg_salario,
                        COALESCE(AVG((additional_data->>'Líquido de Cálculo')::numeric), 0) as avg_liquido,
                        COALESCE(SUM((additional_data->>'Salário Mensal')::numeric), 0) as total_salario_mensal,
                        COALESCE(SUM((additional_data->>'Total de Proventos')::numeric), 0) as total_proventos,
                        COALESCE(SUM((additional_data->>'Total de Descontos')::numeric), 0) as total_descontos,
                        COALESCE(SUM((additional_data->>'Total de Vantagens')::numeric), 0) as total_vantagens,
                        COALESCE(SUM((additional_data->>'Líquido de Cálculo')::numeric), 0) as total_liquido,
                        COALESCE(SUM((deductions_data->>'INSS')::numeric), 0) as total_inss,
                        COALESCE(SUM((deductions_data->>'IRRF')::numeric), 0) as total_irrf,
                        COALESCE(SUM((deductions_data->>'FGTS')::numeric), 0) as total_fgts,
                        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_50_DIURNAS')::numeric), 0) as total_he_50_diurnas,
                        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_50_NOTURNAS')::numeric), 0) as total_he_50_noturnas,
                        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_60_DIURNAS')::numeric), 0) as total_he_60,
                        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_100_DIURNAS')::numeric), 0) as total_he_100_diurnas,
                        COALESCE(SUM((earnings_data->>'HORAS_EXTRAS_100_NOTURNAS')::numeric), 0) as total_he_100_noturnas,
                        COALESCE(SUM((earnings_data->>'ADICIONAL_NOTURNO')::numeric), 0) as total_adicional_noturno,
                        (
                            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO')::numeric), 0) + 
                            COALESCE(SUM((earnings_data->>'GRATIFICACAO_FUNCAO_20')::numeric), 0)
                        ) as total_gratificacoes,
                        -- 13º Salário - TODOS os componentes (Adiantamento Nov + Integral Dez + Proporcional + Indenizado)
                        (
                            COALESCE(SUM((earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_ADIANTAMENTO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_ADIANTAMENTO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_HE_ADIANTAMENTO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_INTEGRAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_INTEGRAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_INTEGRAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_HE_INTEGRAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_PROPORCIONAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_PROPORCIONAL_APP')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_PROPORCIONAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_PROPORCIONAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_HE_PROPORCIONAL')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_INDENIZADO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_COMPLEMENTAR')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_LIC_MATER')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_SALARIO_MATERNIDADE_GPS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_INDENIZADO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'13_MEDIA_HE_INDENIZADO')::numeric), 0)
                        ) as total_13_salario,
                        -- Férias - TODOS os componentes (Valor Base + 1/3 + Gratificações + Médias + Adiantamentos)
                        (
                            COALESCE(SUM((earnings_data->>'FERIAS_VALOR_BASE')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_VALOR_PROPORCIONAIS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_VALOR_VENCIDAS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_VALOR_APP')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_DIFERENCA')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MULTA_DOBRO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3_PROPORCIONAIS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3_VENCIDAS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3_APP')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ANTECIPACAO_1_3')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO_PROPORC')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS_PROPORC')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS_VENCIDAS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HE')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HE_PROPORC')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HE_VENCIDAS')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ADIANTAMENTO_PAGO')::numeric), 0) +
                            COALESCE(SUM((earnings_data->>'FERIAS_ABONO_ADIANTAMENTO')::numeric), 0)
                        ) as total_ferias_pagas,
                        -- 13º Salário - Componentes Agrupados
                        (COALESCE(SUM((earnings_data->>'13_SALARIO_ADIANTAMENTO')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_ADIANTAMENTO')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_ADIANTAMENTO')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_HE_ADIANTAMENTO')::numeric), 0)) as total_13_adiantamento,
                        (COALESCE(SUM((earnings_data->>'13_SALARIO_INTEGRAL')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_INTEGRAL')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_INTEGRAL')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_HE_INTEGRAL')::numeric), 0)) as total_13_integral,
                        (COALESCE(SUM((earnings_data->>'13_SALARIO_PROPORCIONAL')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_SALARIO_PROPORCIONAL_APP')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_GRATIFICACAO_PROPORCIONAL')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_PROPORCIONAL')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_HE_PROPORCIONAL')::numeric), 0)) as total_13_proporcional,
                        (COALESCE(SUM((earnings_data->>'13_SALARIO_INDENIZADO')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_EVENTOS_INDENIZADO')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_MEDIA_HE_INDENIZADO')::numeric), 0)) as total_13_indenizado,
                        (COALESCE(SUM((earnings_data->>'13_SALARIO_COMPLEMENTAR')::numeric), 0)) as total_13_complementar,
                        (COALESCE(SUM((earnings_data->>'13_SALARIO_LIC_MATER')::numeric), 0) + COALESCE(SUM((earnings_data->>'13_SALARIO_MATERNIDADE_GPS')::numeric), 0)) as total_13_maternidade,
                        -- Férias - Componentes Agrupados
                        (COALESCE(SUM((earnings_data->>'FERIAS_VALOR_BASE')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_VALOR_PROPORCIONAIS')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_VALOR_VENCIDAS')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_VALOR_APP')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_DIFERENCA')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_MULTA_DOBRO')::numeric), 0)) as total_ferias_valor_base,
                        (COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3_PROPORCIONAIS')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3_VENCIDAS')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_ABONO_1_3_APP')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_ANTECIPACAO_1_3')::numeric), 0)) as total_ferias_abono_1_3,
                        (COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_GRATIFICACAO_PROPORC')::numeric), 0)) as total_ferias_gratificacao,
                        (COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS_PROPORC')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_EVENTOS_VENCIDAS')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HE')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HE_PROPORC')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_MEDIA_HE_VENCIDAS')::numeric), 0)) as total_ferias_medias,
                        (COALESCE(SUM((earnings_data->>'FERIAS_ADIANTAMENTO_PAGO')::numeric), 0) + COALESCE(SUM((earnings_data->>'FERIAS_ABONO_ADIANTAMENTO')::numeric), 0)) as total_ferias_adiantamento,
                        -- Descontos de 13º (não mais desconto de férias!)
                        COALESCE(SUM((deductions_data->>'DESCONTO_13_ADIANTAMENTO')::numeric), 0) as total_desconto_13_adiantamento,
                        COALESCE(SUM((earnings_data->>'PERICULOSIDADE')::numeric), 0) as total_periculosidade,
                        (COALESCE(SUM((earnings_data->>'INSALUBRIDADE')::numeric), 0) + COALESCE(SUM((earnings_data->>'INSALUBRIDADE_NORMATIVO')::numeric), 0)) as total_insalubridade,
                        COALESCE(SUM((additional_data->>'Valor Salário')::numeric), 0) as total_valor_salario_2,
                        COALESCE(SUM((additional_data->>'Salário Mensal')::numeric), 0) as total_salario_mensal_2,
                        COALESCE(SUM((additional_data->>'Total de Proventos')::numeric), 0) as total_proventos_2,
                        COALESCE(SUM((additional_data->>'Total de Descontos')::numeric), 0) as total_descontos_2,
                        COALESCE(SUM((additional_data->>'Total de Vantagens')::numeric), 0) as total_vantagens_2,
                        COALESCE(SUM((additional_data->>'Líquido de Cálculo')::numeric), 0) as total_liquido_2,
                        COALESCE(AVG((additional_data->>'Valor Salário')::numeric), 0) as avg_salario_2,
                        COALESCE(AVG((additional_data->>'Líquido de Cálculo')::numeric), 0) as avg_liquido_2,
                        COALESCE(SUM((additional_data->>'Horas Extras 50% Diurnas')::numeric), 0) as total_he50_horas,
                        COALESCE(SUM((additional_data->>'Horas Normais Noturnas')::numeric), 0) as total_horas_noturnas,
                        COALESCE(SUM((benefits_data->>'PLANO_SAUDE')::numeric), 0) as total_plano_saude,
                        COALESCE(SUM((benefits_data->>'VALE_TRANSPORTE')::numeric), 0) as total_vale_transporte,
                        COUNT(CASE WHEN additional_data->>'Status' = 'Trabalhando' THEN 1 END) as trabalhando,
                        COUNT(CASE WHEN additional_data->>'Status' = 'Férias' THEN 1 END) as ferias,
                        COUNT(CASE WHEN 
                            additional_data->>'Status' LIKE '%Afastado%' OR
                            additional_data->>'Status' LIKE '%Auxílio Doença%' OR
                            additional_data->>'Status' LIKE '%Auxilio Doenca%' OR
                            additional_data->>'Status' LIKE '%Licença%' OR
                            additional_data->>'Status' LIKE '%Licenca%' OR
                            additional_data->>'Status' LIKE '%Paternidade%' OR
                            additional_data->>'Status' LIKE '%Maternidade%' OR
                            additional_data->>'Status' LIKE '%Acidente Trabalho%'
                        THEN 1 END) as afastados,
                        COUNT(CASE WHEN additional_data->>'Status' LIKE '%Demitido%' OR additional_data->>'Status' LIKE '%Rescisão%' THEN 1 END) as demitidos
                    FROM payroll_data pd
                    INNER JOIN employees e ON e.id = pd.employee_id
                    WHERE 1=1 {where_sql}
                """
                
                result = conn.execute(text(stats_query), query_params)
                row = result.fetchone()
                
                response = {
                    "success": True,
                    "filters": {
                        "periods": period_ids,
                        "divisions": divisions,
                        "employees": employee_ids
                    },
                    "stats": {
                        "total_employees": row[0] if row else 0,
                        "total_periods": row[1] if row else 0,
                        "total_valor_salario": float(row[2]) if row and row[2] else 0,
                        "avg_salario": float(row[3]) if row and row[3] else 0,
                        "avg_liquido": float(row[4]) if row and row[4] else 0,
                        "total_salario_mensal": float(row[5]) if row and row[5] else 0,
                        "total_proventos": float(row[6]) if row and row[6] else 0,
                        "total_descontos": float(row[7]) if row and row[7] else 0,
                        "total_vantagens": float(row[8]) if row and row[8] else 0,
                        "total_liquido": float(row[9]) if row and row[9] else 0,
                        "total_inss": float(row[10]) if row and row[10] else 0,
                        "total_irrf": float(row[11]) if row and row[11] else 0,
                        "total_fgts": float(row[12]) if row and row[12] else 0,
                        "total_he_50_diurnas": float(row[13]) if row and row[13] else 0,
                        "total_he_50_noturnas": float(row[14]) if row and row[14] else 0,
                        "total_he_60": float(row[15]) if row and row[15] else 0,
                        "total_he_100_diurnas": float(row[16]) if row and row[16] else 0,
                        "total_he_100_noturnas": float(row[17]) if row and row[17] else 0,
                        "total_adicional_noturno": float(row[18]) if row and row[18] else 0,
                        "total_gratificacoes": float(row[19]) if row and row[19] else 0,
                        # 13º Salário e Férias - TOTAIS CONSOLIDADOS
                        "total_13_salario": float(row[20]) if row and row[20] else 0,
                        "total_ferias_pagas": float(row[21]) if row and row[21] else 0,
                        # 13º Salário - Componentes detalhados (nova estrutura)
                        "total_13_adiantamento": float(row[22]) if row and row[22] else 0,
                        "total_13_integral": float(row[23]) if row and row[23] else 0,
                        "total_13_proporcional": float(row[24]) if row and row[24] else 0,
                        "total_13_indenizado": float(row[25]) if row and row[25] else 0,
                        "total_13_complementar": float(row[26]) if row and row[26] else 0,
                        "total_13_maternidade": float(row[27]) if row and row[27] else 0,
                        # Férias - Componentes detalhados (nova estrutura)
                        "total_ferias_valor_base": float(row[28]) if row and row[28] else 0,
                        "total_ferias_abono_1_3": float(row[29]) if row and row[29] else 0,
                        "total_ferias_gratificacao": float(row[30]) if row and row[30] else 0,
                        "total_ferias_medias": float(row[31]) if row and row[31] else 0,
                        "total_ferias_adiantamento": float(row[32]) if row and row[32] else 0,
                        # Descontos
                        "total_desconto_13_adiantamento": float(row[33]) if row and row[33] else 0,
                        # Outros campos
                        "total_periculosidade": float(row[34]) if row and row[34] else 0,
                        "total_insalubridade": float(row[35]) if row and row[35] else 0,
                        "total_he50_horas": float(row[44]) if row and row[44] else 0,
                        "total_horas_noturnas": float(row[45]) if row and row[45] else 0,
                        "total_plano_saude": float(row[46]) if row and row[46] else 0,
                        "total_vale_transporte": float(row[47]) if row and row[47] else 0,
                        "trabalhando": row[48] if row else 0,
                        "ferias": row[49] if row else 0,
                        "afastados": row[50] if row else 0,
                        "demitidos": row[51] if row else 0,
                        "contratados": 0,  # Será calculado se múltiplos períodos
                    }
                }
                
                # Se múltiplos períodos, calcular status baseado no PERÍODO MAIS RECENTE
                # Primeiro identificar qual é o período mais recente
                if period_ids and len(period_ids) > 1:
                    # Buscar o período mais recente (maior year/month)
                    most_recent_period_query = f"""
                        SELECT id, month, year
                        FROM payroll_periods
                        WHERE id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                        ORDER BY year DESC, month DESC
                        LIMIT 1
                    """
                    most_recent_result = conn.execute(text(most_recent_period_query), query_params)
                    most_recent_row = most_recent_result.fetchone()
                    
                    if most_recent_row:
                        most_recent_period_id = most_recent_row[0]
                        most_recent_month = most_recent_row[1]
                        most_recent_year = most_recent_row[2]
                        
                        # Contar status APENAS do período mais recente
                        status_query = f"""
                            SELECT 
                                COUNT(DISTINCT CASE WHEN additional_data->>'Status' = 'Trabalhando' THEN e.id END) as trabalhando,
                                COUNT(DISTINCT CASE WHEN additional_data->>'Status' = 'Férias' THEN e.id END) as ferias,
                                COUNT(DISTINCT CASE WHEN 
                                    additional_data->>'Status' LIKE '%Afastado%' OR
                                    additional_data->>'Status' LIKE '%Auxílio Doença%' OR
                                    additional_data->>'Status' LIKE '%Auxilio Doenca%' OR
                                    additional_data->>'Status' LIKE '%Licença%' OR
                                    additional_data->>'Status' LIKE '%Licenca%' OR
                                    additional_data->>'Status' LIKE '%Paternidade%' OR
                                    additional_data->>'Status' LIKE '%Maternidade%' OR
                                    additional_data->>'Status' LIKE '%Acidente Trabalho%'
                                THEN e.id END) as afastados,
                                COUNT(DISTINCT CASE WHEN additional_data->>'Status' LIKE '%Demitido%' OR additional_data->>'Status' LIKE '%Rescisão%' THEN e.id END) as demitidos
                            FROM payroll_data pd
                            INNER JOIN employees e ON e.id = pd.employee_id
                            WHERE pd.period_id = :most_recent_period_id
                        """
                        status_params = {**query_params, 'most_recent_period_id': most_recent_period_id}
                        status_result = conn.execute(text(status_query), status_params)
                        status_row = status_result.fetchone()
                        
                        if status_row:
                            response["stats"]["trabalhando"] = status_row[0]
                            response["stats"]["ferias"] = status_row[1]
                            response["stats"]["afastados"] = status_row[2]
                            response["stats"]["demitidos"] = status_row[3]
                        
                        # Adicionar informações do período mais recente para o frontend exibir
                        response["stats"]["most_recent_period"] = {
                            "id": most_recent_period_id,
                            "month": most_recent_month,
                            "year": most_recent_year
                        }
                    
                    # Calcular contratados = funcionários cuja DATA DE ADMISSÃO está dentro do range dos períodos selecionados
                    # Buscar as datas dos períodos selecionados
                    periods_dates_query = f"""
                        SELECT 
                            MIN(MAKE_DATE(year, month, 1)) as start_date,
                            MAX(MAKE_DATE(year, month, 1) + INTERVAL '1 month' - INTERVAL '1 day') as end_date
                        FROM payroll_periods
                        WHERE id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                    """
                    periods_dates_result = conn.execute(text(periods_dates_query), query_params)
                    periods_dates_row = periods_dates_result.fetchone()
                    
                    if periods_dates_row and periods_dates_row[0] and periods_dates_row[1]:
                        start_date = periods_dates_row[0]
                        end_date = periods_dates_row[1]
                        
                        print(f"🔍 DEBUG - Range de datas dos períodos: {start_date} até {end_date}")
                        
                        # Contar funcionários cuja admission_date está neste range E aparecem nos períodos filtrados
                        contratados_query = f"""
                            SELECT COUNT(DISTINCT e.id)
                            FROM employees e
                            INNER JOIN payroll_data pd ON pd.employee_id = e.id
                            WHERE pd.period_id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                            AND e.admission_date >= :start_date
                            AND e.admission_date <= :end_date
                        """
                        
                        contratados_params = {**query_params, 'start_date': start_date, 'end_date': end_date}
                        contratados_result = conn.execute(text(contratados_query), contratados_params)
                        contratados_row = contratados_result.fetchone()
                        
                        if contratados_row:
                            response["stats"]["contratados"] = contratados_row[0]
                            print(f"✅ Contratados (admission_date entre {start_date} e {end_date}): {contratados_row[0]}")
                        
                        # 🆕 Contar desligados usando termination_date (mesma lógica que contratados)
                        desligados_query = f"""
                            SELECT COUNT(DISTINCT e.id)
                            FROM employees e
                            INNER JOIN payroll_data pd ON pd.employee_id = e.id
                            WHERE pd.period_id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                            AND e.termination_date >= :start_date
                            AND e.termination_date <= :end_date
                        """
                        
                        desligados_result = conn.execute(text(desligados_query), contratados_params)
                        desligados_row = desligados_result.fetchone()
                        
                        if desligados_row:
                            response["stats"]["demitidos"] = desligados_row[0]
                            print(f"✅ Desligados (termination_date entre {start_date} e {end_date}): {desligados_row[0]}")
                    else:
                        print(f"⚠️ Não foi possível determinar range de datas dos períodos")
                
                # 🆕 Para período único, também calcular contratados e desligados
                elif period_ids and len(period_ids) == 1:
                    period_query = "SELECT year, month FROM payroll_periods WHERE id = :period_0"
                    period_result = conn.execute(text(period_query), query_params)
                    period_row = period_result.fetchone()
                    
                    if period_row:
                        year, month = period_row[0], period_row[1]
                        from datetime import date
                        import calendar
                        
                        start_date = date(year, month, 1)
                        last_day = calendar.monthrange(year, month)[1]
                        end_date = date(year, month, last_day)
                        
                        # Contratados no mês
                        contratados_query = f"""
                            SELECT COUNT(DISTINCT e.id)
                            FROM employees e
                            INNER JOIN payroll_data pd ON pd.employee_id = e.id
                            WHERE 1=1 {where_sql}
                            AND e.admission_date >= :start_date
                            AND e.admission_date <= :end_date
                        """
                        
                        single_params = {**query_params, 'start_date': start_date, 'end_date': end_date}
                        contratados_result = conn.execute(text(contratados_query), single_params)
                        contratados_row = contratados_result.fetchone()
                        
                        if contratados_row:
                            response["stats"]["contratados"] = contratados_row[0]
                            print(f"✅ Contratados em {month}/{year}: {contratados_row[0]}")
                        
                        # Desligados no mês
                        desligados_query = f"""
                            SELECT COUNT(DISTINCT e.id)
                            FROM employees e
                            INNER JOIN payroll_data pd ON pd.employee_id = e.id
                            WHERE 1=1 {where_sql}
                            AND e.termination_date >= :start_date
                            AND e.termination_date <= :end_date
                        """
                        
                        desligados_result = conn.execute(text(desligados_query), single_params)
                        desligados_row = desligados_result.fetchone()
                        
                        if desligados_row:
                            response["stats"]["demitidos"] = desligados_row[0]
                            print(f"✅ Desligados em {month}/{year}: {desligados_row[0]}")

                
                print(f"✅ Estatísticas filtradas calculadas")
                self.send_json_response(response)
                
        except Exception as e:
            print(f"❌ Erro ao calcular estatísticas filtradas: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_statistics_debug(self):
        """DEBUG - Retorna listas de nomes dos colaboradores em cada categoria"""
        try:
            from urllib.parse import parse_qs
            query_string = self.path.split('?')[1] if '?' in self.path else ''
            params = parse_qs(query_string)
            
            # Extrair filtros
            period_ids = params.get('periods', [])
            if period_ids and period_ids[0]:
                period_ids = [int(p) for p in period_ids[0].split(',')]
            else:
                period_ids = []
            
            print(f"🔍 DEBUG - Períodos: {period_ids}")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                where_clauses = []
                query_params = {}
                
                if period_ids:
                    placeholders = ', '.join([f':period_{i}' for i in range(len(period_ids))])
                    where_clauses.append(f"pd.period_id IN ({placeholders})")
                    for i, pid in enumerate(period_ids):
                        query_params[f'period_{i}'] = pid
                
                where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""
                
                response = {
                    "success": True,
                    "periods": period_ids,
                    "trabalhando": [],
                    "contratados": [],
                    "desligados": [],
                    "ferias": [],
                    "afastados": []
                }
                
                # Lista de trabalhando - do PERÍODO MAIS RECENTE
                if period_ids and len(period_ids) > 1:
                    # Buscar período mais recente
                    most_recent_period_query = f"""
                        SELECT id FROM payroll_periods
                        WHERE id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                        ORDER BY year DESC, month DESC
                        LIMIT 1
                    """
                    most_recent_result = conn.execute(text(most_recent_period_query), query_params)
                    most_recent_row = most_recent_result.fetchone()
                    
                    if most_recent_row:
                        most_recent_period_id = most_recent_row[0]
                        
                        trabalhando_query = f"""
                            SELECT DISTINCT e.id, e.name, e.unique_id, e.admission_date
                            FROM payroll_data pd
                            INNER JOIN employees e ON e.id = pd.employee_id
                            WHERE pd.period_id = :most_recent_period_id
                            AND additional_data->>'Status' = 'Trabalhando'
                            ORDER BY e.name
                        """
                        result = conn.execute(text(trabalhando_query), {'most_recent_period_id': most_recent_period_id})
                        response["trabalhando"] = [
                            {"id": row[0], "name": row[1], "unique_id": row[2], "admission_date": str(row[3]) if row[3] else None, "status": "Trabalhando"}
                            for row in result.fetchall()
                        ]
                else:
                    # Um período só - pega direto
                    trabalhando_query = f"""
                        SELECT DISTINCT e.id, e.name, e.unique_id, e.admission_date, additional_data->>'Status' as status
                        FROM payroll_data pd
                        INNER JOIN employees e ON e.id = pd.employee_id
                        WHERE 1=1 {where_sql}
                        AND additional_data->>'Status' = 'Trabalhando'
                        ORDER BY e.name
                    """
                    result = conn.execute(text(trabalhando_query), query_params)
                    response["trabalhando"] = [
                        {"id": row[0], "name": row[1], "unique_id": row[2], "admission_date": str(row[3]) if row[3] else None, "status": row[4]}
                        for row in result.fetchall()
                    ]
                
                # Lista de contratados (admission_date dentro do range)
                if period_ids and len(period_ids) > 1:
                    periods_dates_query = f"""
                        SELECT 
                            MIN(MAKE_DATE(year, month, 1)) as start_date,
                            MAX(MAKE_DATE(year, month, 1) + INTERVAL '1 month' - INTERVAL '1 day') as end_date
                        FROM payroll_periods
                        WHERE id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                    """
                    periods_dates_result = conn.execute(text(periods_dates_query), query_params)
                    periods_dates_row = periods_dates_result.fetchone()
                    
                    if periods_dates_row and periods_dates_row[0] and periods_dates_row[1]:
                        start_date = periods_dates_row[0]
                        end_date = periods_dates_row[1]
                        
                        contratados_query = f"""
                            SELECT DISTINCT e.id, e.name, e.unique_id, e.admission_date
                            FROM employees e
                            INNER JOIN payroll_data pd ON pd.employee_id = e.id
                            WHERE pd.period_id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                            AND e.admission_date >= :start_date
                            AND e.admission_date <= :end_date
                            ORDER BY e.admission_date, e.name
                        """
                        
                        contratados_params = {**query_params, 'start_date': start_date, 'end_date': end_date}
                        result = conn.execute(text(contratados_query), contratados_params)
                        response["contratados"] = [
                            {"id": row[0], "name": row[1], "unique_id": row[2], "admission_date": str(row[3]) if row[3] else None}
                            for row in result.fetchall()
                        ]
                        response["date_range"] = {"start": str(start_date), "end": str(end_date)}
                
                # Lista de desligados (termination_date dentro do período)
                if period_ids and len(period_ids) > 1:
                    # Obter range de datas dos períodos
                    periods_dates_query = f"""
                        SELECT 
                            MIN(MAKE_DATE(year, month, 1)) as start_date,
                            MAX(MAKE_DATE(year, month, 1) + INTERVAL '1 month' - INTERVAL '1 day') as end_date
                        FROM payroll_periods
                        WHERE id IN ({','.join([':period_' + str(i) for i in range(len(period_ids))])})
                    """
                    date_result = conn.execute(text(periods_dates_query), query_params)
                    date_row = date_result.fetchone()
                    
                    if date_row and date_row[0] and date_row[1]:
                        start_date = date_row[0]
                        end_date = date_row[1]
                        
                        # Buscar employees cujo termination_date está no range E que aparecem nos períodos
                        desligados_query = f"""
                            SELECT DISTINCT e.id, e.name, e.unique_id, e.termination_date, 'Demitido' as status
                            FROM employees e
                            INNER JOIN payroll_data pd ON pd.employee_id = e.id
                            WHERE pd.period_id IN ({','.join([':period_' + str(i) for i in range(len(period_ids))])})
                            AND e.termination_date >= :start_date
                            AND e.termination_date <= :end_date
                            ORDER BY e.termination_date DESC, e.name
                        """
                        
                        desligados_params = query_params.copy()
                        desligados_params['start_date'] = start_date
                        desligados_params['end_date'] = end_date
                        
                        result = conn.execute(text(desligados_query), desligados_params)
                        response["desligados"] = [
                            {"id": row[0], "name": row[1], "unique_id": row[2], "termination_date": str(row[3]) if row[3] else None, "status": row[4]}
                            for row in result.fetchall()
                        ]
                        
                        print(f"   ✅ Desligados (termination_date entre {start_date} e {end_date}): {len(response['desligados'])}")
                    else:
                        response["desligados"] = []
                else:
                    # Período único - pegar employees com termination_date naquele mês
                    if period_ids:
                        period_query = "SELECT year, month FROM payroll_periods WHERE id = :period_0"
                        period_result = conn.execute(text(period_query), query_params)
                        period_row = period_result.fetchone()
                        
                        if period_row:
                            year, month = period_row[0], period_row[1]
                            from datetime import date
                            import calendar
                            
                            start_date = date(year, month, 1)
                            last_day = calendar.monthrange(year, month)[1]
                            end_date = date(year, month, last_day)
                            
                            desligados_query = f"""
                                SELECT DISTINCT e.id, e.name, e.unique_id, e.termination_date, 'Demitido' as status
                                FROM employees e
                                INNER JOIN payroll_data pd ON pd.employee_id = e.id
                                WHERE 1=1 {where_sql}
                                AND e.termination_date >= :start_date
                                AND e.termination_date <= :end_date
                                ORDER BY e.name
                            """
                            
                            desligados_params = query_params.copy()
                            desligados_params['start_date'] = start_date
                            desligados_params['end_date'] = end_date
                            
                            result = conn.execute(text(desligados_query), desligados_params)
                            response["desligados"] = [
                                {"id": row[0], "name": row[1], "unique_id": row[2], "termination_date": str(row[3]) if row[3] else None, "status": row[4]}
                                for row in result.fetchall()
                            ]
                        else:
                            response["desligados"] = []
                    else:
                        response["desligados"] = []
                
                # 🆕 Lista de férias - do PERÍODO MAIS RECENTE da seleção
                if period_ids and len(period_ids) > 1:
                    # Buscar período mais recente (maior year/month)
                    most_recent_period_query = f"""
                        SELECT id, month, year
                        FROM payroll_periods
                        WHERE id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                        ORDER BY year DESC, month DESC
                        LIMIT 1
                    """
                    most_recent_result = conn.execute(text(most_recent_period_query), query_params)
                    most_recent_row = most_recent_result.fetchone()
                    
                    if most_recent_row:
                        most_recent_period_id, most_recent_month, most_recent_year = most_recent_row[0], most_recent_row[1], most_recent_row[2]
                        
                        ferias_query = """
                            SELECT DISTINCT e.id, e.name, e.unique_id,
                                   additional_data->>'Status' as status,
                                   :month as month, :year as year
                            FROM payroll_data pd
                            INNER JOIN employees e ON e.id = pd.employee_id
                            WHERE pd.period_id = :most_recent_period_id
                            AND additional_data->>'Status' = 'Férias'
                            ORDER BY e.name
                        """
                        result = conn.execute(text(ferias_query), {
                            'most_recent_period_id': most_recent_period_id,
                            'month': most_recent_month,
                            'year': most_recent_year
                        })
                        response["ferias"] = [
                            {"id": row[0], "name": row[1], "unique_id": row[2], "status": row[3], "month": row[4], "year": row[5]}
                            for row in result.fetchall()
                        ]
                    else:
                        response["ferias"] = []
                else:
                    # Período único
                    ferias_query = f"""
                        SELECT DISTINCT e.id, e.name, e.unique_id, additional_data->>'Status' as status, pp.month, pp.year
                        FROM payroll_data pd
                        INNER JOIN employees e ON e.id = pd.employee_id
                        INNER JOIN payroll_periods pp ON pp.id = pd.period_id
                        WHERE 1=1 {where_sql}
                        AND additional_data->>'Status' = 'Férias'
                        ORDER BY e.name
                    """
                    result = conn.execute(text(ferias_query), query_params)
                    response["ferias"] = [
                        {"id": row[0], "name": row[1], "unique_id": row[2], "status": row[3], "month": row[4], "year": row[5]}
                        for row in result.fetchall()
                    ]
                
                # 🆕 Lista de afastados - do PERÍODO MAIS RECENTE da seleção
                if period_ids and len(period_ids) > 1:
                    # Buscar período mais recente (maior year/month)
                    most_recent_period_query = f"""
                        SELECT id, month, year
                        FROM payroll_periods
                        WHERE id IN ({','.join([f':period_{i}' for i in range(len(period_ids))])})
                        ORDER BY year DESC, month DESC
                        LIMIT 1
                    """
                    most_recent_result = conn.execute(text(most_recent_period_query), query_params)
                    most_recent_row = most_recent_result.fetchone()
                    
                    if most_recent_row:
                        most_recent_period_id, most_recent_month, most_recent_year = most_recent_row[0], most_recent_row[1], most_recent_row[2]
                        
                        afastados_query = """
                            SELECT DISTINCT e.id, e.name, e.unique_id,
                                   additional_data->>'Status' as status,
                                   :month as month, :year as year
                            FROM payroll_data pd
                            INNER JOIN employees e ON e.id = pd.employee_id
                            WHERE pd.period_id = :most_recent_period_id
                            AND (
                                additional_data->>'Status' LIKE '%Afastado%' OR
                                additional_data->>'Status' LIKE '%Auxílio Doença%' OR
                                additional_data->>'Status' LIKE '%Auxilio Doenca%' OR
                                additional_data->>'Status' LIKE '%Licença%' OR
                                additional_data->>'Status' LIKE '%Licenca%' OR
                                additional_data->>'Status' LIKE '%Paternidade%' OR
                                additional_data->>'Status' LIKE '%Maternidade%' OR
                                additional_data->>'Status' LIKE '%Acidente Trabalho%'
                            )
                            ORDER BY e.name
                        """
                        result = conn.execute(text(afastados_query), {
                            'most_recent_period_id': most_recent_period_id,
                            'month': most_recent_month,
                            'year': most_recent_year
                        })
                        response["afastados"] = [
                            {"id": row[0], "name": row[1], "unique_id": row[2], "status": row[3], "month": row[4], "year": row[5]}
                            for row in result.fetchall()
                        ]
                    else:
                        response["afastados"] = []
                else:
                    # Período único
                    afastados_query = f"""
                        SELECT DISTINCT e.id, e.name, e.unique_id, additional_data->>'Status' as status, pp.month, pp.year
                        FROM payroll_data pd
                        INNER JOIN employees e ON e.id = pd.employee_id
                        INNER JOIN payroll_periods pp ON pp.id = pd.period_id
                        WHERE 1=1 {where_sql}
                        AND (
                            additional_data->>'Status' LIKE '%Afastado%' OR
                            additional_data->>'Status' LIKE '%Auxílio Doença%' OR
                            additional_data->>'Status' LIKE '%Auxilio Doenca%' OR
                            additional_data->>'Status' LIKE '%Licença%' OR
                            additional_data->>'Status' LIKE '%Licenca%' OR
                            additional_data->>'Status' LIKE '%Paternidade%' OR
                            additional_data->>'Status' LIKE '%Maternidade%' OR
                            additional_data->>'Status' LIKE '%Acidente Trabalho%'
                        )
                        ORDER BY e.name
                    """
                    result = conn.execute(text(afastados_query), query_params)
                    response["afastados"] = [
                        {"id": row[0], "name": row[1], "unique_id": row[2], "status": row[3], "month": row[4], "year": row[5]}
                        for row in result.fetchall()
                    ]
                
                print(f"✅ DEBUG - Trabalhando: {len(response['trabalhando'])}, Contratados: {len(response['contratados'])}, Desligados: {len(response['desligados'])}, Férias: {len(response['ferias'])}, Afastados: {len(response['afastados'])}")
                self.send_json_response(response)
                
        except Exception as e:
            print(f"❌ Erro ao gerar debug: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_payroll_processing_history(self):
        """Retorna histórico de processamento de CSVs"""
        try:
            print("📋 Buscando histórico de processamento...")
            
            from sqlalchemy import text
            
            global db_engine
            if not db_engine:
                self.send_json_response({
                    "success": False,
                    "error": "Banco de dados não disponível"
                }, 500)
                return
            
            with db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        ppl.id,
                        ppl.filename,
                        ppl.file_size,
                        ppl.total_rows,
                        ppl.processed_rows,
                        ppl.error_rows,
                        ppl.status,
                        ppl.error_message,
                        ppl.processing_time,
                        ppl.created_at,
                        pp.period_name,
                        u.username
                    FROM payroll_processing_logs ppl
                    LEFT JOIN payroll_periods pp ON pp.id = ppl.period_id
                    LEFT JOIN users u ON u.id = ppl.processed_by
                    ORDER BY ppl.created_at DESC
                    LIMIT 50
                """))
                
                history = []
                for row in result:
                    history.append({
                        "id": row[0],
                        "filename": row[1],
                        "file_size": row[2],
                        "total_rows": row[3],
                        "processed_rows": row[4],
                        "error_rows": row[5],
                        "status": row[6],
                        "error_message": row[7],
                        "processing_time": float(row[8]) if row[8] else 0,
                        "timestamp": row[9].isoformat() if row[9] else None,
                        "period_name": row[10],
                        "user": row[11] or "Sistema"
                    })
                
                print(f"✅ {len(history)} registros de histórico encontrados")
                self.send_json_response({
                    "success": True,
                    "history": history
                })
                
        except Exception as e:
            print(f"❌ Erro ao buscar histórico: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def handle_list_payroll_periods(self):
        """Lista períodos disponíveis para download"""
        try:
            import os
            import glob
            
            processed_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed')
            
            if not os.path.exists(processed_dir):
                self.send_json_response({"periods": []})
                return
            
            # Listar todas as subpastas em processed/
            periods = []
            for folder_name in os.listdir(processed_dir):
                folder_path = os.path.join(processed_dir, folder_name)
                
                if not os.path.isdir(folder_path):
                    continue
                
                # Contar PDFs na pasta
                pdf_files = glob.glob(os.path.join(folder_path, '*.pdf'))
                file_count = len(pdf_files)
                
                if file_count == 0:
                    continue
                
                # Extrair informações da pasta (formato: TipoNome_MM_YYYY)
                # Ex: Mensal_11_2025, Adiantamento_13_12_2025
                parts = folder_name.split('_')
                
                # Tentar extrair tipo, mês e ano
                payroll_type = None
                month = None
                year = None
                
                if len(parts) >= 3:
                    # Último é ano, penúltimo é mês
                    try:
                        year = int(parts[-1])
                        month = int(parts[-2])
                        
                        # Tipo pode ter múltiplas palavras (Adiantamento_13)
                        type_name = '_'.join(parts[:-2])
                        
                        # Mapear nome para código
                        type_map = {
                            'Mensal': '11',
                            'Adiantamento_13': '31',
                            '13_Integral': '32',
                            'Adiantamento_Salarial': '91'
                        }
                        payroll_type = type_map.get(type_name, '11')
                    except (ValueError, IndexError):
                        pass
                
                periods.append({
                    "folder": folder_name,
                    "file_count": file_count,
                    "payroll_type": payroll_type,
                    "month": month,
                    "year": year,
                    "path": folder_path
                })
            
            # Ordenar por ano e mês (mais recentes primeiro)
            periods.sort(key=lambda x: (x.get('year', 0), x.get('month', 0)), reverse=True)
            
            print(f"📁 {len(periods)} período(s) disponível(is)")
            self.send_json_response({"periods": periods})
            
        except Exception as e:
            print(f"❌ Erro ao listar períodos: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro ao listar períodos: {str(e)}"}, 500)
    
    # ==========================================
    # INDICADORES DE RH
    # ==========================================
    
    def handle_indicators_overview(self):
        """Retorna visão geral dos indicadores de RH com filtros de mês/ano/empresa/setor"""
        try:
            # Parse query params
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            company = query_params.get('company', ['all'])[0]
            division = query_params.get('division', ['all'])[0]
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            
            if SessionLocal:
                from app.models.payroll import PayrollPeriod, PayrollData
                from app.models.employee import Employee
                from sqlalchemy import func, or_, and_
                from decimal import Decimal
                from datetime import date, datetime
                
                db = SessionLocal()
                
                # Se não especificou ano/mês, pegar o mais recente
                if not year or not month:
                    latest_period = db.query(PayrollPeriod).order_by(
                        PayrollPeriod.year.desc(),
                        PayrollPeriod.month.desc()
                    ).first()
                    
                    if not latest_period:
                        db.close()
                        self.send_json_response({"error": "Nenhum período encontrado"}, 404)
                        return
                    
                    year = latest_period.year
                    month = latest_period.month
                else:
                    year = int(year)
                    month = int(month)
                
                # Buscar todos os períodos do mês/ano especificado (mensal e 13º)
                # FILTRAR POR EMPRESA AQUI - usando payroll_periods.company
                period_query = db.query(PayrollPeriod).filter(
                    PayrollPeriod.year == year,
                    PayrollPeriod.month == month
                )
                
                # Filtrar por empresa no período (NÃO no employee, pois company_code pode ser NULL)
                if company != 'all':
                    period_query = period_query.filter(PayrollPeriod.company == company)
                    print(f"🔍 Filtrando períodos por empresa: '{company}'")
                
                periods = period_query.all()
                
                if not periods:
                    db.close()
                    self.send_json_response({"error": f"Nenhum período encontrado para {month:02d}/{year}"}, 404)
                    return
                
                period_ids = [p.id for p in periods]
                print(f"📊 Períodos encontrados: {[(p.id, p.company, p.period_name) for p in periods]}")
                
                # Buscar dados de folha dos períodos
                payroll_query = db.query(PayrollData).filter(
                    PayrollData.period_id.in_(period_ids)
                )
                
                payroll_records = payroll_query.all()
                print(f"📊 Payroll records encontrados: {len(payroll_records)}")
                
                # Obter employee_ids dos registros de folha
                unique_employee_ids = set([r.employee_id for r in payroll_records])
                print(f"📊 Unique employee IDs em payroll: {len(unique_employee_ids)}")
                
                # Buscar dados dos employees para filtro por departamento
                employee_map = {}
                if unique_employee_ids:
                    employees = db.query(Employee).filter(
                        Employee.id.in_(unique_employee_ids)
                    ).all()
                    employee_map = {e.id: e for e in employees}
                    print(f"📊 Employees encontrados: {len(employees)}")
                
                # Filtrar por departamento/setor se especificado
                if division != 'all':
                    print(f"🔍 Filtrando por departamento: '{division}'")
                    # Filtrar payroll_records apenas para employees do departamento
                    dept_employee_ids = [e.id for e in employee_map.values() if e.department == division]
                    payroll_records = [r for r in payroll_records if r.employee_id in dept_employee_ids]
                    unique_employee_ids = set([r.employee_id for r in payroll_records])
                    print(f"📊 Após filtro de departamento: {len(payroll_records)} records, {len(unique_employee_ids)} employees")
                
                # Calcular métricas principais
                total_employees = len(unique_employee_ids)
                total_cost = sum([Decimal(str(r.net_salary or 0)) for r in payroll_records])
                
                # Buscar mês anterior para calcular variação
                if month == 1:
                    prev_year = year - 1
                    prev_month = 12
                else:
                    prev_year = year
                    prev_month = month - 1
                
                prev_period_query = db.query(PayrollPeriod).filter(
                    PayrollPeriod.year == prev_year,
                    PayrollPeriod.month == prev_month
                )
                if company != 'all':
                    prev_period_query = prev_period_query.filter(PayrollPeriod.company == company)
                
                prev_periods = prev_period_query.all()
                
                employee_variation = None
                cost_variation = None
                
                if prev_periods:
                    prev_period_ids = [p.id for p in prev_periods]
                    prev_records = db.query(PayrollData).filter(
                        PayrollData.period_id.in_(prev_period_ids)
                    ).all()
                    
                    # Aplicar filtro de departamento se necessário
                    if division != 'all':
                        dept_employee_ids = [e.id for e in employee_map.values() if e.department == division]
                        prev_records = [r for r in prev_records if r.employee_id in dept_employee_ids]
                    
                    prev_employees = len(set([r.employee_id for r in prev_records]))
                    prev_cost = sum([Decimal(str(r.net_salary or 0)) for r in prev_records])
                    
                    if prev_employees > 0:
                        employee_variation = ((total_employees - prev_employees) / prev_employees) * 100
                    if prev_cost > 0:
                        cost_variation = ((total_cost - prev_cost) / prev_cost) * 100
                
                # Distribuição por empresa (só faz sentido quando company='all')
                by_company = []
                if company == 'all':
                    # Agrupar por company do período
                    periods_by_company = {}
                    for p in periods:
                        if p.company not in periods_by_company:
                            periods_by_company[p.company] = []
                        periods_by_company[p.company].append(p.id)
                    
                    for comp_code, comp_period_ids in periods_by_company.items():
                        comp_records = [r for r in payroll_records if r.period_id in comp_period_ids]
                        comp_count = len(set([r.employee_id for r in comp_records]))
                        comp_cost = sum([Decimal(str(r.net_salary or 0)) for r in comp_records])
                        by_company.append({
                            'company': comp_code,
                            'count': comp_count,
                            'total_cost': float(comp_cost)
                        })
                
                # Top 5 setores
                employees_by_division = {}
                for emp_id in unique_employee_ids:
                    emp = employee_map.get(emp_id)
                    if emp:
                        div = emp.department or 'Não informado'
                        if div not in employees_by_division:
                            employees_by_division[div] = set()
                        employees_by_division[div].add(emp_id)
                
                top_divisions = sorted(
                    [{'division': k, 'count': len(v)} for k, v in employees_by_division.items()],
                    key=lambda x: x['count'],
                    reverse=True
                )[:5]
                
                # Contar admissões e desligamentos no mês
                period_start = date(year, month, 1)
                if month == 12:
                    period_end = date(year + 1, 1, 1)
                else:
                    period_end = date(year, month + 1, 1)
                
                # Contar admissões e desligamentos - restringir aos employees que estão no payroll
                admissions_query = db.query(Employee).filter(
                    Employee.admission_date >= period_start,
                    Employee.admission_date < period_end,
                    Employee.id.in_(unique_employee_ids) if unique_employee_ids else False
                )
                terminations_query = db.query(Employee).filter(
                    Employee.termination_date >= period_start,
                    Employee.termination_date < period_end,
                    Employee.id.in_(unique_employee_ids) if unique_employee_ids else False
                )
                
                # Filtro por departamento se aplicável
                if division != 'all':
                    admissions_query = admissions_query.filter(Employee.department == division)
                    terminations_query = terminations_query.filter(Employee.department == division)
                
                admissions = admissions_query.count()
                terminations = terminations_query.count()
                
                result = {
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division
                    },
                    'total_employees': total_employees,
                    'total_payroll_cost': float(total_cost),
                    'employee_variation': float(employee_variation) if employee_variation is not None else None,
                    'cost_variation': float(cost_variation) if cost_variation is not None else None,
                    'admissions': admissions,
                    'terminations': terminations,
                    'by_company': by_company,
                    'top_divisions': top_divisions
                }
                
                db.close()
                self.send_json_response(result)
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar overview de indicadores: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def handle_indicators_headcount(self):
        """Retorna métricas de headcount com evolução temporal e distribuições"""
        try:
            # Parse query params
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            company = query_params.get('company', ['all'])[0]
            division = query_params.get('division', ['all'])[0]
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            months_range = int(query_params.get('months_range', ['12'])[0])  # Últimos N meses
            
            if SessionLocal:
                from app.models.payroll import PayrollPeriod, PayrollData
                from app.models.employee import Employee
                from sqlalchemy import func, or_, and_
                from decimal import Decimal
                from datetime import date, datetime
                from dateutil.relativedelta import relativedelta
                
                db = SessionLocal()
                
                # Se não especificou período, usar o mais recente
                if not year or not month:
                    latest_period = db.query(PayrollPeriod).order_by(
                        PayrollPeriod.year.desc(),
                        PayrollPeriod.month.desc()
                    ).first()
                    
                    if not latest_period:
                        db.close()
                        self.send_json_response({"error": "Nenhum período encontrado"}, 404)
                        return
                    
                    year = latest_period.year
                    month = latest_period.month
                else:
                    year = int(year)
                    month = int(month)
                
                # Calcular período atual
                current_date = date(year, month, 1)
                
                # MÉTRICA ATUAL (mês selecionado)
                current_metrics = self._get_headcount_for_period(db, year, month, company, division)
                
                # EVOLUÇÃO TEMPORAL (últimos N meses)
                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    
                    metrics = self._get_headcount_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month-1]}/{str(p_year)[2:]}",
                        'headcount': metrics['headcount'],
                        'total_cost': metrics['total_cost'],
                        'total_earnings': metrics.get('total_earnings', 0.0),
                        'total_deductions': metrics.get('total_deductions', 0.0),
                        'avg_cost_per_employee': metrics['avg_cost_per_employee']
                    })
                
                # DISTRIBUIÇÃO POR EMPRESA (só se company='all')
                by_company = current_metrics.get('by_company', [])
                
                # TOP 10 SETORES
                top_divisions = current_metrics.get('top_divisions', [])[:10]
                
                # TOP 10 CARGOS
                top_positions = self._get_top_positions(
                    db, year, month, company, division, limit=10
                )
                
                result = {
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range
                    },
                    'current': {
                        'headcount': current_metrics['headcount'],
                        'total_cost': current_metrics['total_cost'],
                        'avg_cost_per_employee': current_metrics['avg_cost_per_employee'],
                        'total_earnings': current_metrics['total_earnings'],
                        'total_deductions': current_metrics['total_deductions'],
                        'variation_vs_previous': current_metrics['variation_vs_previous']
                    },
                    'evolution': evolution_data,
                    'by_company': by_company,
                    'top_divisions': top_divisions,
                    'top_positions': top_positions
                }
                
                db.close()
                self.send_json_response(result)
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar headcount: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def _get_headcount_for_period(self, db, year, month, company='all', division='all'):
        """Helper para calcular headcount de um período específico"""
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        from decimal import Decimal
        
        # Buscar períodos do mês/ano filtrado por empresa
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        
        if company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)
        
        periods = period_query.all()
        
        if not periods:
            return {
                'headcount': 0,
                'total_cost': 0.0,
                'avg_cost_per_employee': 0.0,
                'variation_vs_previous': None,
                'by_company': [],
                'top_divisions': []
            }
        
        period_ids = [p.id for p in periods]
        
        # Buscar dados de folha
        payroll_records = db.query(PayrollData).filter(
            PayrollData.period_id.in_(period_ids)
        ).all()
        
        unique_employee_ids = set([r.employee_id for r in payroll_records])
        
        # Buscar dados dos employees
        employee_map = {}
        if unique_employee_ids:
            employees = db.query(Employee).filter(
                Employee.id.in_(unique_employee_ids)
            ).all()
            employee_map = {e.id: e for e in employees}
        
        # Filtrar por departamento se especificado
        if division != 'all':
            dept_employee_ids = [e.id for e in employee_map.values() if e.department == division]
            payroll_records = [r for r in payroll_records if r.employee_id in dept_employee_ids]
            unique_employee_ids = set([r.employee_id for r in payroll_records])
        
        headcount = len(unique_employee_ids)
        total_cost = sum([Decimal(str(r.net_salary or 0)) for r in payroll_records])
        total_earnings = sum([Decimal(str(r.gross_salary or 0)) for r in payroll_records])
        total_deductions = total_earnings - total_cost
        avg_cost = float(total_cost / headcount) if headcount > 0 else 0.0
        
        # Calcular variação vs mês anterior
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        
        prev_metrics = self._get_headcount_for_period(db, prev_year, prev_month, company, division)
        prev_headcount = prev_metrics['headcount']
        variation = None
        if prev_headcount > 0:
            variation = ((headcount - prev_headcount) / prev_headcount) * 100
        
        # Distribuição por empresa
        by_company = []
        if company == 'all':
            periods_by_company = {}
            for p in periods:
                if p.company not in periods_by_company:
                    periods_by_company[p.company] = []
                periods_by_company[p.company].append(p.id)
            
            for comp_code, comp_period_ids in periods_by_company.items():
                comp_records = [r for r in payroll_records if r.period_id in comp_period_ids]
                comp_count = len(set([r.employee_id for r in comp_records]))
                comp_cost = sum([Decimal(str(r.net_salary or 0)) for r in comp_records])
                by_company.append({
                    'company': comp_code,
                    'headcount': comp_count,
                    'total_cost': float(comp_cost)
                })
        
        # Top setores
        employees_by_division = {}
        for emp_id in unique_employee_ids:
            emp = employee_map.get(emp_id)
            if emp:
                div = emp.department or 'Não informado'
                if div not in employees_by_division:
                    employees_by_division[div] = set()
                employees_by_division[div].add(emp_id)
        
        top_divisions = sorted(
            [{'division': k, 'count': len(v)} for k, v in employees_by_division.items()],
            key=lambda x: x['count'],
            reverse=True
        )
        
        return {
            'headcount': headcount,
            'total_cost': float(total_cost),
            'avg_cost_per_employee': avg_cost,
            'total_earnings': float(total_earnings),
            'total_deductions': float(total_deductions),
            'variation_vs_previous': float(variation) if variation is not None else None,
            'by_company': by_company,
            'top_divisions': top_divisions
        }
    
    def _get_top_positions(self, db, year, month, company='all', division='all', limit=10):
        """Helper para calcular top cargos"""
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        
        # Buscar períodos
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        
        if company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)
        
        periods = period_query.all()
        if not periods:
            return []
        
        period_ids = [p.id for p in periods]
        
        # Buscar dados de folha
        payroll_records = db.query(PayrollData).filter(
            PayrollData.period_id.in_(period_ids)
        ).all()
        
        unique_employee_ids = set([r.employee_id for r in payroll_records])
        
        # Buscar employees
        if not unique_employee_ids:
            return []
        
        employees = db.query(Employee).filter(
            Employee.id.in_(unique_employee_ids)
        ).all()
        
        # Filtrar por departamento se especificado
        if division != 'all':
            employees = [e for e in employees if e.department == division]
        
        # Agrupar por cargo
        employees_by_position = {}
        for emp in employees:
            pos = emp.position or 'Não informado'
            if pos not in employees_by_position:
                employees_by_position[pos] = set()
            employees_by_position[pos].add(emp.id)
        
        # Ordenar e limitar
        top_positions = sorted(
            [{'position': k, 'count': len(v)} for k, v in employees_by_position.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:limit]
        
        return top_positions
    
    def handle_indicators_demographics(self):
        """Retorna métricas de headcount (efetivo)"""
        try:
            from app.services.hr_indicators import HRIndicatorsService
            
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            use_cache = query_params.get('use_cache', ['true'])[0].lower() != 'false'
            
            db = SessionLocal()
            try:
                service = HRIndicatorsService(db)
                result = service.get_headcount_metrics(use_cache=use_cache)
                self.send_json_response(result)
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao buscar headcount: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def handle_indicators_turnover(self):
        """Retorna métricas de turnover (rotatividade) com evolução temporal"""
        try:
            # Parse query params
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            company = query_params.get('company', ['all'])[0]
            division = query_params.get('division', ['all'])[0]
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            months_range = int(query_params.get('months_range', ['12'])[0])
            
            if SessionLocal:
                from app.models.payroll import PayrollPeriod, PayrollData
                from app.models.employee import Employee
                from sqlalchemy import func, or_, and_
                from decimal import Decimal
                from datetime import date, datetime
                from dateutil.relativedelta import relativedelta
                
                db = SessionLocal()
                
                # Se não especificou período, usar o mais recente
                if not year or not month:
                    latest_period = db.query(PayrollPeriod).order_by(
                        PayrollPeriod.year.desc(),
                        PayrollPeriod.month.desc()
                    ).first()
                    
                    if not latest_period:
                        db.close()
                        self.send_json_response({"error": "Nenhum período encontrado"}, 404)
                        return
                    
                    year = latest_period.year
                    month = latest_period.month
                else:
                    year = int(year)
                    month = int(month)
                
                # Calcular período atual
                current_date = date(year, month, 1)
                
                # MÉTRICA ATUAL (mês selecionado)
                current_metrics = self._get_turnover_for_period(db, year, month, company, division)
                
                # EVOLUÇÃO TEMPORAL (últimos N meses)
                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    
                    metrics = self._get_turnover_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month-1]}/{str(p_year)[2:]}",
                        'turnover_rate': metrics['turnover_rate'],
                        'admissions': metrics['admissions'],
                        'terminations': metrics['terminations'],
                        'avg_headcount': metrics['avg_headcount'],
                        'avg_tenure_months': metrics.get('avg_tenure_months', 0.0)
                    })
                
                # DISTRIBUIÇÃO POR EMPRESA E SETORES - DESABILITADO POR PERFORMANCE
                # Esses cálculos fazem N queries adicionais e tornam a tela muito lenta
                # Podem ser reabilitados se necessário com otimização via query única
                by_company = []
                top_divisions = []
                
                result = {
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range
                    },
                    'current': {
                        'turnover_rate': current_metrics['turnover_rate'],
                        'admissions': current_metrics['admissions'],
                        'terminations': current_metrics['terminations'],
                        'avg_headcount': current_metrics['avg_headcount'],
                        'avg_tenure_months': current_metrics.get('avg_tenure_months', 0.0)
                    },
                    'evolution': evolution_data,
                    'by_company': by_company,
                    'top_divisions': top_divisions
                }
                
                db.close()
                self.send_json_response(result)
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar turnover: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def _get_turnover_for_period(self, db, year, month, company='all', division='all'):
        """Helper OTIMIZADO para calcular turnover de um período específico"""
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        from sqlalchemy import func
        from datetime import date
        
        # Calcular datas do período
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1)
        else:
            period_end = date(year, month + 1, 1)
        
        # Mês anterior
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        
        prev_start = date(prev_year, prev_month, 1)
        
        # Query única para headcount atual e anterior
        periods_query = db.query(PayrollPeriod).filter(
            ((PayrollPeriod.year == year) & (PayrollPeriod.month == month)) |
            ((PayrollPeriod.year == prev_year) & (PayrollPeriod.month == prev_month))
        )
        
        if company != 'all':
            periods_query = periods_query.filter(PayrollPeriod.company == company)
        
        periods = periods_query.all()
        
        current_period_ids = [p.id for p in periods if p.year == year and p.month == month]
        prev_period_ids = [p.id for p in periods if p.year == prev_year and p.month == prev_month]
        
        # Contar headcount de cada período
        current_headcount = 0
        prev_headcount = 0
        employee_ids_current = set()
        
        if current_period_ids:
            hc_query = db.query(func.count(func.distinct(PayrollData.employee_id))).filter(
                PayrollData.period_id.in_(current_period_ids)
            )
            if division != 'all':
                hc_query = hc_query.join(Employee).filter(Employee.department == division)
            current_headcount = hc_query.scalar() or 0
            
            # IDs dos funcionários no período atual
            emp_query = db.query(PayrollData.employee_id).filter(
                PayrollData.period_id.in_(current_period_ids)
            ).distinct()
            employee_ids_current = set([r[0] for r in emp_query.all()])
        
        if prev_period_ids:
            hc_query = db.query(func.count(func.distinct(PayrollData.employee_id))).filter(
                PayrollData.period_id.in_(prev_period_ids)
            )
            if division != 'all':
                hc_query = hc_query.join(Employee).filter(Employee.department == division)
            prev_headcount = hc_query.scalar() or 0
        
        avg_headcount = (current_headcount + prev_headcount) / 2 if (current_headcount + prev_headcount) > 0 else 0
        
        # Contar admissões e desligamentos
        admissions_query = db.query(func.count(Employee.id)).filter(
            Employee.admission_date >= period_start,
            Employee.admission_date < period_end
        )
        terminations_query = db.query(Employee.admission_date, Employee.termination_date).filter(
            Employee.termination_date >= period_start,
            Employee.termination_date < period_end
        )
        
        if division != 'all':
            admissions_query = admissions_query.filter(Employee.department == division)
            terminations_query = terminations_query.filter(Employee.department == division)
        
        if employee_ids_current:
            admissions_query = admissions_query.filter(Employee.id.in_(employee_ids_current))
            terminations_query = terminations_query.filter(Employee.id.in_(employee_ids_current))
        
        admissions = admissions_query.scalar() or 0
        terminated_empes = terminations_query.all()
        terminations = len(terminated_empes)
        
        total_tenure_days = 0
        valid_tenure_count = 0
        for adm_date, term_date in terminated_empes:
            if adm_date and term_date:
                total_tenure_days += (term_date - adm_date).days
                valid_tenure_count += 1
                
        avg_tenure_months = 0.0
        if valid_tenure_count > 0:
            avg_tenure_months = (total_tenure_days / valid_tenure_count) / 30.416
        
        # Taxa de turnover
        turnover_rate = 0.0
        if avg_headcount > 0:
            turnover_rate = ((admissions + terminations) / 2) / avg_headcount * 100
        
        return {
            'turnover_rate': round(turnover_rate, 2),
            'admissions': admissions,
            'terminations': terminations,
            'avg_headcount': round(avg_headcount, 1),
            'avg_tenure_months': avg_tenure_months,
            'by_company': [],
            'top_divisions_turnover': []
        }
    
    def _get_demographics_for_period(self, db, year, month, company='all', division='all'):
        """Helper para calcular métricas demográficas de um período específico"""
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        from sqlalchemy import func, case
        
        # Buscar períodos do mês especificado
        periods_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        
        if company != 'all':
            periods_query = periods_query.filter(PayrollPeriod.company == company)
        
        periods = periods_query.all()
        if not periods:
            return {
                'average_age': 0,
                'male_count': 0,
                'female_count': 0,
                'total_employees': 0,
                'by_sex': [],
                'age_ranges': []
            }
        
        period_ids = [p.id for p in periods]
        
        # Obter IDs únicos de funcionários do período
        employee_ids_query = db.query(PayrollData.employee_id).filter(
            PayrollData.period_id.in_(period_ids)
        ).distinct()
        
        employee_ids = [r[0] for r in employee_ids_query.all()]
        
        if not employee_ids:
            return {
                'average_age': 0,
                'male_count': 0,
                'female_count': 0,
                'total_employees': 0,
                'by_sex': [],
                'age_ranges': []
            }
        
        # Query base de employees do período
        emp_query = db.query(Employee).filter(Employee.id.in_(employee_ids))
        
        if division != 'all':
            emp_query = emp_query.filter(Employee.department == division)
        
        # Distribuição por sexo
        by_sex_query = db.query(
            Employee.sex,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.id.in_(employee_ids),
            Employee.sex.isnot(None)
        )
        
        if division != 'all':
            by_sex_query = by_sex_query.filter(Employee.department == division)
        
        by_sex = by_sex_query.group_by(Employee.sex).all()
        
        # Faixas etárias com nomes na memória
        from datetime import date
        today = date.today()
        
        employees_age_query = db.query(Employee.name, Employee.birth_date, Employee.department).filter(
            Employee.id.in_(employee_ids),
            Employee.birth_date.isnot(None)
        )
        if division != 'all':
            employees_age_query = employees_age_query.filter(Employee.department == division)
            
        emps = employees_age_query.all()
        
        age_groups = {
            '16-20': {'count': 0, 'employees': []},
            '21-30': {'count': 0, 'employees': []},
            '31-40': {'count': 0, 'employees': []},
            '41-50': {'count': 0, 'employees': []},
            '51-60': {'count': 0, 'employees': []},
            '60+': {'count': 0, 'employees': []}
        }
        
        total_age = 0
        for name, bdate, department in emps:
            age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
            total_age += age
            
            if age <= 20: bucket = '16-20'
            elif age <= 30: bucket = '21-30'
            elif age <= 40: bucket = '31-40'
            elif age <= 50: bucket = '41-50'
            elif age <= 60: bucket = '51-60'
            else: bucket = '60+'
            
            age_groups[bucket]['count'] += 1
            age_groups[bucket]['employees'].append({
                'name': name,
                'age': age,
                'department': department or 'Não informado'
            })
            
        age_ranges = []
        for k in ['16-20', '21-30', '31-40', '41-50', '51-60', '60+']:
            if age_groups[k]['count'] > 0:
                age_ranges.append({
                    'range': k,
                    'count': age_groups[k]['count'],
                    'employees': sorted(age_groups[k]['employees'], key=lambda x: x['name'])
                })
        
        # O age_ranges acima já é formatado como array de dicts ordenado corretamente
        sorted_age_ranges = age_ranges
        
        # Calcular a average age
        avg_age = (total_age / len(emps)) if emps else 0
        
        # Extrair contagens por sexo
        male_count = 0
        female_count = 0
        for s, c in by_sex:
            if s == 'M':
                male_count = c
            elif s == 'F':
                female_count = c
        
        total_employees = male_count + female_count
        
        return {
            'average_age': int(round(float(avg_age))) if avg_age else 0,
            'male_count': male_count,
            'female_count': female_count,
            'total_employees': total_employees,
            'by_sex': [{'sex': s or 'Não informado', 'count': c} for s, c in by_sex],
            'age_ranges': sorted_age_ranges
        }
    
    def handle_indicators_demographics(self):
        """Retorna perfil demográfico com evolução temporal"""
        try:
            # Parse query params
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            company = query_params.get('company', ['all'])[0]
            division = query_params.get('division', ['all'])[0]
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            months_range = int(query_params.get('months_range', ['12'])[0])
            
            if SessionLocal:
                from app.models.payroll import PayrollPeriod, PayrollData
                from app.models.employee import Employee
                from sqlalchemy import func, case
                from datetime import date
                from dateutil.relativedelta import relativedelta
                
                db = SessionLocal()
                
                # Se não especificou período, usar o mais recente
                if not year or not month:
                    latest_period = db.query(PayrollPeriod).order_by(
                        PayrollPeriod.year.desc(),
                        PayrollPeriod.month.desc()
                    ).first()
                    
                    if not latest_period:
                        db.close()
                        self.send_json_response({"error": "Nenhum período encontrado"}, 404)
                        return
                    
                    year = latest_period.year
                    month = latest_period.month
                else:
                    year = int(year)
                    month = int(month)
                
                # Calcular período atual
                current_date = date(year, month, 1)
                
                # MÉTRICA ATUAL (mês selecionado)
                current_metrics = self._get_demographics_for_period(db, year, month, company, division)
                
                # EVOLUÇÃO TEMPORAL (últimos N meses)
                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    
                    metrics = self._get_demographics_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month-1]}/{str(p_year)[2:]}",
                        'average_age': metrics['average_age'],
                        'male_count': metrics['male_count'],
                        'female_count': metrics['female_count'],
                        'total_employees': metrics['total_employees']
                    })
                
                result = {
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range
                    },
                    'current': current_metrics,
                    'evolution': evolution_data
                }
                
                db.close()
                self.send_json_response(result)
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar demographics: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def handle_indicators_tenure(self):
        """Retorna métricas de tempo de casa com evolução temporal"""
        try:
            # Parse query params
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            company = query_params.get('company', ['all'])[0]
            division = query_params.get('division', ['all'])[0]
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            months_range = int(query_params.get('months_range', ['12'])[0])
            
            if SessionLocal:
                from app.models.payroll import PayrollPeriod, PayrollData
                from app.models.employee import Employee
                from sqlalchemy import func, case
                from datetime import date
                from dateutil.relativedelta import relativedelta
                
                db = SessionLocal()
                
                # Se não especificou período, usar o mais recente
                if not year or not month:
                    latest_period = db.query(PayrollPeriod).order_by(
                        PayrollPeriod.year.desc(),
                        PayrollPeriod.month.desc()
                    ).first()
                    
                    if not latest_period:
                        db.close()
                        self.send_json_response({"error": "Nenhum período encontrado"}, 404)
                        return
                    
                    year = latest_period.year
                    month = latest_period.month
                else:
                    year = int(year)
                    month = int(month)
                
                # Calcular período atual
                current_date = date(year, month, 1)
                
                # MÉTRICA ATUAL (mês selecionado)
                current_metrics = self._get_tenure_for_period(db, year, month, company, division)
                
                # EVOLUÇÃO TEMPORAL (últimos N meses)
                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    
                    metrics = self._get_tenure_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month-1]}/{str(p_year)[2:]}",
                        'average_tenure_years': metrics['average_tenure_years'],
                        'average_tenure_months': metrics['average_tenure_months'],
                        'total_employees': metrics['total_employees']
                    })
                
                result = {
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range
                    },
                    'current': current_metrics,
                    'evolution': evolution_data
                }
                
                db.close()
                self.send_json_response(result)
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar tenure: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def _get_tenure_for_period(self, db, year, month, company='all', division='all'):
        """Helper para calcular métricas de tempo de casa de um período específico"""
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        from sqlalchemy import func, case
        from datetime import date
        
        # Buscar períodos do mês especificado
        periods_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        
        if company != 'all':
            periods_query = periods_query.filter(PayrollPeriod.company == company)
        
        periods = periods_query.all()
        if not periods:
            return {
                'average_tenure_years': 0,
                'average_tenure_months': 0,
                'total_employees': 0,
                'tenure_ranges': [],
                'by_department': []
            }
        
        period_ids = [p.id for p in periods]
        
        # Obter IDs únicos de funcionários do período
        employee_ids_query = db.query(PayrollData.employee_id).filter(
            PayrollData.period_id.in_(period_ids)
        ).distinct()
        
        employee_ids = [r[0] for r in employee_ids_query.all()]
        
        if not employee_ids:
            return {
                'average_tenure_years': 0,
                'average_tenure_months': 0,
                'total_employees': 0,
                'tenure_ranges': [],
                'by_department': []
            }
        
        # Data de referência para o cálculo
        reference_date = date(year, month, 1)
        
        # Filtrar employee_ids por division se necessário
        filtered_employee_ids = employee_ids
        if division != 'all':
            filtered_ids_query = db.query(Employee.id).filter(
                Employee.id.in_(employee_ids),
                Employee.department == division
            )
            filtered_employee_ids = [r[0] for r in filtered_ids_query.all()]
            
            if not filtered_employee_ids:
                return {
                    'average_tenure_years': 0,
                    'average_tenure_months': 0,
                    'total_employees': 0,
                    'tenure_ranges': [],
                    'by_department': []
                }
        
        # Tempo médio de casa (em dias, depois convertido para anos e meses)
        # IMPORTANTE: Não usar func.age() com extract('day') pois retorna apenas a parte de dias do interval
        # Usar subtração direta de datas para obter o total de dias
        avg_tenure_days_query = db.query(
            func.avg(
                reference_date - Employee.admission_date
            )
        ).filter(
            Employee.id.in_(filtered_employee_ids),
            Employee.admission_date.isnot(None)
        )
        
        avg_tenure_days = avg_tenure_days_query.scalar()
        
        # Converter para anos e meses
        if avg_tenure_days:
            # avg_tenure_days pode vir como timedelta ou float dependendo do DB
            if hasattr(avg_tenure_days, 'days'):
                total_days = avg_tenure_days.days
            else:
                total_days = float(avg_tenure_days)
            
            avg_tenure_years = total_days / 365.25
            avg_tenure_months = int(round(total_days / 30.44))
        else:
            avg_tenure_years = 0
            avg_tenure_months = 0
        
        # Distribuição por tempo de casa
        # Calcular anos de tempo de casa corretamente usando subtração de datas
        employees_tenure_query = db.query(Employee.name, Employee.admission_date, Employee.department, Employee.position, Employee.sex).filter(
            Employee.id.in_(filtered_employee_ids),
            Employee.admission_date.isnot(None)
        )
        emps = employees_tenure_query.all()
        
        tenure_groups = {
            'Até 6 meses': {'count': 0, 'employees': []},
            '6-12 meses': {'count': 0, 'employees': []},
            '1-3 anos': {'count': 0, 'employees': []},
            '3-5 anos': {'count': 0, 'employees': []},
            '5-10 anos': {'count': 0, 'employees': []},
            '10+ anos': {'count': 0, 'employees': []}
        }
        
        dept_totals = {}
        role_totals = {}
        gender_totals = {'M': {'total_months': 0, 'count': 0}, 'F': {'total_months': 0, 'count': 0}}
        
        for name, adm_date, dept, position, sex in emps:
            days = (reference_date - adm_date).days
            months = days / 30.44
            
            if months <= 6: bucket = 'Até 6 meses'
            elif months <= 12: bucket = '6-12 meses'
            elif days < 1095: bucket = '1-3 anos'
            elif days < 1825: bucket = '3-5 anos'
            elif days < 3650: bucket = '5-10 anos'
            else: bucket = '10+ anos'
            
            # format tenure string for display
            tenure_years_val = int(days / 365.25)
            tenure_months_val = int(round(days / 30.44)) % 12
            if tenure_years_val == 0 and tenure_months_val == 0:
                tenure_str = '0 meses'
            elif tenure_years_val == 0:
                tenure_str = f"{tenure_months_val} {'mês' if tenure_months_val == 1 else 'meses'}"
            elif tenure_months_val == 0:
                tenure_str = f"{tenure_years_val} {'ano' if tenure_years_val == 1 else 'anos'}"
            else:
                tenure_str = f"{tenure_years_val}a {tenure_months_val}m"
            
            tenure_groups[bucket]['count'] += 1
            tenure_groups[bucket]['employees'].append({
                'name': name,
                'tenure': tenure_str,
                'department': dept or 'Não informado'
            })
            
            # Acumular por departamento
            d = dept or 'Não informado'
            if d not in dept_totals:
                dept_totals[d] = {'total_months': 0, 'count': 0}
            dept_totals[d]['total_months'] += months
            dept_totals[d]['count'] += 1
            
            # Acumular por cargo
            r = position or 'Não informado'
            if r not in role_totals:
                role_totals[r] = {'total_months': 0, 'count': 0}
            role_totals[r]['total_months'] += months
            role_totals[r]['count'] += 1
            
            # Acumular por sexo
            s = sex or 'Não informado'
            if s in ['M', 'F']:
                gender_totals[s]['total_months'] += months
                gender_totals[s]['count'] += 1
            
        tenure_ranges = []
        for k in ['Até 6 meses', '6-12 meses', '1-3 anos', '3-5 anos', '5-10 anos', '10+ anos']:
            if tenure_groups[k]['count'] > 0:
                tenure_ranges.append({
                    'range': k,
                    'count': tenure_groups[k]['count'],
                    'employees': sorted(tenure_groups[k]['employees'], key=lambda x: x['name'])
                })
        
        sorted_tenure_ranges = tenure_ranges
        
        # Consolidar Tempo médio por departamento
        by_department_results = []
        for d, totals in dept_totals.items():
            if totals['count'] > 0:
                avg_months = int(round(totals['total_months'] / totals['count']))
                by_department_results.append({'department': d, 'avg_months': avg_months})
        by_department_results.sort(key=lambda x: x['department'])
        
        # Consolidar Tempo médio por cargo (Top 10)
        by_role_results = []
        for r, totals in role_totals.items():
            if totals['count'] > 0:
                avg_months = int(round(totals['total_months'] / totals['count']))
                by_role_results.append({'role': r, 'avg_months': avg_months})
        # Ordenar os cargos com maior retenção e pegar top 10
        by_role_results.sort(key=lambda x: x['avg_months'], reverse=True)
        by_role_results = by_role_results[:10]
        
        # Consolidar Tempo médio por sexo
        by_gender_results = {}
        for s, totals in gender_totals.items():
            if totals['count'] > 0:
                by_gender_results[s] = int(round(totals['total_months'] / totals['count']))
            else:
                by_gender_results[s] = 0
        
        total_employees = len(emps)
        
        return {
            'average_tenure_years': int(round(avg_tenure_years)),
            'average_tenure_months': avg_tenure_months,
            'total_employees': total_employees,
            'tenure_ranges': sorted_tenure_ranges,
            'by_department': by_department_results,
            'by_role': by_role_results,
            'by_gender': by_gender_results
        }
    
    def handle_indicators_leaves(self):
        """Retorna métricas de afastamentos com filtros e evolução"""
        try:
            from sqlalchemy import func, and_
            from app.models.employee import Employee
            from app.models.leave import LeaveRecord
            from datetime import datetime, date
            from dateutil.relativedelta import relativedelta
            
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            
            # Filtros
            company = query_params.get('company', [None])[0]
            division = query_params.get('division', [None])[0]
            
            filter_leave_types = query_params.get('leave_type', [])
            if len(filter_leave_types) == 1 and filter_leave_types[0] == 'all':
                filter_leave_types = []
            
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            months_range = int(query_params.get('months_range', ['6'])[0])
            
            db = SessionLocal()
            try:
                # Determinar período de referência
                if year and month:
                    reference_date = date(int(year), int(month), 1)
                else:
                    reference_date = date.today().replace(day=1)
                
                # Buscar tipos de afastamento disponíveis
                leave_types = db.query(LeaveRecord.leave_type).distinct().all()
                leave_types_list = [lt[0] for lt in leave_types if lt[0]]
                
                # Calcular evolução dos últimos N meses
                evolution = []
                for i in range(months_range - 1, -1, -1):
                    period_date = reference_date - relativedelta(months=i)
                    period_metrics = self._get_leaves_for_period(db, period_date, company, division, filter_leave_types)
                    evolution.append(period_metrics)
                
                # Métricas do período atual
                current_metrics = evolution[-1] if evolution else {}
                
                result = {
                    'evolution': evolution,
                    'current': current_metrics,
                    'leave_types': leave_types_list
                }
                
                self.send_json_response(result)
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao buscar leaves: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def _get_leaves_for_period(self, db, reference_date, company=None, division=None, leave_type=None):
        """Calcula métricas de afastamentos para um período específico usando LeaveRecord"""
        from sqlalchemy import func, and_, or_
        from app.models.employee import Employee
        from app.models.leave import LeaveRecord
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        # Último dia do mês
        if reference_date.month == 12:
            last_day = reference_date.replace(day=31)
        else:
            last_day = (reference_date.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)
        
        # Total de colaboradores ativos
        employees_query = db.query(Employee).filter(Employee.is_active == True)
        if company:
            employees_query = employees_query.filter(Employee.company_code == company)
        if division:
            employees_query = employees_query.filter(Employee.department == division)
        
        total_employees = employees_query.count()
        
        # Query unificada para dados nominais de afastamento
        base_query = db.query(
            Employee.id.label('emp_id'),
            Employee.name,
            Employee.department,
            Employee.position,
            Employee.company_code,
            Employee.unique_id,
            LeaveRecord.leave_type,
            LeaveRecord.days,
            LeaveRecord.start_date,
            LeaveRecord.end_date
        ).join(LeaveRecord, LeaveRecord.employee_id == Employee.id).filter(
            and_(
                Employee.is_active == True,
                LeaveRecord.start_date <= last_day,
                LeaveRecord.end_date >= reference_date
            )
        )
        
        # Aplicar filtros (Usamos match em substring para suportar null codes que começam no unique_id)
        if company and company != 'all':
            base_query = base_query.filter(
                or_(
                    Employee.company_code == company,
                    Employee.unique_id.like(f"{company}%")
                )
            )
        if division:
            base_query = base_query.filter(Employee.department == division)
        if leave_type and len(leave_type) > 0:
            base_query = base_query.filter(LeaveRecord.leave_type.in_(leave_type))
            
        leaves_data = base_query.all()
        
        unique_employees = set()
        by_type_dict = {}
        by_department_dict = {}
        by_role_dict = {}
        by_company_dict = {}
        total_duration = 0
        valid_duration_records = 0
        
        for emp_id, name, dept, pos, comp_code, uniq_id, l_type, days_col, start_d, end_d in leaves_data:
            unique_employees.add(emp_id)
            
            l_type = l_type or 'Não especificado'
            dept = dept or 'Não especificado'
            pos = pos or 'Não especificado'
            
            # TODO DEBUG
            print(f"DEBUG LEAVES: name={name}, comp={comp_code}")
            
            comp_val = str(comp_code).strip() if comp_code else ""
            if not comp_val and uniq_id and len(uniq_id) >= 4:
                comp_val = uniq_id[:4]
                
            if comp_val in ['0059', '59']:
                company_name = 'Infraestrutura'
            elif comp_val in ['0060', '60']:
                company_name = 'Empreendimentos'
            else:
                company_name = f"Matriz {comp_val}" if comp_val else 'Outra'
            
            calc_days = days_col if days_col is not None else (end_d - start_d).days if (end_d and start_d) else 0
            
            emp_obj = {
                'name': name,
                'department': dept,
                'type': l_type,
                'days': calc_days
            }
            
            # Type aggregate
            if l_type not in by_type_dict:
                by_type_dict[l_type] = {'count': 0, 'employees': []}
            by_type_dict[l_type]['count'] += 1
            by_type_dict[l_type]['employees'].append(emp_obj)
            
            # Department aggregate
            if dept not in by_department_dict:
                by_department_dict[dept] = {'count': 0, 'employees': []}
            by_department_dict[dept]['count'] += 1
            by_department_dict[dept]['employees'].append(emp_obj)
            
            # Role aggregate
            if pos not in by_role_dict:
                by_role_dict[pos] = {'count': 0, 'employees': []}
            by_role_dict[pos]['count'] += 1
            by_role_dict[pos]['employees'].append(emp_obj)
            
            # Company aggregate
            if company_name not in by_company_dict:
                by_company_dict[company_name] = {'count': 0, 'employees': []}
            by_company_dict[company_name]['count'] += 1
            by_company_dict[company_name]['employees'].append(emp_obj)
            
            # Duration avg
            total_duration += float(calc_days)
            valid_duration_records += 1
                
        total_on_leave = len(unique_employees)
        absenteeism_rate = (total_on_leave / total_employees * 100) if total_employees > 0 else 0
        avg_duration = (total_duration / valid_duration_records) if valid_duration_records > 0 else 0
        total_leaves = len(leaves_data)
        
        by_type_results = []
        for t, data in by_type_dict.items():
            by_type_results.append({
                'type': t,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda x: x['name'])
            })
            
        by_department_results = []
        for d, data in by_department_dict.items():
            by_department_results.append({
                'department': d,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda x: x['name'])
            })
        by_department_results.sort(key=lambda x: x['count'], reverse=True)
        
        by_role_results = []
        for r, data in by_role_dict.items():
            by_role_results.append({
                'role': r,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda x: x['name'])
            })
        by_role_results.sort(key=lambda x: x['count'], reverse=True)
        by_role_results = by_role_results[:10]
        
        by_company_results = []
        for c, data in by_company_dict.items():
            by_company_results.append({
                'company': c,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda x: x['name'])
            })
        by_company_results.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            'year': reference_date.year,
            'month': reference_date.month,
            'total_employees': total_employees,
            'total_on_leave': total_on_leave,
            'total_leave_records': total_leaves,
            'absenteeism_rate': round(absenteeism_rate, 2),
            'average_duration_days': round(avg_duration, 1),
            'by_type': by_type_results,
            'by_department': by_department_results,
            'by_role': by_role_results,
            'by_company': by_company_results
        }
    
    def handle_report_generate(self):
        """Gera relatório PDF com indicadores de RH"""
        try:
            from app.services.report_generator import ReportGeneratorService
            import urllib.parse
            
            # Parse query parameters
            query_string = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query_string)
            
            report_type = params.get('report_type', ['consolidated'])[0]
            sections = params.get('sections', ['overview'])[0].split(',')
            year = int(params.get('year', [datetime.now().year])[0])
            month = int(params.get('month', [datetime.now().month])[0])
            months_range = int(params.get('months_range', ['6'])[0])
            company = params.get('company', [None])[0]
            division = params.get('division', [None])[0]
            
            # Obter informações do usuário logado
            user_info = None
            current_user = getattr(self, 'current_user', None)
            if current_user:
                # current_user é um dict com os dados do usuário
                user_info = {
                    'name': current_user.get('name', 'Usuário'),
                    'email': current_user.get('email', '')
                }
            
            print(f"📊 Gerando relatório PDF: {report_type}")
            print(f"   Seções: {sections}")
            print(f"   Período: {month}/{year}")
            print(f"   Empresa: {company}, Setor: {division}")
            if user_info:
                print(f"   Emitido por: {user_info.get('name', 'N/A')}")
            
            db = SessionLocal()
            try:
                # Coletar dados de cada seção necessária
                data = {}
                
                if 'overview' in sections:
                    # Reutilizar lógica existente
                    data['overview'] = self._get_overview_data(db, year, month, company, division)
                
                if 'headcount' in sections:
                    data['headcount'] = self._get_headcount_data(db, year, month, months_range, company, division)
                
                if 'turnover' in sections:
                    data['turnover'] = self._get_turnover_data(db, year, month, months_range, company, division)
                
                if 'demographics' in sections:
                    data['demographics'] = self._get_demographics_data(db, year, month, company, division)
                
                if 'tenure' in sections:
                    data['tenure'] = self._get_tenure_data(db, year, month, company, division)
                
                if 'leaves' in sections:
                    data['leaves'] = self._get_leaves_data_for_report(db, year, month, months_range, company, division)
                
                if 'payroll' in sections:
                    data['payroll'] = self._get_payroll_data_for_report(db, year, month, company, division)
                
                # Gerar relatório moderno em HTML
                from app.services.modern_report_generator import ModernReportGenerator
                modern_service = ModernReportGenerator(db)
                html_content = modern_service.generate_report(
                    report_type=report_type,
                    sections=sections,
                    year=year,
                    month=month,
                    months_range=months_range,
                    company=company,
                    division=division,
                    data=data,
                    user_info=user_info
                )
                
                # Salvar HTML temporário e retornar URL para abrir no navegador
                import tempfile
                import webbrowser
                
                temp_dir = tempfile.gettempdir()
                month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                filename = f"NexoRH_{report_type}_{month_names[month-1]}_{year}.html"
                temp_path = os.path.join(temp_dir, filename)
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Retornar resposta JSON com caminho do arquivo
                response_data = {
                    'success': True,
                    'message': 'Relatório gerado com sucesso',
                    'file_path': temp_path,
                    'filename': filename
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                
                # Abrir no navegador automaticamente
                print(f"🌐 Abrindo relatório no navegador: {filename}")
                webbrowser.open(f'file:///{temp_path}')
                
                print(f"✅ Relatório HTML gerado com sucesso: {filename}")
                print(f"📁 Arquivo salvo em: {temp_path}")
                print(f"💡 Dica: Use Ctrl+P no navegador para imprimir ou salvar como PDF")
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    def _get_overview_data(self, db, year, month, company, division):
        """Coleta dados de overview para o relatório - usa headcount existente"""
        from datetime import date
        from sqlalchemy import func
        from app.models.leave import LeaveRecord
        from app.models.employee import Employee
        
        # Usar o método _get_headcount_for_period que já funciona
        headcount_data = self._get_headcount_for_period(db, year, month, company or 'all', division or 'all')
        
        # Período de referência para afastamentos
        reference_date = date(year, month, 1)
        last_day = date(year, month, 28)
        
        # Contar afastamentos
        on_leave = 0
        try:
            leave_query = db.query(func.count(LeaveRecord.id)).join(Employee).filter(
                LeaveRecord.start_date <= last_day,
                LeaveRecord.end_date >= reference_date
            )
            if company and company != 'all':
                leave_query = leave_query.filter(Employee.company_code == company)
            if division and division != 'all':
                leave_query = leave_query.filter(Employee.department == division)
            on_leave = leave_query.scalar() or 0
        except Exception as e:
            print(f"⚠️ Erro ao buscar afastamentos: {e}")
        
        # Calcular admissões e demissões a partir dos dados de headcount
        admissions = headcount_data.get('admissions', 0) if headcount_data.get('admissions') else 0
        terminations = headcount_data.get('terminations', 0) if headcount_data.get('terminations') else 0
        
        total_employees = headcount_data.get('headcount', 0)
        avg_employees = total_employees + (admissions - terminations) / 2
        turnover_rate = ((admissions + terminations) / (2 * avg_employees) * 100) if avg_employees > 0 else 0
        
        return {
            'current': {
                'total_employees': total_employees,
                'admissions': admissions,
                'terminations': terminations,
                'turnover_rate': turnover_rate,
                'on_leave': on_leave,
                'total_cost': headcount_data.get('total_cost', 0),
                'avg_cost_per_employee': headcount_data.get('avg_cost_per_employee', 0)
            }
        }
    
    def _get_headcount_data(self, db, year, month, months_range, company, division):
        """Coleta dados de headcount para o relatório"""
        current = self._get_headcount_for_period(db, year, month, company or 'all', division or 'all')
        
        # Formatar dados para o PDF com by_department
        by_department = []
        for div_data in current.get('top_divisions', []):
            by_department.append({
                'department': div_data.get('division', 'Não informado'),
                'count': div_data.get('count', 0)
            })
        
        return {
            'current': {
                'headcount': current.get('headcount', 0),
                'total_cost': current.get('total_cost', 0),
                'avg_cost_per_employee': current.get('avg_cost_per_employee', 0),
                'by_department': by_department,
                'by_company': current.get('by_company', [])
            }
        }
    
    def _get_turnover_data(self, db, year, month, months_range, company, division):
        """Coleta dados de turnover para o relatório - calcula admissões e demissões por mês"""
        from datetime import date
        from calendar import monthrange
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        
        evolution = []
        current_date = date(year, month, 1)
        month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        for i in range(months_range):
            m = current_date.month - i
            y = current_date.year
            while m <= 0:
                m += 12
                y -= 1
            
            # Definir período do mês
            _, last_day = monthrange(y, m)
            period_start = date(y, m, 1)
            period_end = date(y, m, last_day)
            period_label = f"{month_names[m-1]}/{y}"
            
            # Buscar funcionários ativos no período via PayrollData
            period_query = db.query(PayrollPeriod).filter(
                PayrollPeriod.year == y,
                PayrollPeriod.month == m
            )
            if company and company != 'all':
                period_query = period_query.filter(PayrollPeriod.company == company)
            periods = period_query.all()
            
            headcount = 0
            if periods:
                period_ids = [p.id for p in periods]
                employee_ids = db.query(PayrollData.employee_id).filter(
                    PayrollData.period_id.in_(period_ids)
                ).distinct().all()
                employee_ids = [e[0] for e in employee_ids]
                
                # Aplicar filtro de divisão
                if division and division != 'all' and employee_ids:
                    employees = db.query(Employee).filter(
                        Employee.id.in_(employee_ids),
                        Employee.department == division
                    ).all()
                    headcount = len(employees)
                else:
                    headcount = len(employee_ids)
            
            # Contar admissões no mês (funcionários com admission_date no mês)
            admissions_query = db.query(Employee).filter(
                Employee.admission_date >= period_start,
                Employee.admission_date <= period_end
            )
            if division and division != 'all':
                admissions_query = admissions_query.filter(Employee.department == division)
            admissions = admissions_query.count()
            
            # Contar demissões no mês (funcionários com termination_date no mês)
            terminations_query = db.query(Employee).filter(
                Employee.termination_date >= period_start,
                Employee.termination_date <= period_end
            )
            if division and division != 'all':
                terminations_query = terminations_query.filter(Employee.department == division)
            terminations = terminations_query.count()
            
            # Calcular turnover: (admissões + demissões) / média funcionários * 100
            avg_emp = headcount + (admissions - terminations) / 2 if headcount > 0 else 1
            turnover = ((admissions + terminations) / (2 * avg_emp) * 100) if avg_emp > 0 else 0
            
            evolution.insert(0, {
                'period': period_label,
                'headcount': headcount,
                'admissions': admissions,
                'terminations': terminations,
                'turnover_rate': round(turnover, 2)
            })
        
        # Dados do período atual (último da lista após ordenação)
        current_data = evolution[-1] if evolution else {'admissions': 0, 'terminations': 0, 'turnover_rate': 0, 'headcount': 0}
        
        return {
            'current': {
                'headcount': current_data.get('headcount', 0),
                'admissions': current_data.get('admissions', 0),
                'terminations': current_data.get('terminations', 0),
                'turnover_rate': current_data.get('turnover_rate', 0)
            },
            'evolution': evolution
        }
    
    def _get_demographics_data(self, db, year, month, company, division):
        """Coleta dados demográficos para o relatório"""
        from sqlalchemy import func, case
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        
        # Buscar período usando PayrollPeriod (mesmo padrão do _get_headcount_for_period)
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        if company and company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)
        
        periods = period_query.all()
        if not periods:
            return {'current': {'by_gender': [], 'by_age_range': [], 'by_education': []}}
        
        period_ids = [p.id for p in periods]
        
        # Funcionários no período
        payroll_records = db.query(PayrollData.employee_id).filter(
            PayrollData.period_id.in_(period_ids)
        ).distinct().all()
        employee_ids = [r[0] for r in payroll_records]
        
        if not employee_ids:
            return {'current': {'by_gender': [], 'by_age_range': [], 'by_education': []}}
        
        # Buscar employees com filtro de divisão
        emp_query = db.query(Employee).filter(Employee.id.in_(employee_ids))
        if division and division != 'all':
            emp_query = emp_query.filter(Employee.department == division)
        employees = emp_query.all()
        
        if not employees:
            return {'current': {'by_gender': [], 'by_age_range': [], 'by_education': []}}
        
        # Calcular distribuições manualmente (sem funções SQL complexas)
        from datetime import date
        today = date.today()
        
        # Gênero
        gender_counts = {}
        for emp in employees:
            gender = 'Masculino' if emp.sex == 'M' else 'Feminino' if emp.sex == 'F' else 'Não informado'
            gender_counts[gender] = gender_counts.get(gender, 0) + 1
        by_gender = [{'gender': k, 'count': v} for k, v in gender_counts.items()]
        
        # Faixa etária
        age_counts = {'18-24': 0, '25-34': 0, '35-44': 0, '45-54': 0, '55+': 0}
        for emp in employees:
            if emp.birth_date:
                age = (today - emp.birth_date).days // 365
                if age < 25:
                    age_counts['18-24'] += 1
                elif age < 35:
                    age_counts['25-34'] += 1
                elif age < 45:
                    age_counts['35-44'] += 1
                elif age < 55:
                    age_counts['45-54'] += 1
                else:
                    age_counts['55+'] += 1
        by_age = [{'age_range': k, 'count': v} for k, v in age_counts.items() if v > 0]
        
        return {
            'current': {
                'by_gender': by_gender,
                'by_age_range': by_age,
                'total_employees': len(employees)
            }
        }
    
    def _get_tenure_data(self, db, year, month, company, division):
        """Coleta dados de tempo de casa para o relatório"""
        from datetime import date
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        
        reference_date = date(year, month, 1)
        
        # Buscar período usando PayrollPeriod
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        if company and company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)
        
        periods = period_query.all()
        if not periods:
            return {'current': {'average_tenure_months': 0, 'by_tenure_range': []}}
        
        period_ids = [p.id for p in periods]
        
        # Funcionários no período
        payroll_records = db.query(PayrollData.employee_id).filter(
            PayrollData.period_id.in_(period_ids)
        ).distinct().all()
        employee_ids = [r[0] for r in payroll_records]
        
        if not employee_ids:
            return {'current': {'average_tenure_months': 0, 'by_tenure_range': []}}
        
        # Buscar employees com filtro de divisão
        emp_query = db.query(Employee).filter(Employee.id.in_(employee_ids))
        if division and division != 'all':
            emp_query = emp_query.filter(Employee.department == division)
        employees = emp_query.all()
        
        if not employees:
            return {'current': {'average_tenure_months': 0, 'by_tenure_range': []}}
        
        # Calcular tempo de casa manualmente
        tenure_counts = {
            'Até 6 meses': 0,
            '6 meses - 1 ano': 0,
            '1 - 2 anos': 0,
            '2 - 5 anos': 0,
            'Mais de 5 anos': 0
        }
        total_months = 0
        count_with_admission = 0
        
        for emp in employees:
            if emp.admission_date:
                months_tenure = (reference_date - emp.admission_date).days / 30
                total_months += months_tenure
                count_with_admission += 1
                
                if months_tenure < 6:
                    tenure_counts['Até 6 meses'] += 1
                elif months_tenure < 12:
                    tenure_counts['6 meses - 1 ano'] += 1
                elif months_tenure < 24:
                    tenure_counts['1 - 2 anos'] += 1
                elif months_tenure < 60:
                    tenure_counts['2 - 5 anos'] += 1
                else:
                    tenure_counts['Mais de 5 anos'] += 1
        
        avg_tenure = total_months / count_with_admission if count_with_admission > 0 else 0
        by_range = [{'range': k, 'count': v} for k, v in tenure_counts.items() if v > 0]
        
        return {
            'current': {
                'average_tenure_months': avg_tenure,
                'by_tenure_range': by_range
            }
        }
    
    def _get_leaves_data_for_report(self, db, year, month, months_range, company, division):
        """Coleta dados de afastamentos para o relatório"""
        from datetime import date
        from sqlalchemy import and_, func
        from app.models.employee import Employee
        from app.models.leave import LeaveRecord
        
        reference_date = date(year, month, 1)
        last_day = date(year, month, 28)
        
        # Total de afastamentos
        total_query = db.query(func.count(LeaveRecord.id)).join(Employee).filter(
            and_(
                Employee.is_active == True,
                LeaveRecord.start_date <= last_day,
                LeaveRecord.end_date >= reference_date
            )
        )
        if company and company != 'all':
            total_query = total_query.filter(Employee.company_code == company)
        if division and division != 'all':
            total_query = total_query.filter(Employee.department == division)
        
        total = total_query.scalar() or 0
        
        # Por tipo
        by_type_query = db.query(
            LeaveRecord.leave_type, func.count(LeaveRecord.id)
        ).join(Employee).filter(
            and_(
                Employee.is_active == True,
                LeaveRecord.start_date <= last_day,
                LeaveRecord.end_date >= reference_date
            )
        )
        if company and company != 'all':
            by_type_query = by_type_query.filter(Employee.company_code == company)
        if division and division != 'all':
            by_type_query = by_type_query.filter(Employee.department == division)
        
        by_type_results = by_type_query.group_by(LeaveRecord.leave_type).all()
        
        by_type = [{'type': t or 'Não especificado', 'count': c} for t, c in by_type_results]
        
        return {
            'current': {
                'total': total,
                'by_type': by_type
            }
        }
    
    def _get_payroll_data_for_report(self, db, year, month, company, division):
        """Coleta dados de folha de pagamento para o relatório"""
        from decimal import Decimal
        from app.models.payroll import PayrollPeriod, PayrollData
        from app.models.employee import Employee
        
        # Buscar período usando PayrollPeriod
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month
        )
        if company and company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)
        
        periods = period_query.all()
        if not periods:
            return {'current': {}}
        
        period_ids = [p.id for p in periods]
        
        # Buscar dados de folha
        payroll_records = db.query(PayrollData).filter(
            PayrollData.period_id.in_(period_ids)
        ).all()
        
        if not payroll_records:
            return {'current': {}}
        
        # Buscar employees para filtro de divisão
        employee_ids = list(set(r.employee_id for r in payroll_records))
        emp_query = db.query(Employee).filter(Employee.id.in_(employee_ids))
        employees = {e.id: e for e in emp_query.all()}
        
        # Filtrar por divisão se necessário
        if division and division != 'all':
            payroll_records = [r for r in payroll_records if employees.get(r.employee_id) and employees[r.employee_id].department == division]
        
        if not payroll_records:
            return {'current': {}}
        
        # Calcular totais
        total_salary = sum(float(r.gross_salary or 0) for r in payroll_records)
        total_net = sum(float(r.net_salary or 0) for r in payroll_records)
        
        # Calcular proventos e descontos dos campos JSON
        total_earnings = 0
        total_deductions = 0
        for r in payroll_records:
            if r.earnings_data:
                for val in r.earnings_data.values():
                    try:
                        total_earnings += float(val) if val else 0
                    except:
                        pass
            if r.deductions_data:
                for val in r.deductions_data.values():
                    try:
                        total_deductions += float(val) if val else 0
                    except:
                        pass
        
        # Se não tiver dados JSON, usar gross e net
        if total_earnings == 0:
            total_earnings = total_salary
        if total_deductions == 0 and total_salary > total_net:
            total_deductions = total_salary - total_net
        
        employee_count = len(set(r.employee_id for r in payroll_records))
        avg_salary = total_salary / employee_count if employee_count > 0 else 0
        
        # Por setor
        by_department = {}
        for r in payroll_records:
            emp = employees.get(r.employee_id)
            if emp:
                dept = emp.department or 'Não especificado'
                if dept not in by_department:
                    by_department[dept] = {'count': 0, 'total_salary': 0, 'total_net': 0, 'emp_ids': set()}
                if r.employee_id not in by_department[dept]['emp_ids']:
                    by_department[dept]['emp_ids'].add(r.employee_id)
                    by_department[dept]['count'] += 1
                by_department[dept]['total_salary'] += float(r.gross_salary or 0)
                by_department[dept]['total_net'] += float(r.net_salary or 0)
        
        by_department_list = [
            {
                'department': dept,
                'employee_count': data['count'],
                'total_salary': data['total_salary'],
                'total_earnings': data['total_salary'],  # Usando salário bruto como proventos
                'total_net': data['total_net']
            }
            for dept, data in by_department.items()
        ]
        by_department_list.sort(key=lambda x: x['total_salary'], reverse=True)
        
        return {
            'current': {
                'employee_count': employee_count,
                'total_salary': total_salary,
                'total_earnings': total_earnings,
                'total_deductions': total_deductions,
                'total_net': total_net,
                'average_salary': avg_salary,
                'by_department': by_department_list
            }
        }
    
    def handle_indicators_invalidate_cache(self):
        """Invalida cache de indicadores e employees"""
        try:
            from app.services.hr_indicators import HRIndicatorsService
            
            print("🔄 Invalidando cache de indicadores...")
            
            # Tentar obter dados do request (pode ser vazio para POST sem body)
            try:
                data = self.get_request_data()
                indicator_type = data.get('indicator_type') if data else None
            except:
                indicator_type = None
            
            # Invalidar cache de employees primeiro
            print("🗑️  Invalidando cache de employees...")
            invalidate_employees_cache()
            
            db = SessionLocal()
            try:
                service = HRIndicatorsService(db)
                print(f"🗑️  Invalidando cache de indicadores (type: {indicator_type})...")
                service.invalidate_cache(indicator_type=indicator_type)
                
                message = f"Cache invalidado: {indicator_type} + employees" if indicator_type else "Todo cache invalidado (indicators + employees)"
                print(f"✅ {message}")
                self.send_json_response({"success": True, "message": message})
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao invalidar cache: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": str(e)}, 500)
    
    # ==========================================
    
    def handle_export_payroll_batch(self):
        """Exportar lote de holerites como ZIP"""
        try:
            import os
            import zipfile
            from io import BytesIO
            
            data = self.get_request_data()
            payroll_type = data.get('payrollType', '11')
            month = int(data.get('month', datetime.now().month))
            year = int(data.get('year', datetime.now().year))
            
            print(f"📦 Exportando lote: Tipo {payroll_type}, {month}/{year}")
            
            # Determinar pasta de origem
            from app.services.payroll_formatter import PayrollFormatter
            formatter = PayrollFormatter(payroll_type, month, year)
            source_dir = formatter.output_dir
            
            if not os.path.exists(source_dir):
                self.send_json_response({"error": "Nenhum arquivo encontrado para este período"}, 404)
                return
            
            # Listar PDFs
            pdf_files = [f for f in os.listdir(source_dir) if f.endswith('.pdf') and f.startswith('EN_')]
            
            if not pdf_files:
                self.send_json_response({"error": "Nenhum arquivo PDF encontrado"}, 404)
                return
            
            print(f"📄 {len(pdf_files)} arquivos encontrados")
            
            # Criar ZIP em memória
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for pdf_file in pdf_files:
                    file_path = os.path.join(source_dir, pdf_file)
                    zip_file.write(file_path, pdf_file)
            
            zip_buffer.seek(0)
            zip_data = zip_buffer.getvalue()
            
            # Nome do arquivo ZIP
            type_name = formatter.PAYROLL_TYPES[payroll_type]
            zip_filename = f"Holerites_{type_name}_{month:02d}_{year}.zip"
            
            print(f"✅ ZIP criado: {zip_filename} ({len(zip_data)} bytes)")
            
            # Enviar ZIP com headers CORS
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', f'attachment; filename="{zip_filename}"')
            self.send_header('Content-Length', str(len(zip_data)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
            self.end_headers()
            self.wfile.write(zip_data)
            
        except Exception as e:
            print(f"❌ Erro ao exportar lote: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro ao exportar: {str(e)}"}, 500)
    
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
                    
                    # Regex MELHORADO para encontrar o número da empresa
                    # Tenta primeiro o padrão completo com cabeçalho
                    empresa_num = 'UNKNOWN_EMP'
                    header_match = re.search(
                        r'Cadastro\s+Nome\s+do\s+Funcionário\s+CBO\s+Empresa\s+Local\s+Departamento\s+FL\s*\n\s*'
                        r'(\d+)\s+([A-ZÀ-Úa-zà-ú\s\d]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
                        text
                    )
                    
                    if header_match:
                        empresa_num = header_match.group(4)  # Quarto número é a empresa
                    else:
                        # Fallback: padrão mais genérico (linha com vários números após o nome)
                        # Ex: "189 CRISTINA APARECIDA STOROZ WIL 421310 60 1 000101"
                        # Ex: "692 VITORIA DE OLIVEIRA 411005 59 1 000501"
                        generic_match = re.search(r'^\s*(\d+)\s+[A-ZÀ-Úa-zà-ú\s]+\s+(\d{4,6})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', text, re.MULTILINE)
                        if generic_match:
                            empresa_num = generic_match.group(3)  # Terceiro número = empresa
                    
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
                    from app.services.instance_manager import get_instance_manager
                    
                    # Obter instance manager
                    instance_manager = get_instance_manager()
                    
                    # Criar event loop se necessário
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # 📱 SELECIONAR PRÓXIMA INSTÂNCIA ONLINE (ROUND-ROBIN)
                    next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
                    
                    if not next_instance:
                        print(f"❌ Nenhuma instância WhatsApp online disponível")
                        failed_employees.append({
                            'id': emp_id,
                            'name': employee.get('full_name'),
                            'reason': 'Nenhuma instância WhatsApp online'
                        })
                        continue
                    
                    print(f"📱 Usando instância: {next_instance}")
                    
                    # Criar serviço com a instância selecionada
                    evolution_service = EvolutionAPIService(instance_name=next_instance)
                    
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
                        
                        # Registrar envio na instância (para tracking de delays)
                        instance_manager.register_send(next_instance)
                        print(f"✅ Envio registrado para instância: {next_instance}")
                        
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
                        
                        # 📝 REGISTRAR LOG DO SISTEMA - COMUNICADO SUCESSO
                        try:
                            from app.models.system_log import SystemLog, LogLevel, LogCategory
                            log_db = SessionLocal()
                            try:
                                log_entry = SystemLog(
                                    level=LogLevel.INFO,
                                    category=LogCategory.COMMUNICATION,
                                    message=f"Comunicado enviado: {employee.get('full_name')}",
                                    details=f"Mensagem: {message[:100] if message else '[Arquivo]'}, Telefone: {phone}, Instância: {next_instance}",
                                    user_id=user_id,
                                    entity_type='Employee',
                                    entity_id=str(emp_id)
                                )
                                log_db.add(log_entry)
                                log_db.commit()
                                print(f"📝 Log de sucesso registrado")
                            finally:
                                log_db.close()
                        except Exception as log_error:
                            print(f"⚠️ Erro ao registrar log: {log_error}")
                        
                        # Registrar no log (antigo)
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
                        
                        # 📝 REGISTRAR LOG DO SISTEMA - COMUNICADO FALHA  
                        try:
                            from app.models.system_log import SystemLog, LogLevel, LogCategory
                            log_db = SessionLocal()
                            try:
                                log_entry = SystemLog(
                                    level=LogLevel.ERROR,
                                    category=LogCategory.COMMUNICATION,
                                    message=f"Falha ao enviar comunicado: {employee.get('full_name')}",
                                    details=f"Erro: {result.get('message', 'Erro desconhecido')}, Telefone: {phone}",
                                    user_id=user_id,
                                    entity_type='Employee',
                                    entity_id=str(emp_id)
                                )
                                log_db.add(log_entry)
                                log_db.commit()
                                print(f"📝 Log de falha registrado")
                            finally:
                                log_db.close()
                        except Exception as log_error:
                            print(f"⚠️ Erro ao registrar log: {log_error}")
                
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
            
            # Os holerites segmentados ficam em subpastas dentro de processed/ (ex: processed/Mensal_11_2025/)
            # Após envio, são movidos para enviados/
            # Precisamos procurar em ambos os locais
            import os
            import glob
            
            # Obter diretório backend (onde está o main_legacy.py)
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Possíveis diretórios onde o arquivo pode estar
            possible_dirs = [
                os.path.join(backend_dir, 'enviados'),  # Arquivos já enviados
                os.path.join(backend_dir, 'processed')  # Arquivos em subpastas
            ]
            
            file_path = None
            found_in_dir = None
            
            # 1. Procurar primeiro em enviados/ (mais comum)
            enviados_dir = possible_dirs[0]
            if os.path.exists(enviados_dir):
                test_path = os.path.join(enviados_dir, filename)
                if os.path.exists(test_path):
                    file_path = test_path
                    found_in_dir = enviados_dir
                    print(f"✅ Arquivo encontrado em: enviados/")
            
            # 2. Se não encontrou, procurar nas subpastas de processed/
            if not file_path:
                processed_dir = possible_dirs[1]
                if os.path.exists(processed_dir):
                    print(f"🔍 Procurando em subpastas de processed/...")
                    # Procurar em todas as subpastas
                    for folder_name in os.listdir(processed_dir):
                        folder_path = os.path.join(processed_dir, folder_name)
                        if os.path.isdir(folder_path):
                            test_path = os.path.join(folder_path, filename)
                            if os.path.exists(test_path):
                                file_path = test_path
                                found_in_dir = folder_path
                                print(f"✅ Arquivo encontrado em: processed/{folder_name}/")
                                break
            
            # 3. Se ainda não encontrou, tentar com underscore duplo (bug antigo)
            if not file_path:
                alt_filename = filename.replace('_holerite_', '_holerite__')
                
                # Tentar em enviados/
                if os.path.exists(enviados_dir):
                    test_path = os.path.join(enviados_dir, alt_filename)
                    if os.path.exists(test_path):
                        file_path = test_path
                        found_in_dir = enviados_dir
                        filename = alt_filename
                        print(f"✅ Arquivo encontrado com underscore duplo em: enviados/")
                
                # Tentar em subpastas de processed/
                if not file_path and os.path.exists(processed_dir):
                    for folder_name in os.listdir(processed_dir):
                        folder_path = os.path.join(processed_dir, folder_name)
                        if os.path.isdir(folder_path):
                            test_path = os.path.join(folder_path, alt_filename)
                            if os.path.exists(test_path):
                                file_path = test_path
                                found_in_dir = folder_path
                                filename = alt_filename
                                print(f"✅ Arquivo encontrado com underscore duplo em: processed/{folder_name}/")
                                break
            
            # Verificar se arquivo foi encontrado
            if not file_path:
                print(f"❌ Arquivo não encontrado: {filename}")
                print(f"   Procurado em: enviados/ e todas as subpastas de processed/")
                self.send_json_response({"error": f"Arquivo não encontrado: {filename}"}, 404)
                return
            
            print(f"🔍 Caminho completo: {file_path}")
            
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
            # Removido log repetitivo - rota é chamada a cada 3 segundos pelo frontend
            
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
            # Removido log repetitivo - rota é chamada a cada 5 segundos pelo frontend
            
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

    def handle_pause_queue(self, queue_id: str):
        """Pausa uma fila em execução"""
        try:
            print(f"⏸️  Pausando fila {queue_id}...")
            
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
                success = service.pause_queue(queue_id, user.id)
                
                if success:
                    self.send_json_response({"message": "Fila pausada com sucesso"}, 200)
                else:
                    self.send_json_response({"error": "Não foi possível pausar a fila"}, 400)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao pausar fila: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_resume_queue(self, queue_id: str):
        """Retoma uma fila pausada"""
        try:
            print(f"▶️  Retomando fila {queue_id}...")
            
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
                success = service.resume_queue(queue_id, user.id)
                
                if success:
                    self.send_json_response({"message": "Fila retomada com sucesso"}, 200)
                else:
                    self.send_json_response({"error": "Não foi possível retomar a fila"}, 400)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Erro ao retomar fila: {e}")
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
    
    # ========================================
    # HANDLERS DE BENEFÍCIOS (iFood)
    # ========================================
    
    def handle_upload_benefits_xlsx(self):
        """
        Upload e processamento de arquivo XLSX de benefícios
        Endpoint: POST /api/v1/benefits/upload-xlsx
        """
        try:
            print("📊 === UPLOAD DE XLSX DE BENEFÍCIOS ===")
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                return
            
            # Get boundary
            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break
            
            if not boundary:
                self.send_json_response({"error": "Boundary não encontrado"}, 400)
                return
            
            # Read body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Parse multipart data manualmente
            import re
            import tempfile
            import shutil
            
            # Converter boundary para bytes
            boundary_bytes = f'--{boundary}'.encode()
            
            # Dividir por boundary
            parts = body.split(boundary_bytes)
            
            file_data = None
            year = None
            month = None
            company = '0060'
            
            for part in parts:
                if not part or part == b'--\r\n' or part == b'--':
                    continue
                    
                # Procurar por headers
                if b'Content-Disposition' in part:
                    # Extrair nome do campo
                    if b'name="file"' in part:
                        # Extrair dados do arquivo
                        # Formato: headers\r\n\r\nbody
                        split_point = part.find(b'\r\n\r\n')
                        if split_point != -1:
                            file_data = part[split_point + 4:].rstrip(b'\r\n')
                    
                    elif b'name="year"' in part:
                        split_point = part.find(b'\r\n\r\n')
                        if split_point != -1:
                            year = int(part[split_point + 4:].strip())
                    
                    elif b'name="month"' in part:
                        split_point = part.find(b'\r\n\r\n')
                        if split_point != -1:
                            month = int(part[split_point + 4:].strip())
                    
                    elif b'name="company"' in part:
                        split_point = part.find(b'\r\n\r\n')
                        if split_point != -1:
                            company = part[split_point + 4:].strip().decode('utf-8')
            
            # Validar dados extraídos
            if not file_data:
                self.send_json_response({"error": "Arquivo não enviado"}, 400)
                return
            
            if not year or not month:
                self.send_json_response({"error": "Ano e mês são obrigatórios"}, 400)
                return
            
            # Validar parâmetros
            if not (1 <= month <= 12):
                self.send_json_response({"error": "Mês deve estar entre 1 e 12"}, 400)
                return
            
            if company not in ['0060', '0059']:
                self.send_json_response({"error": "Empresa deve ser '0060' ou '0059'"}, 400)
                return
            
            # Salvar arquivo temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(file_data)
                tmp_filepath = tmp_file.name
            
            print(f"📁 Arquivo temporário: {tmp_filepath}")
            print(f"📅 Período: {month}/{year}")
            print(f"🏢 Empresa: {company}")
            
            try:
                # Criar sessão do banco
                db = SessionLocal()
                
                # Obter user_id do usuário autenticado
                user_id = None
                authenticated_user = self.get_authenticated_user(db)
                if authenticated_user:
                    user_id = authenticated_user.id
                    print(f"👤 Processado por: {authenticated_user.username} (ID: {user_id})")
                
                # Processar arquivo
                from app.services.benefits_xlsx_processor import BenefitsXLSXProcessor
                processor = BenefitsXLSXProcessor(db, user_id=user_id)
                
                result = processor.process_xlsx_file(
                    file_path=tmp_filepath,
                    year=year,
                    month=month,
                    company=company
                )
                
                db.close()
                
                # Remover arquivo temporário
                import os
                os.unlink(tmp_filepath)
                
                if result['success']:
                    print(f"✅ XLSX processado com sucesso!")
                    self.send_json_response(result, 200)
                else:
                    print(f"❌ Erro ao processar XLSX: {result.get('error')}")
                    self.send_json_response(result, 400)
                    
            except Exception as e:
                # Limpar arquivo temporário em caso de erro
                import os
                if os.path.exists(tmp_filepath):
                    os.unlink(tmp_filepath)
                raise
                
        except Exception as e:
            print(f"❌ Erro crítico ao processar XLSX: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }, 500)
    
    def handle_benefits_periods_list(self):
        """Lista períodos de benefícios"""
        try:
            if SessionLocal:
                from app.models.payroll import BenefitsPeriod
                
                db = SessionLocal()
                periods = db.query(BenefitsPeriod).filter(
                    BenefitsPeriod.is_active == True
                ).order_by(
                    BenefitsPeriod.year.desc(), 
                    BenefitsPeriod.month.desc()
                ).all()
                
                periods_data = []
                for period in periods:
                    # Mapear código da empresa para nome
                    company_name = "Empreendimentos" if period.company == "0060" else "Infraestrutura" if period.company == "0059" else period.company
                    
                    # Contar registros
                    from app.models.payroll import BenefitsData
                    total_records = db.query(BenefitsData).filter(
                        BenefitsData.period_id == period.id
                    ).count()
                    
                    periods_data.append({
                        "id": period.id,
                        "year": period.year,
                        "month": period.month,
                        "period_name": period.period_name,
                        "company": period.company,
                        "company_name": company_name,
                        "description": period.description,
                        "total_records": total_records,
                        "created_at": period.created_at.isoformat() if hasattr(period, 'created_at') and period.created_at else None
                    })
                
                db.close()
                self.send_json_response({"periods": periods_data, "total": len(periods_data)})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar períodos de benefícios: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_benefits_period_detail(self, period_id: str):
        """Detalhes de um período de benefícios"""
        try:
            if SessionLocal:
                from app.models.payroll import BenefitsPeriod, BenefitsData, BenefitsProcessingLog
                from app.models.employee import Employee
                
                db = SessionLocal()
                period = db.query(BenefitsPeriod).filter(BenefitsPeriod.id == int(period_id)).first()
                
                if not period:
                    db.close()
                    self.send_json_response({"error": "Período não encontrado"}, 404)
                    return
                
                # Buscar dados de benefícios
                benefits_records = db.query(BenefitsData, Employee).join(
                    Employee, BenefitsData.employee_id == Employee.id
                ).filter(BenefitsData.period_id == period.id).all()
                
                records_data = []
                for benefit, employee in benefits_records:
                    records_data.append({
                        "id": benefit.id,
                        "employee_id": employee.id,
                        "employee_name": employee.name,
                        "cpf": benefit.cpf,
                        "refeicao": float(benefit.refeicao) if benefit.refeicao else 0,
                        "alimentacao": float(benefit.alimentacao) if benefit.alimentacao else 0,
                        "mobilidade": float(benefit.mobilidade) if benefit.mobilidade else 0,
                        "livre": float(benefit.livre) if benefit.livre else 0,
                        "total": benefit.get_total_benefits()
                    })
                
                # Buscar logs de processamento
                logs = db.query(BenefitsProcessingLog).filter(
                    BenefitsProcessingLog.period_id == period.id
                ).order_by(BenefitsProcessingLog.created_at.desc()).all()
                
                logs_data = []
                for log in logs:
                    logs_data.append({
                        "id": log.id,
                        "filename": log.filename,
                        "status": log.status,
                        "total_rows": log.total_rows,
                        "processed_rows": log.processed_rows,
                        "error_rows": log.error_rows,
                        "processing_time": float(log.processing_time) if log.processing_time else 0,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    })
                
                db.close()
                
                self.send_json_response({
                    "period": {
                        "id": period.id,
                        "year": period.year,
                        "month": period.month,
                        "period_name": period.period_name,
                        "company": period.company,
                        "company_name": "Empreendimentos" if period.company == "0060" else "Infraestrutura",
                        "description": period.description
                    },
                    "records": records_data,
                    "logs": logs_data,
                    "total_records": len(records_data)
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar detalhes do período: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_delete_benefits_period(self, period_id: str):
        """Deleta um período de benefícios e todos os dados relacionados"""
        try:
            print(f"🗑️ Deletando período de benefícios ID: {period_id}")
            
            if SessionLocal:
                from app.models.payroll import BenefitsPeriod
                
                db = SessionLocal()
                period = db.query(BenefitsPeriod).filter(BenefitsPeriod.id == int(period_id)).first()
                
                if not period:
                    db.close()
                    self.send_json_response({
                        "success": False,
                        "error": "Período não encontrado"
                    }, 404)
                    return
                
                period_name = period.period_name
                
                # Deletar período (cascade vai deletar dados e logs)
                db.delete(period)
                db.commit()
                db.close()
                
                print(f"✅ Período deletado: {period_name}")
                self.send_json_response({
                    "success": True,
                    "message": f"Período '{period_name}' deletado com sucesso"
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar período: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }, 500)
    
    def handle_benefits_processing_logs(self):
        """Retorna histórico de processamento de arquivos de benefícios"""
        try:
            if SessionLocal:
                from app.models.payroll import BenefitsProcessingLog, BenefitsPeriod
                
                db = SessionLocal()
                logs = db.query(
                    BenefitsProcessingLog,
                    BenefitsPeriod.year,
                    BenefitsPeriod.month
                ).join(
                    BenefitsPeriod,
                    BenefitsProcessingLog.period_id == BenefitsPeriod.id
                ).order_by(
                    BenefitsProcessingLog.created_at.desc()
                ).limit(50).all()
                
                logs_data = []
                for log, year, month in logs:
                    logs_data.append({
                        "id": log.id,
                        "filename": log.filename,
                        "year": year,
                        "month": month,
                        "status": log.status,
                        "total_rows": log.total_rows,
                        "processed_rows": log.processed_rows,
                        "error_rows": log.error_rows,
                        "processing_time": float(log.processing_time) if log.processing_time else 0,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    })
                
                db.close()
                self.send_json_response({"logs": logs_data, "total": len(logs_data)})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar histórico de processamento: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    # ============================
    # TIMECARD HANDLERS
    # ============================
    
    def handle_timecard_periods_list(self):
        """Lista períodos de cartão ponto"""
        try:
            if SessionLocal:
                from app.models.timecard import TimecardPeriod, TimecardData
                from sqlalchemy import func
                from decimal import Decimal
                
                db = SessionLocal()
                periods = db.query(TimecardPeriod).filter(
                    TimecardPeriod.is_active == True
                ).order_by(
                    TimecardPeriod.year.desc(), 
                    TimecardPeriod.month.desc()
                ).all()
                
                periods_data = []
                for period in periods:
                    # Contar funcionários
                    employee_count = db.query(TimecardData).filter(
                        TimecardData.period_id == period.id
                    ).count()
                    
                    # Calcular totais detalhados por tipo de hora
                    totals = db.query(
                        func.sum(TimecardData.overtime_50).label('overtime_50'),
                        func.sum(TimecardData.overtime_100).label('overtime_100'),
                        func.sum(TimecardData.night_overtime_50).label('night_overtime_50'),
                        func.sum(TimecardData.night_overtime_100).label('night_overtime_100'),
                        func.sum(TimecardData.night_hours).label('night_hours')
                    ).filter(
                        TimecardData.period_id == period.id
                    ).first()
                    
                    # Converter para Decimal com valores default
                    ot50 = totals.overtime_50 or Decimal('0')
                    ot100 = totals.overtime_100 or Decimal('0')
                    not50 = totals.night_overtime_50 or Decimal('0')
                    not100 = totals.night_overtime_100 or Decimal('0')
                    nh = totals.night_hours or Decimal('0')
                    
                    periods_data.append({
                        "id": period.id,
                        "year": period.year,
                        "month": period.month,
                        "period_name": period.period_name,
                        "start_date": period.start_date.isoformat() if period.start_date else None,
                        "end_date": period.end_date.isoformat() if period.end_date else None,
                        "description": period.description,
                        "is_active": period.is_active,
                        "employee_count": employee_count,
                        # Campos individuais
                        "overtime_50": float(ot50),
                        "overtime_100": float(ot100),
                        "night_overtime_50": float(not50),
                        "night_overtime_100": float(not100),
                        "night_hours": float(nh),
                        # Totais agregados
                        "total_overtime": float(ot50 + ot100),
                        "total_night_hours": float(not50 + not100 + nh),
                        "created_at": period.created_at.isoformat() if hasattr(period, 'created_at') and period.created_at else None
                    })
                
                db.close()
                self.send_json_response({"periods": periods_data, "total": len(periods_data)})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao listar períodos de cartão ponto: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_timecard_period_detail(self, period_id: str):
        """Detalhes de um período de cartão ponto"""
        try:
            if SessionLocal:
                from app.models.timecard import TimecardPeriod, TimecardData, TimecardProcessingLog
                from decimal import Decimal
                
                db = SessionLocal()
                period = db.query(TimecardPeriod).filter(TimecardPeriod.id == int(period_id)).first()
                
                if not period:
                    db.close()
                    self.send_json_response({"error": "Período não encontrado"}, 404)
                    return
                
                # Buscar dados de cartão ponto
                timecard_records = db.query(TimecardData).filter(
                    TimecardData.period_id == period.id
                ).order_by(TimecardData.employee_name).all()
                
                records_data = []
                for record in timecard_records:
                    records_data.append({
                        "id": record.id,
                        "employee_number": record.employee_number,
                        "employee_name": record.employee_name,
                        "company": record.company,
                        "normal_hours": float(record.normal_hours or Decimal('0')),
                        "overtime_50": float(record.overtime_50 or Decimal('0')),
                        "overtime_100": float(record.overtime_100 or Decimal('0')),
                        "night_overtime_50": float(record.night_overtime_50 or Decimal('0')),
                        "night_overtime_100": float(record.night_overtime_100 or Decimal('0')),
                        "night_hours": float(record.night_hours or Decimal('0')),
                        "absences": float(record.absences or Decimal('0')),
                        "dsr_debit": float(record.dsr_debit or Decimal('0')),
                        "bonus_hours": float(record.bonus_hours or Decimal('0')),
                        "total_overtime": float(record.get_total_overtime()),
                        "total_night_hours": float(record.get_total_night_hours())
                    })
                
                # Buscar logs de processamento
                logs = db.query(TimecardProcessingLog).filter(
                    TimecardProcessingLog.period_id == period.id
                ).order_by(TimecardProcessingLog.created_at.desc()).all()
                
                logs_data = []
                for log in logs:
                    logs_data.append({
                        "id": log.id,
                        "filename": log.filename,
                        "status": log.status,
                        "total_rows": log.total_rows,
                        "processed_rows": log.processed_rows,
                        "error_rows": log.error_rows,
                        "processing_time": float(log.processing_time) if log.processing_time else 0,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    })
                
                db.close()
                
                self.send_json_response({
                    "period": {
                        "id": period.id,
                        "year": period.year,
                        "month": period.month,
                        "period_name": period.period_name,
                        "start_date": period.start_date.isoformat() if period.start_date else None,
                        "end_date": period.end_date.isoformat() if period.end_date else None,
                        "description": period.description
                    },
                    "records": records_data,
                    "logs": logs_data,
                    "total_records": len(records_data)
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar detalhes do período: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_timecard_stats(self):
        """Retorna estatísticas de cartão ponto"""
        try:
            if SessionLocal:
                from app.models.timecard import TimecardData, TimecardPeriod
                from decimal import Decimal
                
                # Obter parâmetros da query string
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                period_id = query_params.get('period_id', [None])[0]
                year = query_params.get('year', [None])[0]
                month = query_params.get('month', [None])[0]
                employees_param = query_params.get('employees', [None])[0]
                
                db = SessionLocal()
                query = db.query(TimecardData)
                
                # Filtrar por período
                if period_id:
                    query = query.filter(TimecardData.period_id == int(period_id))
                    print(f"🔍 Filtrando por period_id: {period_id}")
                elif year and month:
                    period = db.query(TimecardPeriod).filter(
                        TimecardPeriod.year == int(year),
                        TimecardPeriod.month == int(month)
                    ).first()
                    if period:
                        query = query.filter(TimecardData.period_id == period.id)
                        print(f"✅ Período encontrado: {period.period_name} (ID: {period.id})")
                    else:
                        print(f"❌ Período NÃO encontrado para year={year}, month={month}")
                        # IMPORTANTE: Retornar dados zerados se não encontrar período
                        db.close()
                        self.send_json_response({
                            "total_employees": 0,
                            "overtime_50": 0,
                            "overtime_100": 0,
                            "night_overtime_50": 0,
                            "night_overtime_100": 0,
                            "night_hours": 0,
                            "total_overtime_hours": 0,
                            "total_night_hours": 0,
                            "employees_with_overtime": 0,
                            "employees_with_night_hours": 0,
                            "average_overtime": 0,
                            "average_night_hours": 0,
                            "by_company": {}
                        })
                        return
                else:
                    print(f"⚠️ Sem filtros de período - retornando TODOS os dados de timecard")
                
                # Filtrar por colaboradores (employee_id do banco de employees)
                if employees_param:
                    employee_ids = employees_param.split(',')
                    print(f"🔍 DEBUG: employees_param recebido: '{employees_param}'")
                    print(f"🔍 DEBUG: employee_ids split: {employee_ids}")
                    
                    # O frontend envia os IDs da tabela employees (employee.id)
                    # Precisamos filtrar por employee_id (FK para employees)
                    employee_ids_int = [int(emp_id) for emp_id in employee_ids]
                    
                    query = query.filter(TimecardData.employee_id.in_(employee_ids_int))
                    print(f"✅ Filtrando por {len(employee_ids_int)} colaboradores (employee_id)")
                    print(f"   IDs: {employee_ids_int}")
                
                timecard_data = query.all()
                print(f"📊 Total de registros retornados: {len(timecard_data)}")
                
                # DEBUG: Mostrar alguns employee_numbers encontrados
                if employees_param and len(timecard_data) > 0:
                    sample = timecard_data[:5]
                    print(f"🔍 DEBUG: Primeiros employee_numbers encontrados:")
                    for d in sample:
                        print(f"   employee_number='{d.employee_number}', nome='{d.employee_name}'")
                elif employees_param and len(timecard_data) == 0:
                    # Verificar se há ALGUM registro no período
                    all_in_period = db.query(TimecardData).filter(
                        TimecardData.period_id == query.whereclause.right.value if hasattr(query.whereclause, 'right') else None
                    ).limit(5).all()
                    if all_in_period:
                        print(f"⚠️ DEBUG: Há {len(all_in_period)} registros no período, mas nenhum match. Exemplos:")
                        for d in all_in_period:
                            print(f"   employee_number='{d.employee_number}', nome='{d.employee_name}'")
                
                if not timecard_data:
                    db.close()
                    self.send_json_response({
                        "total_employees": 0,
                        "total_overtime_hours": 0,
                        "total_night_hours": 0,
                        "employees_with_overtime": 0,
                        "employees_with_night_hours": 0,
                        "average_overtime": 0,
                        "average_night_hours": 0,
                        "by_company": {}
                    })
                    return
                
                # Calcular estatísticas detalhadas por tipo de hora
                total_employees = len(timecard_data)
                
                # Somar cada tipo de hora separadamente
                sum_overtime_50 = sum((d.overtime_50 or Decimal('0') for d in timecard_data), Decimal('0'))
                sum_overtime_100 = sum((d.overtime_100 or Decimal('0') for d in timecard_data), Decimal('0'))
                sum_night_overtime_50 = sum((d.night_overtime_50 or Decimal('0') for d in timecard_data), Decimal('0'))
                sum_night_overtime_100 = sum((d.night_overtime_100 or Decimal('0') for d in timecard_data), Decimal('0'))
                sum_night_hours = sum((d.night_hours or Decimal('0') for d in timecard_data), Decimal('0'))
                
                # Totais agregados
                total_overtime = sum_overtime_50 + sum_overtime_100
                total_night = sum_night_overtime_50 + sum_night_overtime_100 + sum_night_hours
                
                employees_with_overtime = sum(1 for d in timecard_data if d.get_total_overtime() > 0)
                employees_with_night = sum(1 for d in timecard_data if d.get_total_night_hours() > 0)
                
                avg_overtime = total_overtime / total_employees if total_employees > 0 else Decimal('0')
                avg_night = total_night / total_employees if total_employees > 0 else Decimal('0')
                
                # Estatísticas por empresa
                by_company = {}
                for company in ['0059', '0060']:
                    company_data = [d for d in timecard_data if d.company == company]
                    if company_data:
                        by_company[company] = {
                            'employees': len(company_data),
                            'total_overtime': float(sum((d.get_total_overtime() for d in company_data), Decimal('0'))),
                            'total_night_hours': float(sum((d.get_total_night_hours() for d in company_data), Decimal('0'))),
                            'average_overtime': float(sum((d.get_total_overtime() for d in company_data), Decimal('0')) / len(company_data)),
                            'average_night_hours': float(sum((d.get_total_night_hours() for d in company_data), Decimal('0')) / len(company_data))
                        }
                
                db.close()
                
                self.send_json_response({
                    "total_employees": total_employees,
                    # Horas extras detalhadas
                    "overtime_50": float(sum_overtime_50),
                    "overtime_100": float(sum_overtime_100),
                    "night_overtime_50": float(sum_night_overtime_50),
                    "night_overtime_100": float(sum_night_overtime_100),
                    "night_hours": float(sum_night_hours),
                    # Totais agregados
                    "total_overtime_hours": float(total_overtime),
                    "total_night_hours": float(total_night),
                    # Contadores
                    "employees_with_overtime": employees_with_overtime,
                    "employees_with_night_hours": employees_with_night,
                    "average_overtime": float(avg_overtime),
                    "average_night_hours": float(avg_night),
                    "by_company": by_company
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar estatísticas: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_timecard_processing_logs(self):
        """Retorna histórico de processamento de arquivos de cartão ponto"""
        try:
            if SessionLocal:
                from app.models.timecard import TimecardProcessingLog, TimecardPeriod
                
                db = SessionLocal()
                logs = db.query(
                    TimecardProcessingLog,
                    TimecardPeriod.year,
                    TimecardPeriod.month
                ).join(
                    TimecardPeriod,
                    TimecardProcessingLog.period_id == TimecardPeriod.id
                ).order_by(
                    TimecardProcessingLog.created_at.desc()
                ).limit(50).all()
                
                logs_data = []
                for log, year, month in logs:
                    logs_data.append({
                        "id": log.id,
                        "filename": log.filename,
                        "year": year,
                        "month": month,
                        "status": log.status,
                        "total_rows": log.total_rows,
                        "processed_rows": log.processed_rows,
                        "error_rows": log.error_rows,
                        "processing_time": float(log.processing_time) if log.processing_time else 0,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    })
                
                db.close()
                self.send_json_response({"logs": logs_data, "total": len(logs_data)})
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao buscar histórico de processamento: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)
    
    def handle_upload_timecard_xlsx(self):
        """Handle upload e processamento de arquivo XLSX de cartão ponto"""
        try:
            from app.services.timecard_xlsx_processor import TimecardXLSXProcessor
            import tempfile
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                return
            
            # Obter boundary
            boundary = content_type.split('boundary=')[1].strip()
            
            # Ler corpo da requisição
            content_length = int(self.headers.get('Content-Length', 0))
            raw_data = self.rfile.read(content_length)
            
            # Parsear multipart data
            parts = raw_data.split(f'--{boundary}'.encode())
            
            file_content = None
            year = None
            month = None
            start_date = None
            end_date = None
            filename = None
            
            for part in parts:
                if b'Content-Disposition' in part:
                    # Extrair nome do campo
                    if b'name="file"' in part:
                        # Extrair filename
                        filename_match = re.search(b'filename="([^"]+)"', part)
                        if filename_match:
                            filename = filename_match.group(1).decode('utf-8')
                        
                        # Extrair conteúdo do arquivo
                        file_start = part.find(b'\r\n\r\n') + 4
                        file_end = len(part) - 2  # Remove trailing \r\n
                        file_content = part[file_start:file_end]
                    
                    elif b'name="year"' in part:
                        value_start = part.find(b'\r\n\r\n') + 4
                        year = int(part[value_start:].strip())
                    
                    elif b'name="month"' in part:
                        value_start = part.find(b'\r\n\r\n') + 4
                        month = int(part[value_start:].strip())
                    
                    elif b'name="start_date"' in part:
                        value_start = part.find(b'\r\n\r\n') + 4
                        start_date_bytes = part[value_start:].strip()
                        start_date = start_date_bytes.decode('utf-8') if start_date_bytes else None
                    
                    elif b'name="end_date"' in part:
                        value_start = part.find(b'\r\n\r\n') + 4
                        end_date_bytes = part[value_start:].strip()
                        end_date = end_date_bytes.decode('utf-8') if end_date_bytes else None
            
            if not file_content or not year or not month:
                self.send_json_response({
                    "error": "Arquivo, ano e mês são obrigatórios"
                }, 400)
                return
            
            # Validar extensão
            if not filename or not filename.endswith(('.xlsx', '.xls')):
                self.send_json_response({
                    "error": "Arquivo deve ser no formato XLSX ou XLS"
                }, 400)
                return
            
            # Salvar arquivo temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            print(f"📁 Arquivo temporário salvo: {tmp_path}")
            
            # Processar arquivo
            db = SessionLocal()
            current_user = getattr(self, 'current_user', None)
            user_id = current_user.get('id') if current_user else None
            
            processor = TimecardXLSXProcessor(db=db, user_id=user_id)
            result = processor.process_xlsx_file(
                file_path=tmp_path,
                year=year,
                month=month,
                start_date=start_date,
                end_date=end_date
            )
            
            db.close()
            
            # Remover arquivo temporário
            try:
                os.remove(tmp_path)
            except:
                pass
            
            if not result['success']:
                self.send_json_response({
                    "success": False,
                    "error": result.get('error', 'Erro ao processar arquivo')
                }, 400)
                return
            
            self.send_json_response({
                "success": True,
                "message": "Arquivo processado com sucesso",
                "period_id": result['period_id'],
                "period_name": result['period_name'],
                "total_rows": result['total_rows'],
                "processed_rows": result['processed_rows'],
                "error_rows": result['error_rows'],
                "warnings": result.get('warnings', []),
                "errors": result.get('errors', []),
                "processing_time": result.get('processing_time', 0)
            })
            
        except Exception as e:
            print(f"❌ Erro ao processar upload de cartão ponto: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }, 500)
    
    def handle_delete_timecard_period(self, period_id: str):
        """Deleta um período de cartão ponto e todos os dados relacionados"""
        try:
            print(f"🗑️ Deletando período de cartão ponto ID: {period_id}")
            
            if SessionLocal:
                from app.models.timecard import TimecardPeriod
                
                db = SessionLocal()
                period = db.query(TimecardPeriod).filter(TimecardPeriod.id == int(period_id)).first()
                
                if not period:
                    db.close()
                    self.send_json_response({
                        "success": False,
                        "error": "Período não encontrado"
                    }, 404)
                    return
                
                period_name = period.period_name
                
                # Deletar período (cascade vai deletar dados e logs)
                db.delete(period)
                db.commit()
                db.close()
                
                print(f"✅ Período deletado: {period_name}")
                self.send_json_response({
                    "success": True,
                    "message": f"Período '{period_name}' deletado com sucesso"
                })
                
            else:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                
        except Exception as e:
            print(f"❌ Erro ao deletar período: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                "success": False,
                "error": f"Erro interno: {str(e)}"
            }, 500)

    def handle_process_tax_statement_file(self):
        """Processa PDF consolidado de informes de rendimentos."""
        try:
            if not SessionLocal:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                return

            db = SessionLocal()
            try:
                user = self.get_authenticated_user(db)
                if not user:
                    self.send_json_response({"error": "Token de acesso necessário"}, 401)
                    return

                content_type = self.headers.get('Content-Type', '')
                if 'multipart/form-data' not in content_type:
                    self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                    return

                boundary = None
                for part in content_type.split(';'):
                    if 'boundary=' in part:
                        boundary = part.split('boundary=')[1].strip()
                        break

                if not boundary:
                    self.send_json_response({"error": "Boundary não encontrado"}, 400)
                    return

                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                file_data, filename = self.parse_multipart_data(body, boundary)

                if not file_data or not filename:
                    self.send_json_response({"error": "Arquivo não encontrado no upload"}, 400)
                    return

                if not filename.lower().endswith('.pdf'):
                    self.send_json_response({"error": "Apenas arquivos PDF são aceitos"}, 400)
                    return

                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)

                company = query.get('company', [None])[0]
                ref_year_raw = query.get('ref_year', [None])[0]
                ref_year = int(ref_year_raw) if ref_year_raw and str(ref_year_raw).isdigit() else None

                uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'tax_statements')
                os.makedirs(uploads_dir, exist_ok=True)

                timestamp = int(time.time())
                safe_filename = f"{timestamp}_{filename}"
                upload_path = os.path.join(uploads_dir, safe_filename)

                with open(upload_path, 'wb') as fp:
                    fp.write(file_data)

                from app.models.tax_statement import TaxStatementUpload
                from app.services.tax_statement_processing import process_tax_statement_pdf

                batch = TaxStatementUpload(
                    original_filename=filename,
                    file_path=upload_path,
                    file_size=len(file_data),
                    ref_year=ref_year or datetime.now().year,
                    company=company,
                    status='processing',
                    total_statements=0,
                    statements_processed=0,
                    statements_failed=0,
                    processing_started_at=datetime.now(),
                    uploaded_by=user.id,
                )
                db.add(batch)
                db.commit()
                db.refresh(batch)

                result = process_tax_statement_pdf(
                    db=db,
                    source_pdf_path=upload_path,
                    uploaded_by=user.id,
                    company=company,
                    fallback_year=ref_year,
                    output_root_dir=os.path.dirname(os.path.abspath(__file__)),
                )

                batch.status = 'completed'
                batch.total_statements = result.get('chunks_detected', 0)
                batch.statements_processed = result.get('processed_success', 0)
                batch.statements_failed = result.get('processed_failed', 0)
                batch.processing_completed_at = datetime.now()
                batch.processing_log = json.dumps(result, ensure_ascii=False)
                db.commit()

                self.send_json_response({
                    "success": True,
                    "message": "Informe de rendimentos processado com sucesso",
                    "batch_id": batch.id,
                    "summary": result,
                }, 200)

            except Exception as process_error:
                db.rollback()
                self.send_json_response({"error": f"Erro ao processar IR: {str(process_error)}"}, 500)
            finally:
                db.close()

        except Exception as e:
            self.send_json_response({"error": f"Erro interno: {str(e)}"}, 500)

    def handle_list_tax_statements(self):
        """Lista informes de rendimentos com filtros básicos para frontend."""
        try:
            if not SessionLocal:
                self.send_json_response({"error": "PostgreSQL não disponível"}, 500)
                return

            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            page = int(query.get('page', ['1'])[0])
            page_size = int(query.get('page_size', ['50'])[0])
            ref_year = query.get('ref_year', [None])[0]
            status = query.get('status', [None])[0]
            company = query.get('company', [None])[0]

            page = max(page, 1)
            page_size = min(max(page_size, 1), 200)

            from app.models.tax_statement import TaxStatement

            db = SessionLocal()
            try:
                q = db.query(TaxStatement)

                if ref_year and str(ref_year).isdigit():
                    q = q.filter(TaxStatement.ref_year == int(ref_year))
                if status:
                    q = q.filter(TaxStatement.status == status)
                if company:
                    q = q.filter(TaxStatement.company == company)

                total = q.count()
                items = (
                    q.order_by(TaxStatement.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                    .all()
                )

                payload = []
                for item in items:
                    payload.append({
                        "id": item.id,
                        "unique_id": item.unique_id,
                        "ref_year": item.ref_year,
                        "cpf": item.cpf,
                        "employee_id": item.employee_id,
                        "employee_unique_id": item.employee_unique_id,
                        "employee_name": item.employee_name,
                        "status": item.status,
                        "file_path": item.file_path,
                        "pages_count": item.pages_count,
                        "company": item.company,
                        "processing_error": item.processing_error,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    })

                self.send_json_response({
                    "tax_statements": payload,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }, 200)
            finally:
                db.close()

        except Exception as e:
            self.send_json_response({"error": f"Erro ao listar IR: {str(e)}"}, 500)

if __name__ == "__main__":
    import time
    start_time = time.time()  # Para calcular uptime
    
    # 🔇 ATIVAR FILTRO DE LOGGING SILENCIOSO
    try:
        from app.core.logging_config import setup_quiet_logging
        setup_quiet_logging()
    except ImportError:
        print("⚠️ Filtro de logging não disponível - usando logging padrão")
    
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
