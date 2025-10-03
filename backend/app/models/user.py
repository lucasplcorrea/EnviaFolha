from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamentos
    created_employees = relationship("Employee", foreign_keys="Employee.created_by", back_populates="creator")
    updated_employees = relationship("Employee", foreign_keys="Employee.updated_by", back_populates="updater")
    audit_logs = relationship("AuditLog", back_populates="user")
    payroll_sends = relationship("PayrollSend", back_populates="user")
    communication_sends = relationship("CommunicationSend", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
