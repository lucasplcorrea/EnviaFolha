from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(20), unique=True, index=True, nullable=False)  # Para holerites
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    department = Column(String(50), nullable=True)
    position = Column(String(50), nullable=True)
    company_code = Column(String(10), nullable=True)
    registration_number = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Para comunicados
    sector = Column(String(50), nullable=True)
    workplace = Column(String(50), nullable=True)
    
    # Relacionamentos
    payroll_sends = relationship("PayrollSend", back_populates="employee")
    communication_sends = relationship("CommunicationSend", back_populates="employee")
    
    def __repr__(self):
        return f"<Employee(id='{self.unique_id}', name='{self.full_name}')>"
