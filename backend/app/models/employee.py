from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    # --- Identidade ---
    # absolute_id: chave única definitiva = Código_Empresa + Matrícula + CPF_numérico
    # Garante unicidade mesmo com erros contábeis ou readmissões com mesma matrícula.
    absolute_id = Column(String(80), unique=True, index=True, nullable=True)

    # unique_id: matrícula composta (prefixo empresa + número), mantida para compatibilidade.
    # unique=True REMOVIDO: contabilidade pode reutilizar a mesma matrícula.
    unique_id = Column(String(50), index=True, nullable=True)

    # cpf: mantido para exibição/referência, mas unique=True REMOVIDO.
    # Um mesmo CPF pode ter mais de um contrato (demissão + readmissão).
    cpf = Column(String(14), index=True, nullable=True)

    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)

    # --- Estrutura Organizacional ---
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    company_code = Column(String(20), nullable=True)          # Prefixo numérico (ex: 0059)
    registration_number = Column(String(20), nullable=True)   # Número cru da matrícula

    # FK para empresa cadastrada
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    # FK para local/obra de alocação
    work_location_id = Column(Integer, ForeignKey("work_locations.id"), nullable=True, index=True)

    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # --- Dados Demográficos e Contratuais ---
    birth_date = Column(Date, nullable=True)
    sex = Column(String(10), nullable=True)
    marital_status = Column(String(50), nullable=True)
    admission_date = Column(Date, nullable=True)
    contract_type = Column(String(50), nullable=True)

    # --- Status Operacional ---
    employment_status = Column(String(50), nullable=True)   # Ativo, Afastado, Desligado, Férias
    termination_date = Column(Date, nullable=True)
    leave_start_date = Column(Date, nullable=True)
    leave_end_date = Column(Date, nullable=True)
    status_reason = Column(Text, nullable=True)

    # --- Relacionamentos ---
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_employees")
    updater = relationship("User", foreign_keys=[updated_by], back_populates="updated_employees")
    company = relationship("Company", back_populates="employees")
    work_location = relationship("WorkLocation", back_populates="employees")
    payrolls = relationship("PayrollRecord", back_populates="employee")
    benefits = relationship("BenefitRecord", back_populates="employee")
    movements = relationship("MovementRecord", back_populates="employee")
    leaves = relationship("LeaveRecord", back_populates="employee")
    payroll_sends = relationship("PayrollSend", back_populates="employee", overlaps="payrolls")
    communication_recipients = relationship("CommunicationRecipient", back_populates="employee")
    payroll_data = relationship("PayrollData", back_populates="employee")

    def __repr__(self):
        return f"<Employee(absolute_id='{self.absolute_id}', name='{self.name}')\>"
