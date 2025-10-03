from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class CommunicationRecipient(Base):
    __tablename__ = "communication_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    communication_send_id = Column(Integer, ForeignKey("communication_sends.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    status = Column(String(20), nullable=False)  # sent, failed, pending
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relacionamentos
    communication_send = relationship("CommunicationSend", back_populates="recipients")
    employee = relationship("Employee", back_populates="communication_recipients")
    
    def __repr__(self):
        return f"<CommunicationRecipient(employee_id={self.employee_id}, status='{self.status}')>"