from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class TaxStatement(Base, TimestampMixin):
    """Modelo para Informes de Rendimentos"""
    __tablename__ = "tax_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(50), unique=True, index=True, nullable=False)  # Formato: IR_MATRICULA_ANO
    
    # Informações do arquivo
    original_filename = Column(String(255), nullable=False)  # Nome do PDF original
    file_path = Column(String(500), nullable=False)  # Caminho do PDF processado
    file_size = Column(Integer, nullable=True)  # Tamanho em bytes
    
    # Informações do informe
    ref_year = Column(Integer, nullable=False, index=True)  # Ano-calendário (ex: 2025)
    cpf = Column(String(14), nullable=False, index=True)  # CPF do beneficiário
    pages_count = Column(Integer, default=2)  # Número de páginas do informe
    
    # Relacionamento com funcionário
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    employee_unique_id = Column(String(50), nullable=True, index=True)  # Matrícula
    employee_name = Column(String(255), nullable=True)  # Nome (para facilitar consultas)
    
    # Status de processamento
    status = Column(String(20), default="pending", nullable=False)  # pending, processed, sent, failed
    password = Column(String(10), nullable=True)  # Senha do PDF (primeiros 4 dígitos do CPF)
    processing_error = Column(Text, nullable=True)  # Erro de processamento, se houver
    
    # Informações de envio
    sent_at = Column(DateTime, nullable=True)  # Data/hora do envio
    sent_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Usuário que enviou
    whatsapp_instance = Column(String(100), nullable=True)  # Instância do WhatsApp usada
    whatsapp_status = Column(String(50), nullable=True)  # Status do envio WhatsApp
    whatsapp_message_id = Column(String(255), nullable=True)  # ID da mensagem no WhatsApp
    
    # Metadados
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Quem fez upload
    company = Column(String(100), nullable=True, index=True)  # Empresa (AB EMPREENDIMENTOS, AB INFRAESTRUTURA)
    notes = Column(Text, nullable=True)  # Observações
    
    # Relacionamentos
    employee = relationship("Employee", foreign_keys=[employee_id], backref="tax_statements")
    uploader = relationship("User", foreign_keys=[uploaded_by], backref="uploaded_tax_statements")
    sender = relationship("User", foreign_keys=[sent_by], backref="sent_tax_statements")
    
    def __repr__(self):
        return f"<TaxStatement(unique_id='{self.unique_id}', cpf='{self.cpf}', year={self.ref_year}, status='{self.status}')>"


class TaxStatementUpload(Base, TimestampMixin):
    """Modelo para controle de uploads de Informes de Rendimentos"""
    __tablename__ = "tax_statement_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Informações do upload
    original_filename = Column(String(255), nullable=False)  # Nome do PDF original unificado
    file_path = Column(String(500), nullable=False)  # Caminho do arquivo original
    file_size = Column(Integer, nullable=True)  # Tamanho em bytes
    ref_year = Column(Integer, nullable=False, index=True)  # Ano-calendário
    company = Column(String(100), nullable=True, index=True)  # Empresa
    
    # Status de processamento
    status = Column(String(20), default="processing", nullable=False)  # processing, completed, failed
    total_statements = Column(Integer, default=0)  # Total de informes encontrados
    statements_processed = Column(Integer, default=0)  # Informes processados com sucesso
    statements_failed = Column(Integer, default=0)  # Informes que falharam
    
    # Informações de processamento
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_log = Column(Text, nullable=True)  # Log de processamento
    
    # Metadados
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relacionamentos
    uploader = relationship("User", foreign_keys=[uploaded_by], backref="tax_statement_upload_batches")
    
    def __repr__(self):
        return f"<TaxStatementUpload(filename='{self.original_filename}', year={self.ref_year}, status='{self.status}')>"
