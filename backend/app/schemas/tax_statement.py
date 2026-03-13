from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ===========================
# Tax Statement Schemas
# ===========================

class TaxStatementBase(BaseModel):
    """Schema base para Informe de Rendimentos"""
    ref_year: int = Field(..., description="Ano-calendário do informe")
    cpf: str = Field(..., description="CPF do beneficiário (formato: XXX.XXX.XXX-XX)")
    company: Optional[str] = Field(None, description="Empresa emissora")
    notes: Optional[str] = Field(None, description="Observações")


class TaxStatementCreate(TaxStatementBase):
    """Schema para criação de Informe de Rendimentos"""
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    pages_count: int = 2
    employee_unique_id: Optional[str] = None
    employee_name: Optional[str] = None
    password: Optional[str] = None


class TaxStatementUpdate(BaseModel):
    """Schema para atualização de Informe de Rendimentos"""
    status: Optional[str] = None
    processing_error: Optional[str] = None
    whatsapp_status: Optional[str] = None
    whatsapp_message_id: Optional[str] = None
    notes: Optional[str] = None


class TaxStatementResponse(TaxStatementBase):
    """Schema de resposta para Informe de Rendimentos"""
    id: int
    unique_id: str
    original_filename: str
    file_path: str
    file_size: Optional[int]
    pages_count: int
    employee_id: Optional[int]
    employee_unique_id: Optional[str]
    employee_name: Optional[str]
    status: str
    processing_error: Optional[str]
    sent_at: Optional[datetime]
    sent_by: Optional[int]
    whatsapp_instance: Optional[str]
    whatsapp_status: Optional[str]
    whatsapp_message_id: Optional[str]
    uploaded_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaxStatementListResponse(BaseModel):
    """Schema para listagem de Informes de Rendimentos"""
    statements: List[TaxStatementResponse]
    total: int
    page: int
    page_size: int


class TaxStatementSendRequest(BaseModel):
    """Schema para requisição de envio de Informe de Rendimentos"""
    statement_ids: List[int] = Field(..., description="IDs dos informes a enviar")
    message_template: Optional[str] = Field(None, description="Template de mensagem personalizada")


class TaxStatementSendResponse(BaseModel):
    """Schema de resposta para envio de Informes de Rendimentos"""
    success_count: int
    failed_count: int
    success_statements: List[int]
    failed_statements: List[dict]  # [{"id": int, "error": str}]


# ===========================
# Tax Statement Upload Schemas
# ===========================

class TaxStatementUploadCreate(BaseModel):
    """Schema para criação de upload de Informes de Rendimentos"""
    original_filename: str
    file_path: str
    file_size: Optional[int] = None
    ref_year: int
    company: Optional[str] = None


class TaxStatementUploadUpdate(BaseModel):
    """Schema para atualização de upload de Informes de Rendimentos"""
    status: Optional[str] = None
    total_statements: Optional[int] = None
    statements_processed: Optional[int] = None
    statements_failed: Optional[int] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_log: Optional[str] = None


class TaxStatementUploadResponse(BaseModel):
    """Schema de resposta para upload de Informes de Rendimentos"""
    id: int
    original_filename: str
    file_path: str
    file_size: Optional[int]
    ref_year: int
    company: Optional[str]
    status: str
    total_statements: int
    statements_processed: int
    statements_failed: int
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    processing_log: Optional[str]
    uploaded_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaxStatementUploadListResponse(BaseModel):
    """Schema para listagem de uploads de Informes de Rendimentos"""
    uploads: List[TaxStatementUploadResponse]
    total: int
    page: int
    page_size: int


# ===========================
# Filter Schemas
# ===========================

class TaxStatementFilterParams(BaseModel):
    """Parâmetros de filtro para Informes de Rendimentos"""
    ref_year: Optional[int] = None
    company: Optional[str] = None
    status: Optional[str] = None
    employee_unique_id: Optional[str] = None
    cpf: Optional[str] = None
    search: Optional[str] = None  # Busca em nome, CPF, matrícula
    page: int = 1
    page_size: int = 50
