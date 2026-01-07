"""Service para cálculo e cache de indicadores de RH"""
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_, case
from app.models.employee import Employee
from app.models.hr_indicators import HRIndicatorSnapshot


class HRIndicatorsService:
    """
    Serviço otimizado para indicadores de RH com cache inteligente.
    
    Estratégia de otimização:
    1. Cache em tabela de snapshots (reduz queries complexas)
    2. TTL configurável por tipo de indicador
    3. Queries otimizadas com aggregations no PostgreSQL
    4. Invalidação seletiva de cache
    """
    
    # TTL para diferentes tipos de indicadores (em horas)
    CACHE_TTL = {
        'headcount': 1,  # Atualiza a cada 1 hora
        'turnover': 24,  # Atualiza diariamente
        'demographics': 24,  # Atualiza diariamente
        'tenure': 24,  # Atualiza diariamente
        'leaves': 6,  # Atualiza a cada 6 horas (mais dinâmico)
        'trends': 24,  # Atualiza diariamente
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_cached_indicator(
        self, 
        indicator_type: str,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Recupera indicador do cache se ainda válido"""
        ttl_hours = self.CACHE_TTL.get(indicator_type, 24)
        cutoff_time = datetime.now() - timedelta(hours=ttl_hours)
        
        query = self.db.query(HRIndicatorSnapshot).filter(
            HRIndicatorSnapshot.indicator_type == indicator_type,
            HRIndicatorSnapshot.is_valid == 1,
            HRIndicatorSnapshot.created_at >= cutoff_time
        )
        
        # Filtro adicional por período se fornecido
        if period_start:
            query = query.filter(HRIndicatorSnapshot.period_start == period_start)
        if period_end:
            query = query.filter(HRIndicatorSnapshot.period_end == period_end)
        
        snapshot = query.order_by(HRIndicatorSnapshot.created_at.desc()).first()
        
        if snapshot:
            return {
                'metrics': snapshot.metrics,
                'cached': True,
                'cached_at': snapshot.created_at.isoformat(),
                'total_records': snapshot.total_records
            }
        
        return None
    
    def _save_to_cache(
        self,
        indicator_type: str,
        metrics: Dict[str, Any],
        total_records: int,
        calculation_time_ms: int,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ):
        """Salva indicador calculado no cache"""
        # Converter Decimals para float para serialização JSON
        import json
        from decimal import Decimal
        
        def decimal_to_float(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: decimal_to_float(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [decimal_to_float(item) for item in obj]
            return obj
        
        metrics_clean = decimal_to_float(metrics)
        
        snapshot = HRIndicatorSnapshot(
            indicator_type=indicator_type,
            calculation_date=date.today(),
            period_start=period_start,
            period_end=period_end,
            metrics=metrics_clean,
            total_records=total_records,
            calculation_time_ms=calculation_time_ms,
            is_valid=1
        )
        
        self.db.add(snapshot)
        self.db.commit()
    
    def invalidate_cache(self, indicator_type: Optional[str] = None):
        """Invalida cache de indicadores (todos ou de um tipo específico)"""
        query = self.db.query(HRIndicatorSnapshot)
        
        if indicator_type:
            query = query.filter(HRIndicatorSnapshot.indicator_type == indicator_type)
        
        query.update({'is_valid': 0})
        self.db.commit()
    
    # ========== HEADCOUNT ==========
    
    def get_headcount_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Métricas de efetivo (headcount)"""
        
        # Tentar buscar do cache
        if use_cache:
            cached = self._get_cached_indicator('headcount')
            if cached:
                return cached
        
        # Calcular métricas
        start_time = time.time()
        
        # Total de colaboradores ativos
        total_active = self.db.query(func.count(Employee.id)).filter(
            Employee.is_active == True
        ).scalar()
        
        # Por departamento
        by_department = self.db.query(
            Employee.department,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.department.isnot(None)
        ).group_by(Employee.department).order_by(Employee.department).all()
        
        # Por setor
        by_sector = self.db.query(
            Employee.sector,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.sector.isnot(None)
        ).group_by(Employee.sector).order_by(Employee.sector).all()
        
        # Por empresa
        by_company = self.db.query(
            Employee.company_code,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.company_code.isnot(None)
        ).group_by(Employee.company_code).order_by(Employee.company_code).all()
        
        # Por tipo de contrato
        by_contract_type = self.db.query(
            Employee.contract_type,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.contract_type.isnot(None)
        ).group_by(Employee.contract_type).order_by(Employee.contract_type).all()
        
        # Por status de emprego
        by_employment_status = self.db.query(
            Employee.employment_status,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.employment_status.isnot(None)
        ).group_by(Employee.employment_status).order_by(Employee.employment_status).all()
        
        metrics = {
            'total_active': int(total_active),
            'by_department': [{'department': d, 'count': int(c)} for d, c in by_department],
            'by_sector': [{'sector': s, 'count': int(c)} for s, c in by_sector],
            'by_company': [{'company_code': cc, 'count': int(c)} for cc, c in by_company],
            'by_contract_type': [{'contract_type': ct, 'count': int(c)} for ct, c in by_contract_type],
            'by_employment_status': [{'employment_status': es, 'count': int(c)} for es, c in by_employment_status],
        }
        
        calculation_time = int((time.time() - start_time) * 1000)
        
        # Salvar no cache
        self._save_to_cache(
            indicator_type='headcount',
            metrics=metrics,
            total_records=total_active,
            calculation_time_ms=calculation_time
        )
        
        return {
            'metrics': metrics,
            'cached': False,
            'calculation_time_ms': calculation_time,
            'total_records': total_active
        }
    
    # ========== TURNOVER ==========
    
    def get_turnover_metrics(
        self, 
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Métricas de turnover (rotatividade)"""
        
        # Período padrão: último mês
        if not period_end:
            period_end = date.today()
        if not period_start:
            period_start = period_end - timedelta(days=30)
        
        # Tentar buscar do cache
        if use_cache:
            cached = self._get_cached_indicator('turnover', period_start, period_end)
            if cached:
                return cached
        
        start_time = time.time()
        
        # Efetivo médio no período
        total_active_start = self.db.query(func.count(Employee.id)).filter(
            or_(
                Employee.admission_date <= period_start,
                Employee.admission_date.is_(None)
            ),
            or_(
                Employee.termination_date.is_(None),
                Employee.termination_date >= period_start
            )
        ).scalar()
        
        total_active_end = self.db.query(func.count(Employee.id)).filter(
            or_(
                Employee.admission_date <= period_end,
                Employee.admission_date.is_(None)
            ),
            or_(
                Employee.termination_date.is_(None),
                Employee.termination_date >= period_end
            )
        ).scalar()
        
        avg_headcount = (total_active_start + total_active_end) / 2 if total_active_start or total_active_end else 1
        
        # Admissões no período
        admissions = self.db.query(func.count(Employee.id)).filter(
            Employee.admission_date.between(period_start, period_end)
        ).scalar()
        
        # Desligamentos no período
        terminations = self.db.query(func.count(Employee.id)).filter(
            Employee.termination_date.between(period_start, period_end)
        ).scalar()
        
        # Motivos de desligamento
        termination_reasons = self.db.query(
            Employee.status_reason,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.termination_date.between(period_start, period_end),
            Employee.status_reason.isnot(None)
        ).group_by(Employee.status_reason).all()
        
        # Cálculo da taxa de turnover
        # Fórmula: ((admissões + demissões) / 2) / efetivo médio * 100
        turnover_rate = ((admissions + terminations) / 2) / avg_headcount * 100 if avg_headcount > 0 else 0
        admission_rate = (admissions / avg_headcount * 100) if avg_headcount > 0 else 0
        termination_rate = (terminations / avg_headcount * 100) if avg_headcount > 0 else 0
        
        # Turnover por departamento
        turnover_by_dept = self.db.query(
            Employee.department,
            func.count(Employee.id).label('terminations')
        ).filter(
            Employee.termination_date.between(period_start, period_end),
            Employee.department.isnot(None)
        ).group_by(Employee.department).all()
        
        metrics = {
            'period': {
                'start': period_start.isoformat(),
                'end': period_end.isoformat()
            },
            'headcount': {
                'start': int(total_active_start),
                'end': int(total_active_end),
                'average': round(avg_headcount, 2)
            },
            'movements': {
                'admissions': int(admissions),
                'terminations': int(terminations)
            },
            'rates': {
                'turnover': round(turnover_rate, 2),
                'admission': round(admission_rate, 2),
                'termination': round(termination_rate, 2)
            },
            'termination_reasons': [{'reason': r, 'count': int(c)} for r, c in termination_reasons],
            'turnover_by_department': [{'department': d, 'terminations': int(t)} for d, t in turnover_by_dept]
        }
        
        calculation_time = int((time.time() - start_time) * 1000)
        
        self._save_to_cache(
            indicator_type='turnover',
            metrics=metrics,
            total_records=admissions + terminations,
            calculation_time_ms=calculation_time,
            period_start=period_start,
            period_end=period_end
        )
        
        return {
            'metrics': metrics,
            'cached': False,
            'calculation_time_ms': calculation_time,
            'total_records': admissions + terminations
        }
    
    # ========== DEMOGRAPHICS ==========
    
    def get_demographic_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Perfil demográfico dos colaboradores"""
        
        if use_cache:
            cached = self._get_cached_indicator('demographics')
            if cached:
                return cached
        
        start_time = time.time()
        
        # Distribuição por sexo
        by_sex = self.db.query(
            Employee.sex,
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.sex.isnot(None)
        ).group_by(Employee.sex).all()
        
        # Faixas etárias
        today = date.today()
        age_ranges = self.db.query(
            case(
                (func.extract('year', func.age(Employee.birth_date)) < 25, '18-24'),
                (func.extract('year', func.age(Employee.birth_date)) < 35, '25-34'),
                (func.extract('year', func.age(Employee.birth_date)) < 45, '35-44'),
                (func.extract('year', func.age(Employee.birth_date)) < 55, '45-54'),
                else_='55+'
            ).label('age_range'),
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.birth_date.isnot(None)
        ).group_by('age_range').all()
        
        # Idade média
        avg_age = self.db.query(
            func.avg(func.extract('year', func.age(Employee.birth_date)))
        ).filter(
            Employee.is_active == True,
            Employee.birth_date.isnot(None)
        ).scalar()
        
        metrics = {
            'by_sex': [{'sex': s or 'Não informado', 'count': c} for s, c in by_sex],
            'age_ranges': [{'range': r, 'count': c} for r, c in age_ranges],
            'average_age': int(round(float(avg_age))) if avg_age else None
        }
        
        calculation_time = int((time.time() - start_time) * 1000)
        total_records = sum(c for _, c in by_sex)
        
        self._save_to_cache(
            indicator_type='demographics',
            metrics=metrics,
            total_records=total_records,
            calculation_time_ms=calculation_time
        )
        
        return {
            'metrics': metrics,
            'cached': False,
            'calculation_time_ms': calculation_time,
            'total_records': total_records
        }
    
    # ========== TEMPO DE CASA (TENURE) ==========
    
    def get_tenure_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Métricas de tempo de casa"""
        
        if use_cache:
            cached = self._get_cached_indicator('tenure')
            if cached:
                return cached
        
        start_time = time.time()
        today = date.today()
        
        # Tempo médio de casa (em dias, depois convertido para anos e meses)
        avg_tenure_days = self.db.query(
            func.avg(
                func.extract('day', func.age(
                    func.coalesce(Employee.termination_date, today),
                    Employee.admission_date
                ))
            )
        ).filter(
            Employee.is_active == True,
            Employee.admission_date.isnot(None)
        ).scalar()
        
        avg_tenure_years = (float(avg_tenure_days) / 365.25) if avg_tenure_days else 0
        avg_tenure_months = int(round(float(avg_tenure_days) / 30.44)) if avg_tenure_days else 0
        
        # Distribuição por tempo de casa
        tenure_ranges_query = self.db.query(
            case(
                (func.extract('year', func.age(func.coalesce(Employee.termination_date, today), Employee.admission_date)) < 1, '0-1 ano'),
                (func.extract('year', func.age(func.coalesce(Employee.termination_date, today), Employee.admission_date)) < 3, '1-3 anos'),
                (func.extract('year', func.age(func.coalesce(Employee.termination_date, today), Employee.admission_date)) < 5, '3-5 anos'),
                (func.extract('year', func.age(func.coalesce(Employee.termination_date, today), Employee.admission_date)) < 10, '5-10 anos'),
                else_='10+ anos'
            ).label('tenure_range'),
            func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.admission_date.isnot(None)
        ).group_by('tenure_range').all()
        
        # Ordenar faixas de tenure
        tenure_order = {'0-1 ano': 1, '1-3 anos': 2, '3-5 anos': 3, '5-10 anos': 4, '10+ anos': 5}
        tenure_ranges = sorted(tenure_ranges_query, key=lambda x: tenure_order.get(x[0], 99))
        
        # Tempo médio por departamento (ordenado alfabeticamente)
        avg_tenure_by_dept = self.db.query(
            Employee.department,
            func.avg(
                func.extract('day', func.age(
                    func.coalesce(Employee.termination_date, today),
                    Employee.admission_date
                )) / 365.25
            ).label('avg_years')
        ).filter(
            Employee.is_active == True,
            Employee.admission_date.isnot(None),
            Employee.department.isnot(None)
        ).group_by(Employee.department).order_by(Employee.department).all()
        
        metrics = {
            'average_tenure_years': int(round(avg_tenure_years)),
            'average_tenure_months': avg_tenure_months,
            'tenure_ranges': [{'range': r, 'count': int(c)} for r, c in tenure_ranges],
            'by_department': [{'department': d, 'avg_years': int(round(float(a) if a else 0))} for d, a in avg_tenure_by_dept]
        }
        
        calculation_time = int((time.time() - start_time) * 1000)
        total_records = sum(c for _, c in tenure_ranges)
        
        self._save_to_cache(
            indicator_type='tenure',
            metrics=metrics,
            total_records=total_records,
            calculation_time_ms=calculation_time
        )
        
        return {
            'metrics': metrics,
            'cached': False,
            'calculation_time_ms': calculation_time,
            'total_records': total_records
        }
    
    # ========== AFASTAMENTOS ==========
    
    def get_leave_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Métricas de afastamentos"""
        
        if use_cache:
            cached = self._get_cached_indicator('leaves')
            if cached:
                return cached
        
        start_time = time.time()
        today = date.today()
        
        # Colaboradores atualmente afastados
        currently_on_leave = self.db.query(func.count(Employee.id)).filter(
            Employee.is_active == True,
            Employee.leave_start_date <= today,
            Employee.leave_end_date >= today
        ).scalar()
        
        # Total de afastamentos (últimos 30 dias)
        thirty_days_ago = today - timedelta(days=30)
        recent_leaves = self.db.query(func.count(Employee.id)).filter(
            Employee.leave_start_date.between(thirty_days_ago, today)
        ).scalar()
        
        # Duração média de afastamentos (em dias)
        avg_leave_duration = self.db.query(
            func.avg(
                func.extract('day', func.age(Employee.leave_end_date, Employee.leave_start_date))
            )
        ).filter(
            Employee.leave_start_date.isnot(None),
            Employee.leave_end_date.isnot(None),
            Employee.leave_start_date >= thirty_days_ago
        ).scalar()
        
        # Taxa de absenteísmo (afastados / total ativo)
        total_active = self.db.query(func.count(Employee.id)).filter(
            Employee.is_active == True
        ).scalar()
        
        absenteeism_rate = (currently_on_leave / total_active * 100) if total_active > 0 else 0
        
        metrics = {
            'currently_on_leave': currently_on_leave,
            'recent_leaves_30d': recent_leaves,
            'average_duration_days': round(avg_leave_duration, 1) if avg_leave_duration else 0,
            'absenteeism_rate': round(absenteeism_rate, 2),
            'total_active_employees': total_active
        }
        
        calculation_time = int((time.time() - start_time) * 1000)
        
        self._save_to_cache(
            indicator_type='leaves',
            metrics=metrics,
            total_records=currently_on_leave + recent_leaves,
            calculation_time_ms=calculation_time
        )
        
        return {
            'metrics': metrics,
            'cached': False,
            'calculation_time_ms': calculation_time,
            'total_records': currently_on_leave + recent_leaves
        }
    
    # ========== OVERVIEW (COMBINADO) ==========
    
    def get_overview_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """Métricas de visão geral (combinação otimizada de vários indicadores)"""
        
        # Para overview, pegamos cache individual de cada tipo
        headcount = self.get_headcount_metrics(use_cache)
        turnover = self.get_turnover_metrics(use_cache=use_cache)
        tenure = self.get_tenure_metrics(use_cache)
        leaves = self.get_leave_metrics(use_cache)
        
        return {
            'headcount': headcount['metrics'],
            'turnover': turnover['metrics'],
            'tenure': tenure['metrics'],
            'leaves': leaves['metrics'],
            'cached': all([
                headcount.get('cached', False),
                turnover.get('cached', False),
                tenure.get('cached', False),
                leaves.get('cached', False)
            ])
        }
