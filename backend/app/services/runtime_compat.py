"""Compatibilidade de runtime para o servidor modular.

Centraliza a sessão de banco, o cache de employees e helpers de persistência
usados pelos routers modularizados.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.models.base import SessionLocal as _SessionLocal
from app.models.base import engine as db_engine
from app.models.employee import Employee
from app.models.user import User
from app.utils.parsers import generate_name_id

SessionLocal = _SessionLocal

employees_cache = {
    'data': None,
    'last_update': 0.0,
    'ttl': 180,
}


def check_database_health() -> Dict[str, Any]:
    """Verifica se o banco está acessível."""
    try:
        if not db_engine:
            return {
                'status': 'error',
                'message': 'Engine do banco não inicializada',
                'connected': False,
                'type': 'None',
                'version': 'N/A',
            }

        with db_engine.connect() as connection:
            connection.execute(text('SELECT 1'))
            result = connection.execute(text('SELECT version()'))
            version = result.fetchone()[0]

        return {
            'status': 'online',
            'message': 'Banco de dados PostgreSQL está online',
            'connected': True,
            'type': 'PostgreSQL',
            'version': version.split(',')[0] if ',' in version else version,
        }
    except Exception as exc:
        return {
            'status': 'offline',
            'message': f'Banco de dados offline: {exc}',
            'connected': False,
            'type': 'PostgreSQL',
            'version': 'N/A',
        }


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except Exception:
        return None


def load_employees_data(include_inactive: bool = False) -> Dict[str, Any]:
    """Carrega colaboradores do banco com cache em memória."""
    current_time = time.time()
    cache_age = current_time - employees_cache['last_update']

    if not include_inactive and employees_cache['data'] is not None and cache_age < employees_cache['ttl']:
        return employees_cache['data']

    if SessionLocal:
        db = None
        try:
            db = SessionLocal()
            query = db.query(Employee)
            if not include_inactive:
                query = query.filter(Employee.is_active == True)

            employees = query.all()
            employees_data = []
            for emp in employees:
                employees_data.append({
                    'id': emp.id,
                    'unique_id': emp.unique_id,
                    'absolute_id': emp.absolute_id or '',
                    'company_code': emp.company_code or '',
                    'registration_number': emp.registration_number or '',
                    'full_name': emp.name,
                    'cpf': emp.cpf or '',
                    'phone_number': emp.phone or '',
                    'email': emp.email or '',
                    'department': emp.department or '',
                    'position': emp.position or '',
                    'birth_date': emp.birth_date.isoformat() if emp.birth_date else '',
                    'sex': emp.sex or '',
                    'marital_status': emp.marital_status or '',
                    'admission_date': emp.admission_date.isoformat() if emp.admission_date else '',
                    'contract_type': emp.contract_type or '',
                    'employment_status': emp.employment_status or 'Ativo',
                    'termination_date': emp.termination_date.isoformat() if emp.termination_date else '',
                    'leave_start_date': emp.leave_start_date.isoformat() if emp.leave_start_date else '',
                    'leave_end_date': emp.leave_end_date.isoformat() if emp.leave_end_date else '',
                    'status_reason': emp.status_reason or '',
                    'is_active': emp.is_active,
                    'company_id': emp.company_id,
                    'work_location_id': emp.work_location_id,
                })

            result = {'employees': employees_data, 'users': []}
            if not include_inactive:
                employees_cache['data'] = result
                employees_cache['last_update'] = current_time
            return result
        except Exception:
            pass
        finally:
            if db:
                db.close()

    json_file = 'employees.json'
    if os.path.exists(json_file):
        with open(json_file, 'r', encoding='utf-8') as file_obj:
            return json.load(file_obj)
    return {'employees': [], 'users': []}


def invalidate_employees_cache() -> None:
    employees_cache['data'] = None
    employees_cache['last_update'] = 0.0


def save_employee_to_db(employee_data: Dict[str, Any], created_by_user_id: int = 3) -> bool:
    """Cria ou atualiza colaborador no banco de dados."""
    if not SessionLocal:
        return False

    db = None
    try:
        db = SessionLocal()

        user_exists = db.query(User).filter(User.id == created_by_user_id).first()
        if not user_exists:
            first_user = db.query(User).first()
            if first_user:
                created_by_user_id = first_user.id
            else:
                return False

        reg_raw = str(employee_data.get('registration_number') or '').strip()
        reg_digits = re.sub(r'\D', '', reg_raw)
        if reg_digits:
            employee_data['registration_number'] = reg_digits.zfill(5)

        status_reason_raw = str(employee_data.get('status_reason') or '').strip().lower()
        termination_date_raw = str(employee_data.get('termination_date') or '').strip()
        inferred_inactive = bool(termination_date_raw) or ('demit' in status_reason_raw) or ('deslig' in status_reason_raw)

        existing = db.query(Employee).filter(Employee.unique_id == employee_data.get('unique_id')).first()

        if existing:
            existing.name = employee_data.get('full_name', existing.name)
            existing.phone = employee_data.get('phone_number', existing.phone)
            existing.email = employee_data.get('email', existing.email)
            existing.department = employee_data.get('department', existing.department)
            existing.position = employee_data.get('position', existing.position)
            existing.is_active = employee_data.get('is_active', existing.is_active)
            if inferred_inactive:
                existing.is_active = False
            existing.unique_id = employee_data.get('unique_id', existing.unique_id)
            existing.absolute_id = employee_data.get('absolute_id', existing.absolute_id)
            existing.company_code = employee_data.get('company_code', existing.company_code)
            existing.registration_number = employee_data.get('registration_number', existing.registration_number)
            if employee_data.get('cpf'):
                existing.cpf = employee_data.get('cpf')

            existing.birth_date = _parse_date(employee_data.get('birth_date')) or existing.birth_date
            if employee_data.get('sex'):
                existing.sex = employee_data['sex']
            if employee_data.get('marital_status'):
                existing.marital_status = employee_data['marital_status']
            existing.admission_date = _parse_date(employee_data.get('admission_date')) or existing.admission_date
            if employee_data.get('contract_type'):
                existing.contract_type = employee_data['contract_type']
            if employee_data.get('status_reason'):
                existing.status_reason = employee_data['status_reason']
            existing.termination_date = _parse_date(employee_data.get('termination_date'))
            if 'company_id' in employee_data:
                existing.company_id = employee_data['company_id']
            if 'work_location_id' in employee_data:
                existing.work_location_id = employee_data['work_location_id']
            existing.name_id = generate_name_id(existing.company_code, existing.registration_number, existing.name)
        else:
            new_employee = Employee(
                unique_id=employee_data.get('unique_id'),
                absolute_id=employee_data.get('absolute_id'),
                company_code=employee_data.get('company_code'),
                registration_number=employee_data.get('registration_number'),
                name=employee_data.get('full_name'),
                cpf=employee_data.get('cpf') or employee_data.get('unique_id', '000.000.000-00'),
                phone=employee_data.get('phone_number'),
                email=employee_data.get('email'),
                department=employee_data.get('department'),
                position=employee_data.get('position'),
                birth_date=_parse_date(employee_data.get('birth_date')),
                sex=employee_data.get('sex'),
                marital_status=employee_data.get('marital_status'),
                admission_date=_parse_date(employee_data.get('admission_date')),
                contract_type=employee_data.get('contract_type'),
                employment_status=employee_data.get('employment_status', 'Ativo'),
                termination_date=_parse_date(employee_data.get('termination_date')),
                leave_start_date=_parse_date(employee_data.get('leave_start_date')),
                leave_end_date=_parse_date(employee_data.get('leave_end_date')),
                status_reason=employee_data.get('status_reason'),
                is_active=employee_data.get('is_active', not inferred_inactive),
                company_id=employee_data.get('company_id'),
                work_location_id=employee_data.get('work_location_id'),
            )
            if inferred_inactive:
                new_employee.is_active = False
            new_employee.name_id = generate_name_id(new_employee.company_code, new_employee.registration_number, new_employee.name)
            db.add(new_employee)

        db.commit()
        invalidate_employees_cache()
        return True
    except Exception:
        if db:
            db.rollback()
        return False
    finally:
        if db:
            db.close()
