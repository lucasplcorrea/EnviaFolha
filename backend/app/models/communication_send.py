from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class CommunicationSend(Base, TimestampMixin):
    __tablename__ = "communication_sends"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Permitir NULL para envios legados
    title = Column(String(255), nullable=True)  # Título opcional para identificação
    message = Column(Text, nullable=True)  # Mensagem de texto (pode ser None se só enviar arquivo)
    file_path = Column(String(500), nullable=True)
    total_recipients = Column(Integer, nullable=False, default=0)
    successful_sends = Column(Integer, nullable=False, default=0)
    failed_sends = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False)  # pending, sending, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="communication_sends")
    recipients = relationship("CommunicationRecipient", back_populates="communication_send")
    
    def __repr__(self):
        return f"<CommunicationSend(id={self.id}, status='{self.status}', recipients={self.total_recipients})>"