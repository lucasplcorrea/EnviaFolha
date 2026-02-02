"""
Router para endpoints de Benefícios iFood
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List
import tempfile
import os

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.payroll import BenefitsPeriod, BenefitsData, BenefitsProcessingLog
from app.models.employee import Employee
from app.models.user import User
from app.services.benefits_xlsx_processor import BenefitsXLSXProcessor
from pydantic import BaseModel
from datetime import datetime


router = APIRouter(
    prefix="/benefits",
    tags=["benefits"]
)


# ===== Schemas =====

class BenefitRecordResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    cpf: str
    refeicao: float
    alimentacao: float
    mobilidade: float
    livre: float
    total: float


class ProcessingLogResponse(BaseModel):
    id: int
    filename: str
    status: str
    total_rows: int | None
    processed_rows: int | None
    error_rows: int | None
    processing_time: float | None
    created_at: datetime | None


class BenefitsPeriodResponse(BaseModel):
    id: int
    year: int
    month: int
    period_name: str
    company: str
    company_name: str
    description: str | None
    total_records: int
    created_at: datetime | None


class BenefitsPeriodDetailResponse(BaseModel):
    period: dict
    records: List[BenefitRecordResponse]
    logs: List[ProcessingLogResponse]
    total_records: int


# ===== Endpoints =====

@router.post("/upload-xlsx")
async def upload_benefits_xlsx(
    file: UploadFile = File(...),
    year: int = Form(...),
    month: int = Form(...),
    company: str = Form('0060'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload e processamento de arquivo XLSX de benefícios iFood
    
    Args:
        file: Arquivo XLSX com colunas: CPF, Refeicao, Alimentacao, Mobilidade, Livre
        year: Ano do período
        month: Mês do período (1-12)
        company: Código da empresa ('0060' = Empreendimentos, '0059' = Infraestrutura)
    
    Returns:
        Resultado do processamento com estatísticas e avisos
    """
    # Validar parâmetros
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")
    
    if company not in ['0060', '0059']:
        raise HTTPException(status_code=400, detail="Empresa deve ser '0060' ou '0059'")
    
    # Validar tipo de arquivo
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")
    
    # Salvar arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        contents = await file.read()
        tmp_file.write(contents)
        tmp_filepath = tmp_file.name
    
    try:
        # Processar arquivo
        processor = BenefitsXLSXProcessor(db, user_id=current_user.id)
        
        result = processor.process_xlsx_file(
            file_path=tmp_filepath,
            year=year,
            month=month,
            company=company
        )
        
        return result
        
    finally:
        # Limpar arquivo temporário
        if os.path.exists(tmp_filepath):
            os.unlink(tmp_filepath)


@router.get("/periods", response_model=dict)
async def list_benefits_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todos os períodos de benefícios cadastrados
    
    Returns:
        Lista de períodos com estatísticas
    """
    periods = db.query(BenefitsPeriod).filter(
        BenefitsPeriod.is_active == True
    ).order_by(
        BenefitsPeriod.year.desc(), 
        BenefitsPeriod.month.desc()
    ).all()
    
    periods_data = []
    for period in periods:
        # Mapear código da empresa para nome
        company_name = (
            "Empreendimentos" if period.company == "0060" 
            else "Infraestrutura" if period.company == "0059" 
            else period.company
        )
        
        # Contar registros
        total_records = db.query(BenefitsData).filter(
            BenefitsData.period_id == period.id
        ).count()
        
        periods_data.append({
            "id": period.id,
            "year": period.year,
            "month": period.month,
            "period_name": period.period_name,
            "company": period.company,
            "company_name": company_name,
            "description": period.description,
            "total_records": total_records,
            "created_at": period.created_at.isoformat() if hasattr(period, 'created_at') and period.created_at else None
        })
    
    return {"periods": periods_data, "total": len(periods_data)}


@router.get("/periods/{period_id}", response_model=dict)
async def get_benefits_period_detail(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna detalhes de um período específico de benefícios
    
    Args:
        period_id: ID do período
    
    Returns:
        Detalhes do período, registros de benefícios e logs de processamento
    """
    period = db.query(BenefitsPeriod).filter(BenefitsPeriod.id == period_id).first()
    
    if not period:
        raise HTTPException(status_code=404, detail="Período não encontrado")
    
    # Buscar dados de benefícios
    benefits_records = db.query(BenefitsData, Employee).join(
        Employee, BenefitsData.employee_id == Employee.id
    ).filter(BenefitsData.period_id == period.id).all()
    
    records_data = []
    for benefit, employee in benefits_records:
        records_data.append({
            "id": benefit.id,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "cpf": benefit.cpf,
            "refeicao": float(benefit.refeicao) if benefit.refeicao else 0,
            "alimentacao": float(benefit.alimentacao) if benefit.alimentacao else 0,
            "mobilidade": float(benefit.mobilidade) if benefit.mobilidade else 0,
            "livre": float(benefit.livre) if benefit.livre else 0,
            "total": benefit.get_total_benefits()
        })
    
    # Buscar logs de processamento
    logs = db.query(BenefitsProcessingLog).filter(
        BenefitsProcessingLog.period_id == period.id
    ).order_by(BenefitsProcessingLog.created_at.desc()).all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            "id": log.id,
            "filename": log.filename,
            "status": log.status,
            "total_rows": log.total_rows,
            "processed_rows": log.processed_rows,
            "error_rows": log.error_rows,
            "processing_time": float(log.processing_time) if log.processing_time else 0,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })
    
    return {
        "period": {
            "id": period.id,
            "year": period.year,
            "month": period.month,
            "period_name": period.period_name,
            "company": period.company,
            "company_name": "Empreendimentos" if period.company == "0060" else "Infraestrutura",
            "description": period.description
        },
        "records": records_data,
        "logs": logs_data,
        "total_records": len(records_data)
    }


@router.delete("/periods/{period_id}")
async def delete_benefits_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deleta um período de benefícios e todos os dados relacionados
    
    Args:
        period_id: ID do período a deletar
    
    Returns:
        Confirmação de deleção
    """
    period = db.query(BenefitsPeriod).filter(BenefitsPeriod.id == period_id).first()
    
    if not period:
        raise HTTPException(status_code=404, detail="Período não encontrado")
    
    period_name = period.period_name
    
    # Deletar período (cascade vai deletar dados e logs)
    db.delete(period)
    db.commit()
    
    return {
        "success": True,
        "message": f"Período '{period_name}' deletado com sucesso"
    }
