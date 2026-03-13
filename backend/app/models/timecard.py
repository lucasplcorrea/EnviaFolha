"""
Modelos de banco de dados para o sistema de Cartão Ponto
"""
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DECIMAL, JSON, Date
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class TimecardPeriod(Base, TimestampMixin):
    """Modelo para períodos de cartão ponto"""
    __tablename__ = "timecard_periods"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    period_name = Column(String(100), nullable=False)  # Ex: "Fevereiro 2025"
    start_date = Column(Date, nullable=True)  # Data início do período
    end_date = Column(Date, nullable=True)  # Data fim do período
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relacionamentos
    timecard_data = relationship("TimecardData", back_populates="period", cascade="all, delete-orphan")
    processing_logs = relationship("TimecardProcessingLog", back_populates="period", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TimecardPeriod(period='{self.period_name}', year={self.year}, month={self.month})>"


class TimecardData(Base, TimestampMixin):
    """Modelo para dados de cartão ponto por colaborador"""
    __tablename__ = "timecard_data"
    
    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey('timecard_periods.id', ondelete='CASCADE'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=True)  # Pode não encontrar
    
    # Identificação
    employee_number = Column(String(20), nullable=False, index=True)  # Nº Folha (matrícula)
    employee_name = Column(String(255), nullable=True)
    company = Column(String(50), nullable=False)  # '0060' ou '0059' baseado no "E"
    
    # Horas normais
    normal_hours = Column(DECIMAL(10, 2), nullable=True, default=0)
    
    # Horas extras
    overtime_50 = Column(DECIMAL(10, 2), nullable=True, default=0)  # Ex50%
    overtime_100 = Column(DECIMAL(10, 2), nullable=True, default=0)  # Ex100%
    
    # Horas extras noturnas
    night_overtime_50 = Column(DECIMAL(10, 2), nullable=True, default=0)  # EN50%
    night_overtime_100 = Column(DECIMAL(10, 2), nullable=True, default=0)  # EN100%
    
    # Horas noturnas
    night_hours = Column(DECIMAL(10, 2), nullable=True, default=0)  # Not.
    
    # Outras horas
    absences = Column(DECIMAL(10, 2), nullable=True, default=0)  # Faltas
    dsr_debit = Column(DECIMAL(10, 2), nullable=True, default=0)  # DSR.Deb
    bonus_hours = Column(DECIMAL(10, 2), nullable=True, default=0)  # Abono2
    
    # Metadados
    upload_filename = Column(String(500), nullable=True)
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relacionamentos
    period = relationship("TimecardPeriod", back_populates="timecard_data")
    employee = relationship("Employee")
    processor = relationship("User")
    
    def __repr__(self):
        return f"<TimecardData(employee_number='{self.employee_number}', period_id={self.period_id})>"
    
    def get_total_overtime(self):
        """Calcula total de horas extras (50% + 100%)"""
        total = Decimal('0')
        if self.overtime_50:
            total += self.overtime_50
        if self.overtime_100:
            total += self.overtime_100
        return total
    
    def get_total_night_hours(self):
        """Calcula total de horas noturnas (EN50% + EN100% + Not.)"""
        total = Decimal('0')
        if self.night_overtime_50:
            total += self.night_overtime_50
        if self.night_overtime_100:
            total += self.night_overtime_100
        if self.night_hours:
            total += self.night_hours
        return total


class TimecardProcessingLog(Base, TimestampMixin):
    """Log de processamento de planilhas de cartão ponto"""
    __tablename__ = "timecard_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey('timecard_periods.id', ondelete='CASCADE'), nullable=False)
    
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
    period = relationship("TimecardPeriod", back_populates="processing_logs")
    processor = relationship("User")
    
    def __repr__(self):
        return f"<TimecardProcessingLog(filename='{self.filename}', status='{self.status}')>"
