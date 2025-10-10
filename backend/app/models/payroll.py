from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, DECIMAL, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class PayrollPeriod(Base, TimestampMixin):
    """Modelo para períodos de folha de pagamento"""
    __tablename__ = "payroll_periods"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    period_name = Column(String(100), nullable=False)  # Ex: "Janeiro 2024", "13º Salário 2024"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_closed = Column(Boolean, default=False)  # Período fechado não pode ser alterado
    
    # Relacionamentos
    payroll_data = relationship("PayrollData", back_populates="period")
    
    def __repr__(self):
        return f"<PayrollPeriod(period='{self.period_name}', year={self.year}, month={self.month})>"

class PayrollData(Base, TimestampMixin):
    """Modelo para dados dinâmicos de folha de pagamento"""
    __tablename__ = "payroll_data"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    period_id = Column(Integer, ForeignKey('payroll_periods.id'), nullable=False)
    
    # Dados básicos sempre presentes
    gross_salary = Column(DECIMAL(10, 2), nullable=True)  # Salário bruto
    net_salary = Column(DECIMAL(10, 2), nullable=True)   # Salário líquido
    
    # JSON para armazenar dados dinâmicos
    earnings_data = Column(JSON, nullable=True)    # Proventos (salário, horas extras, etc)
    deductions_data = Column(JSON, nullable=True)  # Descontos (INSS, IR, etc)
    benefits_data = Column(JSON, nullable=True)    # Benefícios (vale transporte, alimentação, etc)
    additional_data = Column(JSON, nullable=True)  # Outros dados específicos
    
    # Metadados sobre o processamento
    upload_filename = Column(String(255), nullable=True)  # Nome do arquivo origem
    upload_date = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relacionamentos
    employee = relationship("Employee", back_populates="payroll_data")
    period = relationship("PayrollPeriod", back_populates="payroll_data")
    processor = relationship("User")
    
    def __repr__(self):
        return f"<PayrollData(employee_id={self.employee_id}, period='{self.period.period_name}')>"
    
    def get_earnings_total(self):
        """Calcula total de proventos"""
        if not self.earnings_data:
            return 0
        return sum(float(value) for value in self.earnings_data.values() if isinstance(value, (int, float, str)) and str(value).replace('.', '').replace(',', '').isdigit())
    
    def get_deductions_total(self):
        """Calcula total de descontos"""
        if not self.deductions_data:
            return 0
        return sum(float(value) for value in self.deductions_data.values() if isinstance(value, (int, float, str)) and str(value).replace('.', '').replace(',', '').isdigit())

class PayrollTemplate(Base, TimestampMixin):
    """Template para mapear colunas de planilhas Excel"""
    __tablename__ = "payroll_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Mapeamento de colunas (JSON)
    column_mapping = Column(JSON, nullable=False)
    # Exemplo: {
    #   "employee_identifier": "CPF",  # Coluna que identifica o funcionário
    #   "earnings": ["Salário Base", "Horas Extras", "Adicional Noturno"],
    #   "deductions": ["INSS", "IRRF", "Vale Transporte"],
    #   "benefits": ["Vale Alimentação", "Plano de Saúde"]
    # }
    
    # Configurações de processamento
    skip_rows = Column(Integer, default=0)  # Linhas a pular no início
    header_row = Column(Integer, default=1)  # Linha do cabeçalho
    
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relacionamentos
    creator = relationship("User")
    
    def __repr__(self):
        return f"<PayrollTemplate(name='{self.name}')>"

class PayrollProcessingLog(Base, TimestampMixin):
    """Log de processamento de planilhas de folha"""
    __tablename__ = "payroll_processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey('payroll_periods.id'), nullable=False)
    template_id = Column(Integer, ForeignKey('payroll_templates.id'), nullable=True)
    
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, nullable=True)
    error_rows = Column(Integer, nullable=True)
    
    # Resultado do processamento
    status = Column(String(50), nullable=False)  # 'processing', 'completed', 'failed', 'partial'
    error_message = Column(Text, nullable=True)
    processing_summary = Column(JSON, nullable=True)  # Resumo detalhado
    
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    processing_time = Column(DECIMAL(5, 2), nullable=True)  # Tempo em segundos
    
    # Relacionamentos
    period = relationship("PayrollPeriod")
    template = relationship("PayrollTemplate")
    processor = relationship("User")
    
    def __repr__(self):
        return f"<PayrollProcessingLog(filename='{self.filename}', status='{self.status}')>"