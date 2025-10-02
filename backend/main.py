from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import timedelta
import os

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
