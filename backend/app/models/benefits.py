"""
Modelos de banco de dados para o sistema de Benefícios iFood
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DECIMAL, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class BenefitsPeriod(Base, TimestampMixin):
    """Modelo para períodos de benefícios (iFood)"""
    __tablename__ = "benefits_periods"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    period_name = Column(String(100), nullable=False)  # Ex: "Janeiro 2026"
    company = Column(String(50), nullable=False)  # '0060' = Empreendimentos, '0059' = Infraestrutura
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relacionamentos
    benefits_data = relationship("BenefitsData", back_populates="period", cascade="all, delete-orphan")
    processing_logs = relationship("BenefitsProcessingLog", back_populates="period", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BenefitsPeriod(period='{self.period_name}', year={self.year}, month={self.month}, company={self.company})>"


class BenefitsData(Base, TimestampMixin):
    """Modelo para dados de benefícios iFood por colaborador"""
    __tablename__ = "benefits_data"
    
    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey('benefits_periods.id', ondelete='CASCADE'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    
    # CPF é mantido para referência e validação
    cpf = Column(String(20), nullable=False, index=True)  # Formato: XXX.XXX.XXX-XX
    
    # Valores dos benefícios
    refeicao = Column(DECIMAL(10, 2), nullable=True, default=0)
    alimentacao = Column(DECIMAL(10, 2), nullable=True, default=0)
    mobilidade = Column(DECIMAL(10, 2), nullable=True, default=0)
    livre = Column(DECIMAL(10, 2), nullable=True, default=0)
    
    # Metadados
    upload_filename = Column(String(500), nullable=True)
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relacionamentos
    period = relationship("BenefitsPeriod", back_populates="benefits_data")
    employee = relationship("Employee")
    processor = relationship("User")
    
    def __repr__(self):
        return f"<BenefitsData(cpf='{self.cpf}', period_id={self.period_id})>"
    
    def get_total_benefits(self):
        """Calcula total de benefícios"""
        total = 0
        if self.refeicao:
            total += float(self.refeicao)
        if self.alimentacao:
            total += float(self.alimentacao)
        if self.mobilidade:
            total += float(self.mobilidade)
        if self.livre:
            total += float(self.livre)
        return total


class BenefitsProcessingLog(Base, TimestampMixin):
    """Log de processamento de planilhas de benefícios"""
    __tablename__ = "benefits_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey('benefits_periods.id', ondelete='CASCADE'), nullable=False)
    
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, nullable=True)
    error_rows = Column(Integer, nullable=True)
    
    # Resultado do processamento
    status = Column(String(50), nullable=False)  # 'processing', 'completed', 'failed', 'partial'
    error_message = Column(Text, nullable=True)
    processing_summary = Column(JSON, nullable=True)
    
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    processing_time = Column(DECIMAL(5, 2), nullable=True)
    
    # Relacionamentos
    period = relationship("BenefitsPeriod", back_populates="processing_logs")
    processor = relationship("User")
    
    def __repr__(self):
        return f"<BenefitsProcessingLog(filename='{self.filename}', status='{self.status}')>"
