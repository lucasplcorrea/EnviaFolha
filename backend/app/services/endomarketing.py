"""
Serviço de Endomarketing - Indicadores de RH
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, and_, or_

from app.models.employee import Employee

logger = logging.getLogger(__name__)


class EndomarketingService:
    """Serviço para gerenciar indicadores de endomarketing e RH."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_birthday_employees(self, period: str = 'month') -> Dict[str, Any]:
        """
        Retorna colaboradores aniversariantes.
        
        Args:
            period: 'week' ou 'month'
            
        Returns:
            Dict com lista de aniversariantes e contagem
        """
        logger.info(f"Buscando aniversariantes do período: {period}")
        
        today = datetime.now()
        current_month = today.month
        
        if period == 'week':
            # Próximos 7 dias
            start_day = today.day
            end_date = today + timedelta(days=7)
            
            # Buscar aniversariantes na semana
            if end_date.month == current_month:
                # Mesma semana no mesmo mês
                employees = self.db.query(Employee).filter(
                    Employee.is_active == True,
                    Employee.birth_date.isnot(None),
                    extract('month', Employee.birth_date) == current_month,
                    extract('day', Employee.birth_date) >= start_day,
                    extract('day', Employee.birth_date) <= end_date.day
                ).order_by(extract('day', Employee.birth_date)).all()
            else:
                # Semana atravessa virada de mês
                employees = self.db.query(Employee).filter(
                    Employee.is_active == True,
                    Employee.birth_date.isnot(None),
                    or_(
                        and_(
                            extract('month', Employee.birth_date) == current_month,
                            extract('day', Employee.birth_date) >= start_day
                        ),
                        and_(
                            extract('month', Employee.birth_date) == end_date.month,
                            extract('day', Employee.birth_date) <= end_date.day
                        )
                    )
                ).order_by(
                    extract('month', Employee.birth_date),
                    extract('day', Employee.birth_date)
                ).all()
        else:
            # Mês inteiro
            employees = self.db.query(Employee).filter(
                Employee.is_active == True,
                Employee.birth_date.isnot(None),
                extract('month', Employee.birth_date) == current_month
            ).order_by(extract('day', Employee.birth_date)).all()
        
        # Formatar resposta
        birthdays = []
        for emp in employees:
            if emp.birth_date:
                # Calcular idade
                age = today.year - emp.birth_date.year
                if today.month < emp.birth_date.month or (
                    today.month == emp.birth_date.month and today.day < emp.birth_date.day
                ):
                    age -= 1
                
                # Calcular dias até aniversário
                next_birthday = emp.birth_date.replace(year=today.year)
                if next_birthday < today.date():
                    next_birthday = emp.birth_date.replace(year=today.year + 1)
                
                days_until = (next_birthday - today.date()).days
                
                birthdays.append({
                    'id': emp.id,
                    'unique_id': emp.unique_id,
                    'name': emp.name,
                    'department': emp.department,
                    'position': emp.position,
                    'birth_date': emp.birth_date.strftime('%d/%m/%Y'),
                    'birth_day': emp.birth_date.day,
                    'birth_month': emp.birth_date.month,
                    'age': age + 1,  # Idade que vai completar
                    'days_until': days_until,
                    'is_today': days_until == 0
                })
        
        return {
            'period': period,
            'count': len(birthdays),
            'employees': birthdays
        }
    
    def get_work_anniversary_employees(self, period: str = 'month') -> Dict[str, Any]:
        """
        Retorna colaboradores com aniversário de tempo de empresa.
        Considera apenas colaboradores com 1 ano ou mais.
        
        Args:
            period: 'week' ou 'month'
            
        Returns:
            Dict com lista de aniversariantes de empresa e contagem
        """
        logger.info(f"Buscando aniversariantes de empresa do período: {period}")
        
        today = datetime.now()
        current_month = today.month
        
        if period == 'week':
            start_day = today.day
            end_date = today + timedelta(days=7)
            
            if end_date.month == current_month:
                employees = self.db.query(Employee).filter(
                    Employee.is_active == True,
                    Employee.admission_date.isnot(None),
                    extract('month', Employee.admission_date) == current_month,
                    extract('day', Employee.admission_date) >= start_day,
                    extract('day', Employee.admission_date) <= end_date.day
                ).order_by(extract('day', Employee.admission_date)).all()
            else:
                employees = self.db.query(Employee).filter(
                    Employee.is_active == True,
                    Employee.admission_date.isnot(None),
                    or_(
                        and_(
                            extract('month', Employee.admission_date) == current_month,
                            extract('day', Employee.admission_date) >= start_day
                        ),
                        and_(
                            extract('month', Employee.admission_date) == end_date.month,
                            extract('day', Employee.admission_date) <= end_date.day
                        )
                    )
                ).order_by(
                    extract('month', Employee.admission_date),
                    extract('day', Employee.admission_date)
                ).all()
        else:
            employees = self.db.query(Employee).filter(
                Employee.is_active == True,
                Employee.admission_date.isnot(None),
                extract('month', Employee.admission_date) == current_month
            ).order_by(extract('day', Employee.admission_date)).all()
        
        # Filtrar apenas quem completa 1 ano ou mais
        anniversaries = []
        for emp in employees:
            if emp.admission_date:
                years = today.year - emp.admission_date.year
                if today.month < emp.admission_date.month or (
                    today.month == emp.admission_date.month and today.day < emp.admission_date.day
                ):
                    years -= 1
                
                # Próximo aniversário de empresa
                years_completing = years + 1
                
                # Apenas se for completar 1 ano ou mais
                if years_completing >= 1:
                    next_anniversary = emp.admission_date.replace(year=today.year)
                    if next_anniversary < today.date():
                        next_anniversary = emp.admission_date.replace(year=today.year + 1)
                    
                    days_until = (next_anniversary - today.date()).days
                    
                    anniversaries.append({
                        'id': emp.id,
                        'unique_id': emp.unique_id,
                        'name': emp.name,
                        'department': emp.department,
                        'position': emp.position,
                        'admission_date': emp.admission_date.strftime('%d/%m/%Y'),
                        'admission_day': emp.admission_date.day,
                        'admission_month': emp.admission_date.month,
                        'years_completing': years_completing,
                        'days_until': days_until,
                        'is_today': days_until == 0
                    })
        
        return {
            'period': period,
            'count': len(anniversaries),
            'employees': anniversaries
        }
    
    def get_probation_employees(self, phase: int) -> Dict[str, Any]:
        """
        Retorna colaboradores em período de experiência.
        
        Args:
            phase: 1 (45 dias) ou 2 (90 dias)
            
        Returns:
            Dict com lista de colaboradores e contagem
        """
        logger.info(f"Buscando colaboradores em fase {phase} de experiência")
        
        today = datetime.now()
        
        # Definir períodos
        if phase == 1:
            # Primeira fase: entre 30 e 50 dias (janela ao redor de 45 dias)
            days_target = 45
            days_before = 15  # Alertar 15 dias antes
            days_after = 5    # Mostrar até 5 dias depois
        else:  # phase == 2
            # Segunda fase: entre 75 e 95 dias (janela ao redor de 90 dias)
            days_target = 90
            days_before = 15
            days_after = 5
        
        min_date = today - timedelta(days=days_target + days_after)
        max_date = today - timedelta(days=days_target - days_before)
        
        employees = self.db.query(Employee).filter(
            Employee.is_active == True,
            Employee.admission_date.isnot(None),
            Employee.admission_date >= min_date,
            Employee.admission_date <= max_date
        ).order_by(Employee.admission_date).all()
        
        probation_list = []
        for emp in employees:
            if emp.admission_date:
                days_working = (today.date() - emp.admission_date).days
                days_until_phase = days_target - days_working
                phase_date = emp.admission_date + timedelta(days=days_target)
                
                probation_list.append({
                    'id': emp.id,
                    'unique_id': emp.unique_id,
                    'name': emp.name,
                    'department': emp.department,
                    'position': emp.position,
                    'admission_date': emp.admission_date.strftime('%d/%m/%Y'),
                    'days_working': days_working,
                    'phase_date': phase_date.strftime('%d/%m/%Y'),
                    'days_until_phase': days_until_phase,
                    'is_today': days_until_phase == 0,
                    'is_overdue': days_until_phase < 0
                })
        
        return {
            'phase': phase,
            'days_target': days_target,
            'count': len(probation_list),
            'employees': probation_list
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo dos indicadores para o dashboard.
        
        Returns:
            Dict com contagens resumidas de todos os indicadores
        """
        logger.info("Gerando resumo de endomarketing para dashboard")
        
        # Aniversariantes da semana
        birthdays_week = self.get_birthday_employees('week')
        
        # Aniversariantes de empresa da semana
        work_anniversaries_week = self.get_work_anniversary_employees('week')
        
        # Experiência fase 1 (próximos a completar 45 dias)
        probation_phase1 = self.get_probation_employees(1)
        
        # Experiência fase 2 (próximos a completar 90 dias)
        probation_phase2 = self.get_probation_employees(2)
        
        return {
            'birthdays': {
                'week': birthdays_week['count'],
                'today': sum(1 for e in birthdays_week['employees'] if e['is_today'])
            },
            'work_anniversaries': {
                'week': work_anniversaries_week['count'],
                'today': sum(1 for e in work_anniversaries_week['employees'] if e['is_today'])
            },
            'probation': {
                'phase1': probation_phase1['count'],
                'phase2': probation_phase2['count']
            }
        }
