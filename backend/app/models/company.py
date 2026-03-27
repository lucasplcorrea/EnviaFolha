from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """Empresas do grupo (ex: Infraestrutura - 0059, Empreendimentos - 0060)"""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)                  # Nome da empresa (ex: Infraestrutura)
    trade_name = Column(String(255), nullable=True)             # Nome fantasia
    cnpj = Column(String(18), nullable=True, unique=True)       # XX.XXX.XXX/XXXX-XX
    payroll_prefix = Column(String(10), nullable=False)         # Prefixo da matrícula (ex: 0059, 0060)
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    # Relacionamentos
    work_locations = relationship("WorkLocation", back_populates="company")
    employees = relationship("Employee", back_populates="company")

    def __repr__(self):
        return f"<Company(name='{self.name}', prefix='{self.payroll_prefix}')>"
