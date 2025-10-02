from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta
import os

from app.core.config import settings
from app.core.auth import create_access_token, verify_password, get_current_user
from app.models.base import engine, get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.notification import SendExecution, PayrollSend, CommunicationSend, AccessLog
from app.schemas.user import UserLogin, Token, UserResponse
from app.core.auth import get_password_hash

# Criar todas as tabelas
from app.models.base import Base
Base.metadata.create_all(bind=engine)

# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Sistema completo para envio de holerites e comunicados via WhatsApp"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
    return {
        "message": f"Sistema de Envio RH v{settings.VERSION}",
        "status": "running",
        "docs": "/docs",
        "note": "Versão sem pandas - funcionalidades de planilha limitadas"
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

@app.get("/api/v1/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": settings.VERSION,
        "pandas_available": False
    }

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
        new_employee = Employee(
            unique_id=employee_data.get("unique_id"),
            full_name=employee_data.get("full_name"),
            phone_number=employee_data.get("phone_number"),
            email=employee_data.get("email"),
            department=employee_data.get("department"),
            position=employee_data.get("position"),
            is_active=True
        )
        
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        return {"message": "Colaborador criado com sucesso", "employee": new_employee}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao criar colaborador: {str(e)}")

@app.post("/api/v1/upload/excel")
async def upload_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload de planilha Excel (limitado sem pandas)"""
    return {
        "message": "Funcionalidade de upload de Excel não disponível sem pandas",
        "suggestion": "Use o formulário manual para adicionar colaboradores"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
