from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    cpf = Column(String(11), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    company_code = Column(String(20), nullable=True)
    registration_number = Column(String(20), nullable=True)
    sector = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relacionamentos
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_employees")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_employees")
    # payroll_sends = relationship("PayrollSend", back_populates="employee")
    # communication_recipients = relationship("CommunicationRecipient", back_populates="employee")
    payroll_data = relationship("PayrollData", back_populates="employee")
    
    def __repr__(self):
        return f"<Employee(unique_id='{self.unique_id}', name='{self.name}')>"
