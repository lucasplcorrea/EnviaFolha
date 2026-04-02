from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Configurações básicas
    APP_NAME: str = "Sistema de Envio RH"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Configurações do banco de dados
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/dbname"
    
    # Configurações PostgreSQL individuais
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "enviafolha_db"
    DB_USER: str = "enviafolha_user"
    DB_PASSWORD: str = ""
    PORT: str = "8002"
    
    # Configurações de autenticação
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configurações da Evolution API
    EVOLUTION_SERVER_URL: Optional[str] = None
    EVOLUTION_API_KEY: Optional[str] = None
    EVOLUTION_INSTANCE_NAME: Optional[str] = None
    EVOLUTION_INSTANCE_NAME2: Optional[str] = None  # Segunda instância (opcional)
    EVOLUTION_INSTANCE_NAME3: Optional[str] = None  # Terceira instância (opcional)
    
    # Configurações de Email SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "Sistema RH <rh@empresa.com>"
    SMTP_USE_TLS: bool = True
    
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

    def get_evolution_instances(self) -> list:
        """Retorna lista de instâncias WhatsApp configuradas"""
        instances = []
        if self.EVOLUTION_INSTANCE_NAME:
            instances.append(self.EVOLUTION_INSTANCE_NAME)
        if self.EVOLUTION_INSTANCE_NAME2:
            instances.append(self.EVOLUTION_INSTANCE_NAME2)
        if self.EVOLUTION_INSTANCE_NAME3:
            instances.append(self.EVOLUTION_INSTANCE_NAME3)
        return instances
    
    def has_smtp_configured(self) -> bool:
        """Verifica se SMTP está configurado"""
        return all([self.SMTP_HOST, self.SMTP_USER, self.SMTP_PASSWORD])

settings = Settings()

# Criar diretórios necessários
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
os.makedirs("processed", exist_ok=True)
os.makedirs("sent", exist_ok=True)
