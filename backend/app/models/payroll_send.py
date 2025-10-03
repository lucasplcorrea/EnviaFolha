from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class PayrollSend(Base, TimestampMixin):
    __tablename__ = "payroll_sends"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month = Column(String(7), nullable=False)  # YYYY-MM format
    status = Column(String(20), nullable=False)  # sent, failed, pending
    file_path = Column(String(500), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="payroll_sends")
    employee = relationship("Employee", back_populates="payroll_sends")
    
    def __repr__(self):
        return f"<PayrollSend(employee_id={self.employee_id}, month='{self.month}', status='{self.status}')>"