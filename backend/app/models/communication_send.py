from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class CommunicationSend(Base, TimestampMixin):
    __tablename__ = "communication_sends"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=True)
    total_recipients = Column(Integer, nullable=False, default=0)
    successful_sends = Column(Integer, nullable=False, default=0)
    failed_sends = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False)  # pending, sending, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="communication_sends")
    recipients = relationship("CommunicationRecipient", back_populates="communication_send")
    
    def __repr__(self):
        return f"<CommunicationSend(title='{self.title}', status='{self.status}')>"