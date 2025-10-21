from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    cpf = Column(String(11), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    company_code = Column(String(20), nullable=True)
    registration_number = Column(String(20), nullable=True)
    sector = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Additional fields for metrics
    birth_date = Column(Date, nullable=True)
    sex = Column(String(10), nullable=True)
    marital_status = Column(String(50), nullable=True)
    admission_date = Column(Date, nullable=True)
    contract_type = Column(String(50), nullable=True)
    
    # Status detalhado
    employment_status = Column(String(50), nullable=True)  # Ativo, Afastado, Desligado, Férias
    termination_date = Column(Date, nullable=True)  # Data de desligamento
    leave_start_date = Column(Date, nullable=True)  # Data início afastamento/férias
    leave_end_date = Column(Date, nullable=True)  # Data prevista de retorno
    status_reason = Column(Text, nullable=True)  # Motivo detalhado do status

    # Relacionamentos
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_employees")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_employees")
    payrolls = relationship("PayrollRecord", back_populates="employee")
    benefits = relationship("BenefitRecord", back_populates="employee")
    movements = relationship("MovementRecord", back_populates="employee")
    leaves = relationship("LeaveRecord", back_populates="employee")
    # Backwards-compatible relationship name used by legacy code
    # Some existing modules expect Employee.payroll_data (PayrollData model).
    # Keep it here as an alias to the legacy PayrollData relationship so both
    # new and old code can coexist during migration.
    payroll_data = relationship("PayrollData", back_populates="employee")

    def __repr__(self):
        return f"<Employee(unique_id='{self.unique_id}', name='{self.name}')>"
