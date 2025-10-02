from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta
import os
from typing import List
import PyPDF2
import shutil

# Importações locais com tratamento de erro
try:
    from app.core.config import settings
    from app.core.auth import create_access_token, verify_password, get_current_user
    from app.models.base import engine, get_db
    from app.models.user import User
    from app.models.employee import Employee
    from app.schemas.user import UserLogin, Token, UserResponse
    from app.core.auth import get_password_hash
    
    # Criar todas as tabelas
    from app.models.base import Base
    Base.metadata.create_all(bind=engine)
    
    # Criar diretórios necessários
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("processed", exist_ok=True)
    os.makedirs("enviados", exist_ok=True)
    
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("⚠️ Usando configuração mínima...")
    
    # Configuração mínima para teste
    class Settings:
        APP_NAME = "Sistema de Envio RH"
        VERSION = "2.0.0"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        SECRET_KEY = "test-secret-key"
        ALGORITHM = "HS256"
    
    settings = Settings()

# Criar aplicação FastAPI
app = FastAPI(
    title=getattr(settings, 'APP_NAME', 'Sistema de Envio RH'),
    version=getattr(settings, 'VERSION', '2.0.0'),
    description="Sistema completo para envio de holerites e comunicados via WhatsApp"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Criar diretórios necessários
os.makedirs("uploads", exist_ok=True)

# Servir arquivos estáticos
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except Exception as e:
    print(f"⚠️ Erro ao montar arquivos estáticos: {e}")

@app.on_event("startup")
async def startup_event():
    """Criar usuário admin padrão se não existir"""
    db = next(get_db())
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@empresa.com",
                full_name="Administrador",
                hashed_password=get_password_hash("admin123"),
                is_admin=True,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("✅ Usuário admin criado (admin/admin123)")
        else:
            print("✅ Usuário admin já existe")
    except Exception as e:
        print(f"❌ Erro ao criar usuário admin: {e}")
    finally:
        db.close()

@app.get("/")
async def root():
    """Endpoint de teste"""
    try:
        # Testar pandas
        import pandas as pd
        pandas_version = pd.__version__
        pandas_status = "✅ Disponível"
    except ImportError:
        pandas_version = "N/A"
        pandas_status = "❌ Não disponível"
    
    try:
        import numpy as np
        numpy_version = np.__version__
        numpy_status = "✅ Disponível"
    except ImportError:
        numpy_version = "N/A"
        numpy_status = "❌ Não disponível"
    
    return {
        "message": f"Sistema de Envio RH v{getattr(settings, 'VERSION', '2.0.0')}",
        "status": "running",
        "docs": "/docs",
        "dependencies": {
            "pandas": {"version": pandas_version, "status": pandas_status},
            "numpy": {"version": numpy_version, "status": numpy_status},
            "fastapi": "✅ Funcionando"
        }
    }

@app.get("/api/v1/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "healthy",
        "version": getattr(settings, 'VERSION', '2.0.0'),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    }

@app.post("/api/v1/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Endpoint de login"""
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Usuário inativo"
        )
    
    # Criar token de acesso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    # Atualizar último login
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Obter informações do usuário atual"""
    return UserResponse.from_orm(current_user)

@app.get("/api/v1/employees")
async def list_employees(
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Listar colaboradores"""
    employees = db.query(Employee).filter(Employee.is_active == True).offset(skip).limit(limit).all()
    return employees

@app.post("/api/v1/employees")
async def create_employee(
    employee_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Criar novo colaborador"""
    try:
        # Verificar se unique_id já existe
        existing = db.query(Employee).filter(
            Employee.unique_id == employee_data.get("unique_id"),
            Employee.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"ID único {employee_data.get('unique_id')} já existe")
        
        new_employee = Employee(**employee_data)
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        return new_employee
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao criar colaborador: {str(e)}")

@app.get("/api/v1/employees/{employee_id}")
async def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter colaborador por ID"""
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.is_active == True
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    
    return employee

@app.put("/api/v1/employees/{employee_id}")
async def update_employee(
    employee_id: int,
    employee_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualizar colaborador"""
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.is_active == True
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    
    try:
        # Verificar se o novo unique_id já existe (se foi alterado)
        if "unique_id" in employee_data and employee_data["unique_id"] != employee.unique_id:
            existing = db.query(Employee).filter(
                Employee.unique_id == employee_data["unique_id"],
                Employee.is_active == True,
                Employee.id != employee_id
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail=f"ID único {employee_data['unique_id']} já existe")
        
        # Atualizar campos
        for field, value in employee_data.items():
            if hasattr(employee, field):
                setattr(employee, field, value)
        
        db.commit()
        db.refresh(employee)
        
        return employee
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar colaborador: {str(e)}")

@app.delete("/api/v1/employees/{employee_id}")
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Excluir colaborador (soft delete)"""
    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.is_active == True
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado")
    
    employee.is_active = False
    db.commit()
    
    return {"message": "Colaborador removido com sucesso"}

@app.post("/api/v1/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload de arquivos (holerites, comunicados)"""
    try:
        # Verificar tamanho do arquivo
        if file.size and file.size > getattr(settings, 'MAX_FILE_SIZE', 25 * 1024 * 1024):
            raise HTTPException(status_code=400, detail="Arquivo muito grande")
        
        # Gerar nome único
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join("uploads", filename)
        
        # Salvar arquivo
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "filename": filename,
            "original_name": file.filename,
            "file_path": file_path,
            "size": len(content),
            "upload_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro no upload: {str(e)}")

@app.post("/api/v1/communications/send")
async def send_communications(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enviar comunicados para colaboradores selecionados"""
    try:
        from app.services.evolution_api import EvolutionAPIService
        
        selected_employees = request_data.get("selectedEmployees", [])
        message = request_data.get("message", "")
        uploaded_file = request_data.get("uploadedFile")
        
        if not selected_employees:
            raise HTTPException(status_code=400, detail="Nenhum colaborador selecionado")
        
        if not message and not uploaded_file:
            raise HTTPException(status_code=400, detail="Mensagem ou arquivo é obrigatório")
        
        # Buscar colaboradores
        employees = db.query(Employee).filter(
            Employee.id.in_(selected_employees),
            Employee.is_active == True
        ).all()
        
        if not employees:
            raise HTTPException(status_code=404, detail="Nenhum colaborador válido encontrado")
        
        evolution_service = EvolutionAPIService()
        
        # Verificar status da conexão
        if not await evolution_service.check_instance_status():
            raise HTTPException(status_code=503, detail="Evolution API não está conectada")
        
        success_count = 0
        failed_employees = []
        
        for employee in employees:
            try:
                # Validar telefone
                from app.services.phone_validator import PhoneValidator
                validator = PhoneValidator()
                
                if not validator.is_valid_whatsapp_number(employee.phone_number):
                    failed_employees.append({
                        "employee": employee.full_name,
                        "error": "Número de telefone inválido"
                    })
                    continue
                
                # Enviar mensagem
                if uploaded_file:
                    file_path = uploaded_file.get("file_path")
                    if os.path.exists(file_path):
                        success = await evolution_service.send_communication_message(
                            phone=employee.phone_number,
                            message_text=message if message else None,
                            file_path=file_path
                        )
                    else:
                        failed_employees.append({
                            "employee": employee.full_name,
                            "error": "Arquivo não encontrado"
                        })
                        continue
                else:
                    success = await evolution_service.send_communication_message(
                        phone=employee.phone_number,
                        message_text=message
                    )
                
                if success:
                    success_count += 1
                else:
                    failed_employees.append({
                        "employee": employee.full_name,
                        "error": "Falha no envio"
                    })
                
                # Delay entre envios
                evolution_service._add_random_delay()
                
            except Exception as e:
                failed_employees.append({
                    "employee": employee.full_name,
                    "error": str(e)
                })
        
        return {
            "success_count": success_count,
            "total_count": len(employees),
            "failed_employees": failed_employees,
            "message": f"Enviado para {success_count} de {len(employees)} colaboradores"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro no envio: {str(e)}")

@app.get("/api/v1/evolution/status")
async def check_evolution_status():
    """Verificar status da Evolution API"""
    try:
        from app.services.evolution_api import EvolutionAPIService
        
        if not all([getattr(settings, 'EVOLUTION_SERVER_URL', None), 
                   getattr(settings, 'EVOLUTION_API_KEY', None), 
                   getattr(settings, 'EVOLUTION_INSTANCE_NAME', None)]):
            return {
                "connected": False,
                "error": "Configurações da Evolution API não encontradas no .env",
                "config": {
                    "server_url": bool(getattr(settings, 'EVOLUTION_SERVER_URL', None)),
                    "api_key": bool(getattr(settings, 'EVOLUTION_API_KEY', None)),
                    "instance_name": bool(getattr(settings, 'EVOLUTION_INSTANCE_NAME', None))
                }
            }
        
        evolution_service = EvolutionAPIService()
        connected = await evolution_service.check_instance_status()
        
        return {
            "connected": connected,
            "instance_name": getattr(settings, 'EVOLUTION_INSTANCE_NAME', None),
            "server_url": getattr(settings, 'EVOLUTION_SERVER_URL', None)
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": f"Erro ao verificar status: {str(e)}"
        }

@app.post("/api/v1/payroll/process")
async def process_payroll_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Processar arquivos de holerites na pasta uploads"""
    try:
        uploads_dir = "uploads"
        processed_dir = "processed"
        
        if not os.path.exists(uploads_dir):
            raise HTTPException(status_code=404, detail="Pasta uploads não encontrada")
        
        files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
        
        if not files:
            raise HTTPException(status_code=404, detail="Nenhum arquivo PDF encontrado na pasta uploads")
        
        # Buscar todos os colaboradores ativos
        employees = db.query(Employee).filter(Employee.is_active == True).all()
        employee_map = {emp.unique_id: emp for emp in employees}
        
        processed_files = []
        errors = []
        
        for filename in files:
            file_path = os.path.join(uploads_dir, filename)
            
            try:
                # Tentar extrair unique_id do nome do arquivo
                # Assumindo formato: UNIQUE_ID_algo.pdf ou UNIQUE_ID.pdf
                name_parts = filename.replace('.pdf', '').split('_')
                unique_id = name_parts[0]
                
                if unique_id not in employee_map:
                    errors.append(f"Colaborador com ID {unique_id} não encontrado para arquivo {filename}")
                    continue
                
                employee = employee_map[unique_id]
                
                # Mover arquivo para pasta processed com nome padronizado
                processed_filename = f"{unique_id}_{employee.full_name.replace(' ', '_')}.pdf"
                processed_path = os.path.join(processed_dir, processed_filename)
                
                shutil.copy2(file_path, processed_path)
                
                processed_files.append({
                    "original_filename": filename,
                    "processed_filename": processed_filename,
                    "employee_id": employee.id,
                    "employee_name": employee.full_name,
                    "employee_phone": employee.phone_number,
                    "unique_id": unique_id
                })
                
            except Exception as e:
                errors.append(f"Erro ao processar {filename}: {str(e)}")
        
        return {
            "processed_files": processed_files,
            "total_processed": len(processed_files),
            "errors": errors,
            "total_errors": len(errors)
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro no processamento: {str(e)}")

@app.post("/api/v1/payroll/send")
async def send_payroll_files(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enviar holerites processados via WhatsApp"""
    try:
        from app.services.evolution_api import EvolutionAPIService
        
        processed_files = request_data.get("processedFiles", [])
        month_year = request_data.get("monthYear", "")
        
        if not processed_files:
            raise HTTPException(status_code=400, detail="Nenhum arquivo para enviar")
        
        if not month_year:
            raise HTTPException(status_code=400, detail="Mês/Ano é obrigatório")
        
        evolution_service = EvolutionAPIService()
        
        # Verificar status da conexão
        if not await evolution_service.check_instance_status():
            raise HTTPException(status_code=503, detail="Evolution API não está conectada")
        
        processed_dir = "processed"
        sent_dir = "enviados"
        
        success_count = 0
        failed_employees = []
        
        for file_info in processed_files:
            try:
                file_path = os.path.join(processed_dir, file_info["processed_filename"])
                
                if not os.path.exists(file_path):
                    failed_employees.append({
                        "employee": file_info["employee_name"],
                        "error": "Arquivo não encontrado"
                    })
                    continue
                
                # Buscar colaborador
                employee = db.query(Employee).filter(Employee.id == file_info["employee_id"]).first()
                
                if not employee:
                    failed_employees.append({
                        "employee": file_info["employee_name"],
                        "error": "Colaborador não encontrado no banco"
                    })
                    continue
                
                # Validar telefone
                from app.services.phone_validator import PhoneValidator
                validator = PhoneValidator()
                
                if not validator.is_valid_whatsapp_number(employee.phone_number):
                    failed_employees.append({
                        "employee": employee.full_name,
                        "error": "Número de telefone inválido"
                    })
                    continue
                
                # Mensagem personalizada
                message = f"""🧾 *Holerite {month_year}*

Olá {employee.full_name}!

Seu holerite referente ao período de *{month_year}* está disponível.

📄 O arquivo está protegido com senha.
🔑 *Senha:* Os 4 primeiros dígitos do seu CPF

Qualquer dúvida, entre em contato com o RH.

_Mensagem automática do Sistema RH_"""

                # Enviar via Evolution API
                success = await evolution_service.send_payroll_message(
                    phone=employee.phone_number,
                    message_text=message,
                    file_path=file_path,
                    filename=f"Holerite_{month_year}_{employee.full_name}.pdf"
                )
                
                if success:
                    success_count += 1
                    
                    # Mover arquivo para pasta enviados
                    sent_filename = f"{month_year}_{file_info['processed_filename']}"
                    sent_path = os.path.join(sent_dir, sent_filename)
                    
                    try:
                        shutil.move(file_path, sent_path)
                    except Exception as move_error:
                        print(f"Erro ao mover arquivo {file_path}: {move_error}")
                else:
                    failed_employees.append({
                        "employee": employee.full_name,
                        "error": "Falha no envio via WhatsApp"
                    })
                
                # Delay entre envios (30±10 segundos)
                evolution_service._add_random_delay(30, 10)
                
            except Exception as e:
                failed_employees.append({
                    "employee": file_info.get("employee_name", "Desconhecido"),
                    "error": str(e)
                })
        
        return {
            "success_count": success_count,
            "total_count": len(processed_files),
            "failed_employees": failed_employees,
            "message": f"Enviado para {success_count} de {len(processed_files)} colaboradores"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro no envio: {str(e)}")

# Endpoint de login simples (sem banco por enquanto)
@app.post("/api/v1/auth/login")
async def login_simple(credentials: dict):
    """Login simples para teste"""
    if credentials.get("username") == "admin" and credentials.get("password") == "admin123":
        return {
            "access_token": "test-token",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "username": "admin",
                "full_name": "Administrador",
                "email": "admin@empresa.com",
                "is_admin": True
            }
        }
    else:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

if __name__ == "__main__":
    import uvicorn
    import sys
    print(f"🚀 Iniciando servidor Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print("📡 Acesse: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
