from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .base import Base, TimestampMixin

class SendStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SendType(enum.Enum):
    PAYROLL = "payroll"
    COMMUNICATION = "communication"

class SendExecution(Base, TimestampMixin):
    """Controla execuções de envio"""
    __tablename__ = "send_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(50), unique=True, index=True, nullable=False)
    send_type = Column(Enum(SendType), nullable=False)
    total_employees = Column(Integer, default=0)
    processed_employees = Column(Integer, default=0)
    successful_sends = Column(Integer, default=0)
    failed_sends = Column(Integer, default=0)
    status = Column(Enum(SendStatus), default=SendStatus.PENDING)
    started_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relacionamentos
    user = relationship("User")
    payroll_sends = relationship("PayrollSend", back_populates="execution")
    communication_sends = relationship("CommunicationSend", back_populates="execution")

class PayrollSend(Base, TimestampMixin):
    """Controla envios individuais de holerites"""
    __tablename__ = "payroll_sends"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("send_executions.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    file_path = Column(String(255), nullable=False)
    formatted_phone = Column(String(20), nullable=False)
    status = Column(Enum(SendStatus), default=SendStatus.PENDING)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    month_year = Column(String(20), nullable=False)
    
    # Relacionamentos
    execution = relationship("SendExecution", back_populates="payroll_sends")
    employee = relationship("Employee", back_populates="payroll_sends")

class CommunicationSend(Base, TimestampMixin):
    """Controla envios individuais de comunicados"""
    __tablename__ = "communication_sends"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("send_executions.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    file_path = Column(String(255), nullable=True)
    message_text = Column(Text, nullable=True)
    formatted_phone = Column(String(20), nullable=False)
    status = Column(Enum(SendStatus), default=SendStatus.PENDING)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    execution = relationship("SendExecution", back_populates="communication_sends")
    employee = relationship("Employee", back_populates="communication_sends")

class AccessLog(Base, TimestampMixin):
    """Log de acessos ao sistema"""
    __tablename__ = "access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    
    # Relacionamento
    user = relationship("User")
