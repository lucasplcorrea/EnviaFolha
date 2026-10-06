"""Modelo para cache de indicadores de RH"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Date, Index
from datetime import datetime
from .base import Base, TimestampMixin


class HRIndicatorSnapshot(Base, TimestampMixin):
    """
    Armazena snapshots calculados de indicadores de RH.
    Reduz carga no banco ao cachear métricas agregadas.
    """
    __tablename__ = "hr_indicator_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identificação do snapshot
    indicator_type = Column(String(50), nullable=False, index=True)  # 'headcount', 'turnover', 'demographics', etc
    calculation_date = Column(Date, nullable=False, index=True)  # Data do cálculo
    period_start = Column(Date, nullable=True)  # Início do período analisado (para métricas temporais)
    period_end = Column(Date, nullable=True)  # Fim do período analisado
    
    # Dados agregados (JSON flexível)
    metrics = Column(JSON, nullable=False)  # Armazena todas as métricas calculadas
    
    # Metadados
    total_records = Column(Integer, nullable=True)  # Quantidade de registros analisados
    calculation_time_ms = Column(Integer, nullable=True)  # Tempo de processamento em milissegundos
    is_valid = Column(Integer, default=1)
    
    # Índices compostos para queries otimizadas
    __table_args__ = (
        Index('idx_type_date', 'indicator_type', 'calculation_date'),
        Index('idx_type_period', 'indicator_type', 'period_start', 'period_end'),
    )
    
    def __repr__(self):
        return f"<HRIndicatorSnapshot(type='{self.indicator_type}', date={self.calculation_date}, valid={bool(self.is_valid)})>"
