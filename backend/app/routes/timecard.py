"""
Rotas da API para gerenciamento de Cartão Ponto
"""
import logging
import os
import shutil
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.employee import Employee
from app.models.timecard import TimecardPeriod, TimecardData, TimecardProcessingLog
from app.models.user import User
from app.services.timecard_xlsx_processor import TimecardXLSXProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/timecard", tags=["timecard"])


# Schemas Pydantic
class TimecardDataResponse(BaseModel):
    id: int
    employee_number: str
    employee_name: str
    company: str
    normal_hours: Optional[Decimal]
    overtime_50: Optional[Decimal]
    overtime_100: Optional[Decimal]
    night_overtime_50: Optional[Decimal]
    night_overtime_100: Optional[Decimal]
    night_hours: Optional[Decimal]
    absences: Optional[Decimal]
    dsr_debit: Optional[Decimal]
    bonus_hours: Optional[Decimal]
    
    class Config:
        from_attributes = True


class TimecardPeriodResponse(BaseModel):
    id: int
    year: int
    month: int
    period_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    description: Optional[str]
    is_active: bool
    employee_count: int = 0
    # Horas extras detalhadas
    overtime_50: Optional[Decimal] = None
    overtime_100: Optional[Decimal] = None
    night_overtime_50: Optional[Decimal] = None
    night_overtime_100: Optional[Decimal] = None
    night_hours: Optional[Decimal] = None
    # Totais (para compatibilidade)
    total_overtime: Optional[Decimal] = None
    total_night_hours: Optional[Decimal] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TimecardProcessingLogResponse(BaseModel):
    id: int
    filename: str
    file_size: Optional[int]
    total_rows: int
    processed_rows: int
    error_rows: int
    status: str
    processing_time: Optional[Decimal]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TimecardPeriodDetail(TimecardPeriodResponse):
    timecard_data: List[TimecardDataResponse] = []
    processing_logs: List[TimecardProcessingLogResponse] = []


class TimecardStats(BaseModel):
    total_employees: int
    # Horas extras detalhadas
    overtime_50: Decimal  # HE 50%
    overtime_100: Decimal  # HE 100%
    night_overtime_50: Decimal  # HE Noturna 50%
    night_overtime_100: Decimal  # HE Noturna 100%
    night_hours: Decimal  # Adicional Noturno
    intrajornada_hours: Decimal
    dsr_debit_hours: Decimal
    # Totais agregados (para compatibilidade)
    total_overtime_hours: Decimal
    total_night_hours: Decimal
    # Contadores
    employees_with_overtime: int
    employees_with_night_hours: int
    employees_with_intrajornada: int
    employees_with_dsr_debit: int
    average_overtime: Decimal
    average_night_hours: Decimal
    average_intrajornada: Decimal
    average_dsr_debit: Decimal
    by_company: dict


@router.post("/upload-xlsx", status_code=status.HTTP_201_CREATED)
async def upload_timecard_xlsx(
    file: UploadFile = File(...),
    year: int = Form(...),
    month: int = Form(...),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload e processamento de arquivo XLSX de cartão ponto
    
    - **file**: Arquivo XLSX com dados de cartão ponto
    - **year**: Ano do período (ex: 2025)
    - **month**: Mês do período (1-12)
    - **start_date**: Data início do período (formato: YYYY-MM-DD)
    - **end_date**: Data fim do período (formato: YYYY-MM-DD)
    """
    # Validar extensão do arquivo
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo deve ser no formato XLSX ou XLS"
        )
    
    # Validar mês
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mês deve estar entre 1 e 12"
        )
    
    # Validar datas
    if start_date:
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date deve estar no formato YYYY-MM-DD"
            )
    
    if end_date:
        try:
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date deve estar no formato YYYY-MM-DD"
            )
    
    # Criar diretório de uploads se não existir
    upload_dir = "uploads/timecard"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Salvar arquivo temporariamente
    file_path = os.path.join(upload_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Arquivo salvo em: {file_path}")
        
        # Processar arquivo
        processor = TimecardXLSXProcessor(db=db, user_id=current_user.id)
        result = processor.process_xlsx_file(
            file_path=file_path,
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Erro ao processar arquivo')
            )
        
        logger.info(f"Processamento concluído: {result['processed_rows']} linhas processadas")
        
        return {
            "success": True,
            "message": "Arquivo processado com sucesso",
            "period_id": result['period_id'],
            "period_name": result['period_name'],
            "total_rows": result['total_rows'],
            "processed_rows": result['processed_rows'],
            "error_rows": result['error_rows'],
            "warnings": result.get('warnings', []),
            "errors": result.get('errors', []),
            "processing_time": float(result.get('processing_time', 0))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar upload de cartão ponto: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )
    finally:
        # Limpar arquivo temporário
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")


@router.get("/periods", response_model=List[TimecardPeriodResponse])
async def get_timecard_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Lista todos os períodos de cartão ponto"""
    periods = db.query(TimecardPeriod).order_by(
        TimecardPeriod.year.desc(),
        TimecardPeriod.month.desc()
    ).offset(skip).limit(limit).all()
    
    # Adicionar contagem de funcionários e totais detalhados
    result = []
    for period in periods:
        employee_count = db.query(TimecardData).filter(
            TimecardData.period_id == period.id
        ).count()
        
        # Calcular totais detalhados por tipo de hora
        totals = db.query(
            func.sum(TimecardData.overtime_50).label('overtime_50'),
            func.sum(TimecardData.overtime_100).label('overtime_100'),
            func.sum(TimecardData.night_overtime_50).label('night_overtime_50'),
            func.sum(TimecardData.night_overtime_100).label('night_overtime_100'),
            func.sum(TimecardData.night_hours).label('night_hours')
        ).filter(
            TimecardData.period_id == period.id
        ).first()
        
        # Calcular totais agregados
        ot50 = totals.overtime_50 or Decimal('0')
        ot100 = totals.overtime_100 or Decimal('0')
        not50 = totals.night_overtime_50 or Decimal('0')
        not100 = totals.night_overtime_100 or Decimal('0')
        nh = totals.night_hours or Decimal('0')
        
        period_dict = {
            'id': period.id,
            'year': period.year,
            'month': period.month,
            'period_name': period.period_name,
            'start_date': period.start_date,
            'end_date': period.end_date,
            'description': period.description,
            'is_active': period.is_active,
            'created_at': period.created_at,
            'employee_count': employee_count,
            'overtime_50': ot50,
            'overtime_100': ot100,
            'night_overtime_50': not50,
            'night_overtime_100': not100,
            'night_hours': nh,
            'total_overtime': ot50 + ot100,
            'total_night_hours': not50 + not100 + nh
        }
        
        result.append(TimecardPeriodResponse(**period_dict))
    
    return result


@router.get("/periods/{period_id}", response_model=TimecardPeriodDetail)
async def get_timecard_period_detail(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de um período específico"""
    period = db.query(TimecardPeriod).filter(TimecardPeriod.id == period_id).first()
    
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Período não encontrado"
        )
    
    # Buscar dados de cartão ponto
    timecard_data = db.query(TimecardData).filter(
        TimecardData.period_id == period_id
    ).order_by(TimecardData.employee_name).all()
    
    # Buscar logs de processamento
    processing_logs = db.query(TimecardProcessingLog).filter(
        TimecardProcessingLog.period_id == period_id
    ).order_by(TimecardProcessingLog.created_at.desc()).all()
    
    # Calcular estatísticas
    employee_count = len(timecard_data)
    total_overtime = sum((d.get_total_overtime() for d in timecard_data), Decimal('0'))
    total_night = sum((d.get_total_night_hours() for d in timecard_data), Decimal('0'))
    
    return {
        'id': period.id,
        'year': period.year,
        'month': period.month,
        'period_name': period.period_name,
        'start_date': period.start_date,
        'end_date': period.end_date,
        'description': period.description,
        'is_active': period.is_active,
        'created_at': period.created_at,
        'employee_count': employee_count,
        'total_overtime': total_overtime,
        'total_night_hours': total_night,
        'timecard_data': timecard_data,
        'processing_logs': processing_logs
    }


@router.delete("/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timecard_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta um período de cartão ponto (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem deletar períodos"
        )
    
    period = db.query(TimecardPeriod).filter(TimecardPeriod.id == period_id).first()
    
    if not period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Período não encontrado"
        )
    
    try:
        db.delete(period)
        db.commit()
        logger.info(f"Período de cartão ponto deletado: {period.period_name} (ID: {period_id})")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao deletar período: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar período: {str(e)}"
        )


@router.get("/stats", response_model=TimecardStats)
async def get_timecard_stats(
    period_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtém estatísticas de cartão ponto
    
    Pode filtrar por período específico ou por ano/mês
    """
    query = db.query(TimecardData)
    
    if period_id:
        query = query.filter(TimecardData.period_id == period_id)
    elif year and month:
        period = db.query(TimecardPeriod).filter(
            TimecardPeriod.year == year,
            TimecardPeriod.month == month
        ).first()
        if period:
            query = query.filter(TimecardData.period_id == period.id)
        else:
            # Se não encontrou período, retornar stats zerados
            return TimecardStats(
                total_employees=0,
                overtime_50=Decimal('0'),
                overtime_100=Decimal('0'),
                night_overtime_50=Decimal('0'),
                night_overtime_100=Decimal('0'),
                night_hours=Decimal('0'),
                intrajornada_hours=Decimal('0'),
                dsr_debit_hours=Decimal('0'),
                total_overtime_hours=Decimal('0'),
                total_night_hours=Decimal('0'),
                employees_with_overtime=0,
                employees_with_night_hours=0,
                employees_with_intrajornada=0,
                employees_with_dsr_debit=0,
                average_overtime=Decimal('0'),
                average_night_hours=Decimal('0'),
                average_intrajornada=Decimal('0'),
                average_dsr_debit=Decimal('0'),
                by_company={}
            )
    
    timecard_data = query.all()
    
    if not timecard_data:
        return TimecardStats(
            total_employees=0,
            overtime_50=Decimal('0'),
            overtime_100=Decimal('0'),
            night_overtime_50=Decimal('0'),
            night_overtime_100=Decimal('0'),
            night_hours=Decimal('0'),
            intrajornada_hours=Decimal('0'),
            dsr_debit_hours=Decimal('0'),
            total_overtime_hours=Decimal('0'),
            total_night_hours=Decimal('0'),
            employees_with_overtime=0,
            employees_with_night_hours=0,
            employees_with_intrajornada=0,
            employees_with_dsr_debit=0,
            average_overtime=Decimal('0'),
            average_night_hours=Decimal('0'),
            average_intrajornada=Decimal('0'),
            average_dsr_debit=Decimal('0'),
            by_company={}
        )
    
    # Calcular estatísticas detalhadas por tipo de hora
    total_employees = len(timecard_data)
    
    # Somar cada tipo de hora separadamente
    sum_overtime_50 = sum((d.overtime_50 or Decimal('0') for d in timecard_data), Decimal('0'))
    sum_overtime_100 = sum((d.overtime_100 or Decimal('0') for d in timecard_data), Decimal('0'))
    sum_night_overtime_50 = sum((d.night_overtime_50 or Decimal('0') for d in timecard_data), Decimal('0'))
    sum_night_overtime_100 = sum((d.night_overtime_100 or Decimal('0') for d in timecard_data), Decimal('0'))
    sum_night_hours = sum((d.night_hours or Decimal('0') for d in timecard_data), Decimal('0'))
    sum_intrajornada = sum((d.absences or Decimal('0') for d in timecard_data), Decimal('0'))
    sum_dsr_debit = sum((d.dsr_debit or Decimal('0') for d in timecard_data), Decimal('0'))
    
    # Totais agregados
    total_overtime = sum_overtime_50 + sum_overtime_100
    total_night = sum_night_overtime_50 + sum_night_overtime_100 + sum_night_hours
    
    employees_with_overtime = sum(1 for d in timecard_data if d.get_total_overtime() > 0)
    employees_with_night = sum(1 for d in timecard_data if d.get_total_night_hours() > 0)
    employees_with_intrajornada = sum(1 for d in timecard_data if (d.absences or Decimal('0')) > 0)
    employees_with_dsr_debit = sum(1 for d in timecard_data if (d.dsr_debit or Decimal('0')) > 0)
    
    avg_overtime = total_overtime / total_employees if total_employees > 0 else Decimal('0')
    avg_night = total_night / total_employees if total_employees > 0 else Decimal('0')
    avg_intrajornada = sum_intrajornada / total_employees if total_employees > 0 else Decimal('0')
    avg_dsr_debit = sum_dsr_debit / total_employees if total_employees > 0 else Decimal('0')
    
    # Estatísticas por empresa
    by_company = {}
    for company in ['0059', '0060']:
        company_data = [d for d in timecard_data if d.company == company]
        if company_data:
            by_company[company] = {
                'employees': len(company_data),
                'total_overtime': float(sum((d.get_total_overtime() for d in company_data), Decimal('0'))),
                'total_night_hours': float(sum((d.get_total_night_hours() for d in company_data), Decimal('0'))),
                'total_intrajornada': float(sum((d.absences or Decimal('0') for d in company_data), Decimal('0'))),
                'total_dsr_debit': float(sum((d.dsr_debit or Decimal('0') for d in company_data), Decimal('0'))),
                'average_overtime': float(sum((d.get_total_overtime() for d in company_data), Decimal('0')) / len(company_data)),
                'average_night_hours': float(sum((d.get_total_night_hours() for d in company_data), Decimal('0')) / len(company_data)),
                'average_intrajornada': float(sum((d.absences or Decimal('0') for d in company_data), Decimal('0')) / len(company_data)),
                'average_dsr_debit': float(sum((d.dsr_debit or Decimal('0') for d in company_data), Decimal('0')) / len(company_data)),
            }
    
    return TimecardStats(
        total_employees=total_employees,
        overtime_50=sum_overtime_50,
        overtime_100=sum_overtime_100,
        night_overtime_50=sum_night_overtime_50,
        night_overtime_100=sum_night_overtime_100,
        night_hours=sum_night_hours,
        intrajornada_hours=sum_intrajornada,
        dsr_debit_hours=sum_dsr_debit,
        total_overtime_hours=total_overtime,
        total_night_hours=total_night,
        employees_with_overtime=employees_with_overtime,
        employees_with_night_hours=employees_with_night,
        employees_with_intrajornada=employees_with_intrajornada,
        employees_with_dsr_debit=employees_with_dsr_debit,
        average_overtime=avg_overtime,
        average_night_hours=avg_night,
        average_intrajornada=avg_intrajornada,
        average_dsr_debit=avg_dsr_debit,
        by_company=by_company
    )
