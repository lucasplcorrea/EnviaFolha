from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.sql import func
from .base import Base
import enum

class LogLevel(enum.Enum):
    """Níveis de log do sistema"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(enum.Enum):
    """Categorias de log do sistema"""
    SYSTEM = "SYSTEM"
    AUTH = "AUTH"
    EMPLOYEE = "EMPLOYEE"
    IMPORT = "IMPORT"
    PAYROLL = "PAYROLL"
    COMMUNICATION = "COMMUNICATION"
    WHATSAPP = "WHATSAPP"
    DATABASE = "DATABASE"
    API = "API"

class SystemLog(Base):
    """
    Tabela de logs do sistema para rastreabilidade completa.
    Armazena eventos, erros, ações de usuários e atividades do sistema.
    """
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Informações do log
    level = Column(Enum(LogLevel), nullable=False, default=LogLevel.INFO, index=True)
    category = Column(Enum(LogCategory), nullable=False, default=LogCategory.SYSTEM, index=True)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string com detalhes adicionais
    
    # Contexto da ação
    user_id = Column(Integer, nullable=True, index=True)  # ID do usuário (se aplicável)
    username = Column(String(100), nullable=True)  # Nome do usuário
    entity_type = Column(String(100), nullable=True)  # Tipo de entidade (Employee, Payroll, etc)
    entity_id = Column(String(100), nullable=True)  # ID da entidade afetada
    
    # Informações da requisição
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_path = Column(String(500), nullable=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemLog(level={self.level}, category={self.category}, message='{self.message[:50]}...')>"
    
    def to_dict(self):
        """Converte o log para dicionário"""
        return {
            'id': self.id,
            'level': self.level.value if self.level else None,
            'category': self.category.value if self.category else None,
            'message': self.message,
            'details': self.details,
            'user_id': self.user_id,
            'username': self.username,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
