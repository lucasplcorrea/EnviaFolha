from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Configurações básicas
    APP_NAME: str = "Sistema de Envio RH"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Configurações do banco de dados
    DATABASE_URL: str = "postgresql://enviafolha_user:secure_password@localhost:5432/enviafolha_db"
    
    # Configurações PostgreSQL individuais
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "enviafolha_db"
    DB_USER: str = "enviafolha_user"
    DB_PASSWORD: str = "secure_password"
    PORT: str = "8002"
    
    # Configurações de autenticação
    SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configurações da Evolution API
    EVOLUTION_SERVER_URL: Optional[str] = None
    EVOLUTION_API_KEY: Optional[str] = None
    EVOLUTION_INSTANCE_NAME: Optional[str] = None
    
    # Configurações de upload
    UPLOAD_FOLDER: str = "uploads"
    MAX_FILE_SIZE: int = 60 * 1024 * 1024  # 60MB
    
    # Configurações de notificação
    ADMIN_WHATSAPP_NUMBER: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Permite campos extras
        case_sensitive = True

settings = Settings()

# Criar diretórios necessários
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs("processed", exist_ok=True)
os.makedirs("sent", exist_ok=True)
