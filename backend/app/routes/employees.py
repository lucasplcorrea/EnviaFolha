"""Modular route handlers for employee detail and history endpoints."""

import re
import urllib.parse
from datetime import date, datetime

from app.models.base import SessionLocal
from app.models.company import Company
from app.models.employee import Employee
from app.models.leave import LeaveRecord
from app.models.movement import MovementRecord
from app.models.payroll import PayrollData, PayrollPeriod
from app.models.timecard import TimecardData, TimecardPeriod
from app.routes.base import BaseRouter
from app.utils.parsers import generate_name_id, normalize_cpf
from app.services.runtime_compat import employees_cache, invalidate_employees_cache, save_employee_to_db


class EmployeesRouter(BaseRouter):
    """Router para endpoints de colaboradores no servidor HTTP legado."""

    def handle_get(self, path: str):
        if path == '/api/v1/employees/cache/status':
            self.handle_cache_status()
            return

        if path == '/api/v1/employees':
            self.handle_employees_list()
            return

        if not path.startswith('/api/v1/employees/'):
            self.send_error('Endpoint não encontrado', 404)
            return

        parts = path.split('/')
        if len(parts) < 5:
            self.send_error('Endpoint não encontrado', 404)
            return

        employee_id = parts[4]

        if len(parts) >= 6 and parts[5] == 'movements':
            self.handle_get_employee_movements(employee_id)
            return

        if len(parts) >= 6 and parts[5] == 'payroll':
            self.handle_get_employee_payroll(employee_id)
            return

        if len(parts) >= 6 and parts[5] == 'timecard':
            self.handle_get_employee_timecard(employee_id)
            return

        if len(parts) >= 6 and parts[5] == 'leaves':
            if len(parts) == 6:
                self.handle_get_employee_leaves(employee_id)
            else:
                self.handle_get_employee_leave_detail(employee_id, parts[6])
            return

        if len(parts) == 5:
            self.handle_employee_detail(employee_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/employees':
            self.handle_create_employee()
            return

        if path == '/api/v1/employees/cache/invalidate':
            self.handle_cache_invalidate()
            return

        parts = path.split('/')
        if len(parts) >= 6 and parts[1] == 'api' and parts[2] == 'v1' and parts[3] == 'employees' and parts[5] == 'leaves':
            self.handle_create_employee_leave(parts[4])
            return
        self.send_error('Endpoint não encontrado', 404)

    def handle_put(self, path: str):
        parts = path.split('/')
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'v1' and parts[3] == 'employees':
            self.handle_update_employee(parts[4])
            return

        if len(parts) >= 7 and parts[1] == 'api' and parts[2] == 'v1' and parts[3] == 'employees' and parts[5] == 'leaves':
            self.handle_update_employee_leave(parts[4], parts[6])
            return
        self.send_error('Endpoint não encontrado', 404)

    def handle_delete(self, path: str):
        if path == '/api/v1/employees/bulk':
            self.handle_bulk_delete_employees()
            return

        parts = path.split('/')
        if len(parts) == 5 and parts[1] == 'api' and parts[2] == 'v1' and parts[3] == 'employees':
            self.handle_delete_employee(parts[4])
            return

        if len(parts) >= 7 and parts[1] == 'api' and parts[2] == 'v1' and parts[3] == 'employees' and parts[5] == 'leaves':
            self.handle_delete_employee_leave(parts[4], parts[6])
            return
        self.send_error('Endpoint não encontrado', 404)

    def handle_patch(self, path: str):
        if path == '/api/v1/employees/bulk':
            self.handle_bulk_update_employees()
            return
        self.send_error('Endpoint não encontrado', 404)

    @staticmethod
    def _employee_to_dict(employee: Employee):
        return {
            'id': employee.id,
            'unique_id': employee.unique_id,
            'absolute_id': employee.absolute_id or '',
            'company_code': employee.company_code or '',
            'registration_number': employee.registration_number or '',
            'full_name': employee.name,
            'cpf': employee.cpf or '',
            'phone_number': employee.phone or '',
            'email': employee.email or '',
            'department': employee.department or '',
            'position': employee.position or '',
            'birth_date': employee.birth_date.isoformat() if employee.birth_date else '',
            'sex': employee.sex or '',
            'marital_status': employee.marital_status or '',
            'admission_date': employee.admission_date.isoformat() if employee.admission_date else '',
            'contract_type': employee.contract_type or '',
            'employment_status': employee.employment_status or 'Ativo',
            'termination_date': employee.termination_date.isoformat() if employee.termination_date else '',
            'leave_start_date': employee.leave_start_date.isoformat() if employee.leave_start_date else '',
            'leave_end_date': employee.leave_end_date.isoformat() if employee.leave_end_date else '',
            'status_reason': employee.status_reason or '',
            'is_active': employee.is_active,
            'company_id': employee.company_id,
            'work_location_id': employee.work_location_id,
        }

    def _resolve_employee(self, db, employee_id: str):
        employee_id_str = str(employee_id).strip()
        employee_id_int = int(employee_id_str) if employee_id_str.isdigit() else None

        employee_filter = (Employee.unique_id == employee_id_str)
        if employee_id_int is not None:
            employee_filter = (Employee.id == employee_id_int) | employee_filter

        return db.query(Employee).filter(employee_filter).first()

    @staticmethod
    def _parse_iso_date(value):
        if value in (None, ''):
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return None

    def handle_employees_list(self):
        db = None
        try:
            query = urllib.parse.urlparse(self.handler.path).query
            args = urllib.parse.parse_qs(query)
            include_inactive = args.get('status', [''])[0] == 'all'

            db = SessionLocal()
            query_obj = db.query(Employee)
            if not include_inactive:
                query_obj = query_obj.filter(Employee.is_active == True)

            employees = query_obj.order_by(Employee.name.asc()).all()
            payload = [self._employee_to_dict(employee) for employee in employees]

            self.send_json_response({
                'employees': payload,
                'total': len(payload),
                'source': 'PostgreSQL'
            })
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao carregar funcionários: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_cache_status(self):
        try:
            import time

            current_time = time.time()
            cache_age = current_time - employees_cache['last_update']
            is_valid = employees_cache['data'] is not None and cache_age < employees_cache['ttl']

            self.send_json_response({
                'cache_valid': is_valid,
                'cache_age_seconds': round(cache_age, 2),
                'cache_ttl_seconds': employees_cache['ttl'],
                'has_data': employees_cache['data'] is not None,
                'employee_count': len(employees_cache['data']['employees']) if employees_cache['data'] else 0,
                'last_update': employees_cache['last_update']
            })
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def handle_cache_invalidate(self):
        try:
            authenticated_user = self.handler.get_authenticated_user()
            if not authenticated_user:
                self.send_json_response({'error': 'Usuário não autenticado'}, 401)
                return

            invalidate_employees_cache()
            self.send_json_response({
                'success': True,
                'message': 'Cache invalidado com sucesso',
                'invalidated_by': authenticated_user.username
            })
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def handle_create_employee(self):
        try:
            data = self.get_request_data()

            required_fields = ['unique_id', 'full_name', 'phone_number']
            for field in required_fields:
                if not data.get(field):
                    self.send_json_response({'error': f'Campo obrigatório: {field}'}, 400)
                    return

            db = SessionLocal()
            try:
                existing = db.query(Employee).filter(Employee.unique_id == data.get('unique_id')).first()
                if existing:
                    self.send_json_response({'error': f"ID único {data.get('unique_id')} já existe"}, 400)
                    return
            finally:
                db.close()

            employee_data = {
                'unique_id': data.get('unique_id'),
                'absolute_id': data.get('absolute_id'),
                'company_code': data.get('company_code'),
                'registration_number': data.get('registration_number'),
                'full_name': data.get('full_name'),
                'cpf': data.get('cpf'),
                'phone_number': data.get('phone_number'),
                'email': data.get('email', ''),
                'department': data.get('department', ''),
                'position': data.get('position', ''),
                'birth_date': data.get('birth_date', ''),
                'sex': data.get('sex', ''),
                'marital_status': data.get('marital_status', ''),
                'admission_date': data.get('admission_date', ''),
                'contract_type': data.get('contract_type', ''),
                'status_reason': data.get('status_reason', ''),
                'termination_date': data.get('termination_date', ''),
                'company_id': data.get('company_id'),
                'work_location_id': data.get('work_location_id'),
                'is_active': True,
            }

            reg_raw = str(employee_data.get('registration_number') or '').strip()
            reg_digits = re.sub(r'\D', '', reg_raw)
            if reg_digits:
                employee_data['registration_number'] = reg_digits.zfill(5)

            status_reason_raw = str(employee_data.get('status_reason') or '').strip().lower()
            termination_date_raw = str(employee_data.get('termination_date') or '').strip()
            if termination_date_raw or ('demit' in status_reason_raw) or ('deslig' in status_reason_raw):
                employee_data['is_active'] = False

            if not save_employee_to_db(employee_data):
                self.send_json_response({'error': 'Erro ao salvar funcionário'}, 500)
                return

            db = SessionLocal()
            try:
                created = db.query(Employee).filter(Employee.unique_id == employee_data.get('unique_id')).order_by(Employee.id.desc()).first()
                if not created:
                    self.send_json_response({'error': 'Funcionário criado, mas não encontrado para retorno'}, 500)
                    return
                self.send_json_response(self._employee_to_dict(created), 201)
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)

    def handle_update_employee(self, employee_id: str):
        db = None
        try:
            data = self.get_request_data()
            db = SessionLocal()

            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            selected_company_code = employee.company_code
            if 'company_id' in data and data.get('company_id'):
                company = db.query(Company).filter(Company.id == data.get('company_id')).first()
                if company:
                    employee.company_id = company.id
                    employee.company_code = company.payroll_prefix
                    selected_company_code = company.payroll_prefix

            if 'company_code' in data and data.get('company_code'):
                employee.company_code = data.get('company_code')
                selected_company_code = data.get('company_code')

            matricula_value = None
            if 'matricula' in data and data.get('matricula'):
                matricula_value = str(data.get('matricula')).strip()
            elif 'registration_number' in data and data.get('registration_number'):
                matricula_value = str(data.get('registration_number')).strip()

            if matricula_value:
                matricula_value = re.sub(r'\D', '', matricula_value).zfill(5)
                employee.registration_number = matricula_value
                generated_unique_id = f'{selected_company_code}{matricula_value.zfill(5)}'
                employee.unique_id = generated_unique_id

                cpf_value = data.get('cpf') or employee.cpf
                absolute_id = f'{selected_company_code}-{generated_unique_id}'
                if cpf_value:
                    cpf_normalized = normalize_cpf(str(cpf_value))
                    absolute_id = f'{absolute_id}-{cpf_normalized}' if cpf_normalized else absolute_id

                existing_abs = db.query(Employee).filter(Employee.absolute_id == absolute_id, Employee.id != employee.id).first()
                if existing_abs:
                    self.send_json_response({'error': f'absolute_id {absolute_id} já existe em outro funcionário'}, 400)
                    return
                employee.absolute_id = absolute_id

            prev_pos = employee.position
            prev_dept = employee.department
            prev_loc = employee.work_location_id

            if 'full_name' in data:
                employee.name = data['full_name']
            if 'cpf' in data:
                employee.cpf = data['cpf']
            if 'phone_number' in data:
                employee.phone = data['phone_number']
            if 'email' in data:
                employee.email = data['email']
            if 'department' in data:
                employee.department = data['department']
            if 'position' in data:
                employee.position = data['position']
            if 'is_active' in data:
                employee.is_active = data['is_active']

            if 'birth_date' in data:
                employee.birth_date = self._parse_iso_date(data['birth_date'])
            if 'sex' in data:
                employee.sex = data['sex'] or None
            if 'marital_status' in data:
                employee.marital_status = data['marital_status'] or None
            if 'admission_date' in data:
                employee.admission_date = self._parse_iso_date(data['admission_date'])
            if 'contract_type' in data:
                employee.contract_type = data['contract_type'] or None
            if 'status_reason' in data:
                employee.status_reason = data['status_reason'] or None
            if 'company_id' in data:
                employee.company_id = data['company_id'] if data['company_id'] != '' else None
            if 'work_location_id' in data:
                employee.work_location_id = data['work_location_id'] if data['work_location_id'] != '' else None
            if 'employment_status' in data:
                employee.employment_status = data['employment_status'] or 'Ativo'
            if 'termination_date' in data:
                employee.termination_date = self._parse_iso_date(data['termination_date'])
            if 'leave_start_date' in data:
                employee.leave_start_date = self._parse_iso_date(data['leave_start_date'])
            if 'leave_end_date' in data:
                employee.leave_end_date = self._parse_iso_date(data['leave_end_date'])

            status_reason_raw = str(employee.status_reason or '').strip().lower()
            if employee.termination_date or ('demit' in status_reason_raw) or ('deslig' in status_reason_raw):
                employee.is_active = False

            employee.name_id = generate_name_id(employee.company_code, employee.registration_number, employee.name)

            if employee.position != prev_pos or employee.department != prev_dept or employee.work_location_id != prev_loc:
                movement = MovementRecord(
                    employee_id=employee.id,
                    movement_type='Atualização de Pessoal',
                    previous_position=prev_pos,
                    new_position=employee.position,
                    previous_department=prev_dept,
                    new_department=employee.department,
                    previous_work_location_id=prev_loc,
                    new_work_location_id=employee.work_location_id,
                    date=date.today(),
                    reason='Edição Manual'
                )
                db.add(movement)

            db.commit()
            db.refresh(employee)

            invalidate_employees_cache()
            self.send_json_response(self._employee_to_dict(employee), 200)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_delete_employee(self, employee_id: str):
        db = None
        try:
            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            employee.is_active = False
            employee_name = employee.name
            db.commit()

            invalidate_employees_cache()
            self.send_json_response({'message': f'Funcionário {employee_name} removido com sucesso'}, 200)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_bulk_delete_employees(self):
        db = None
        try:
            data = self.get_request_data()
            employee_ids = data.get('employee_ids', [])

            if not employee_ids:
                self.send_json_response({'error': 'Nenhum funcionário selecionado'}, 400)
                return

            if not isinstance(employee_ids, list):
                self.send_json_response({'error': 'employee_ids deve ser uma lista'}, 400)
                return

            db = SessionLocal()
            employees = db.query(Employee).filter(Employee.id.in_(employee_ids), Employee.is_active == True).all()
            for emp in employees:
                emp.is_active = False

            deleted_count = len(employees)
            db.commit()

            invalidate_employees_cache()
            self.send_json_response({
                'message': f'{deleted_count} funcionários removidos com sucesso',
                'deleted_count': deleted_count
            }, 200)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_bulk_update_employees(self):
        db = None
        try:
            data = self.get_request_data()
            employee_ids = data.get('employee_ids', [])
            updates = data.get('updates', {})

            if not employee_ids:
                self.send_json_response({'error': 'Nenhum funcionário selecionado'}, 400)
                return

            if not isinstance(employee_ids, list):
                self.send_json_response({'error': 'employee_ids deve ser uma lista'}, 400)
                return

            if not updates:
                self.send_json_response({'error': 'Nenhum campo para atualizar fornecido'}, 400)
                return

            allowed_fields = ['department', 'position', 'work_location_id']
            update_fields = {}
            for field, value in updates.items():
                if field in allowed_fields and str(value).strip():
                    update_fields[field] = value

            if 'work_location_id' in updates and updates['work_location_id'] == '':
                update_fields['work_location_id'] = None

            if not update_fields:
                self.send_json_response({'error': 'Nenhum campo válido para atualizar'}, 400)
                return

            db = SessionLocal()
            employees = db.query(Employee).filter(Employee.id.in_(employee_ids), Employee.is_active == True).all()

            updated_count = 0
            for emp in employees:
                prev_pos = emp.position
                prev_dept = emp.department
                prev_loc = emp.work_location_id
                changed = False

                if 'department' in update_fields:
                    emp.department = update_fields['department']
                    changed = True
                if 'position' in update_fields:
                    emp.position = update_fields['position']
                    changed = True
                if 'work_location_id' in update_fields:
                    emp.work_location_id = update_fields['work_location_id']
                    changed = True

                if changed:
                    updated_count += 1
                    if emp.position != prev_pos or emp.department != prev_dept or emp.work_location_id != prev_loc:
                        movement = MovementRecord(
                            employee_id=emp.id,
                            movement_type='Transferência (Lote)',
                            previous_position=prev_pos,
                            new_position=emp.position,
                            previous_department=prev_dept,
                            new_department=emp.department,
                            previous_work_location_id=prev_loc,
                            new_work_location_id=emp.work_location_id,
                            date=date.today(),
                            reason='Edição em Massa'
                        )
                        db.add(movement)

            db.commit()

            invalidate_employees_cache()
            self.send_json_response({
                'message': f'{updated_count} funcionários atualizados com sucesso e histórico gerado',
                'updated_count': updated_count,
                'updates': updates,
            }, 200)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_employee_detail(self, employee_id: str):
        db = None
        try:
            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return
            self.send_json_response(self._employee_to_dict(employee), 200)
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao buscar funcionário: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_get_employee_payroll(self, employee_id: str):
        db = None
        try:
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.handler.path).query)
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            period_id = query_params.get('period_id', [None])[0]
            company = query_params.get('company', [None])[0]
            limit = int(query_params.get('limit', ['24'])[0] or 24)

            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            payroll_query = db.query(PayrollData, PayrollPeriod).outerjoin(
                PayrollPeriod, PayrollPeriod.id == PayrollData.period_id
            ).filter(PayrollData.employee_id == employee.id)

            if year:
                payroll_query = payroll_query.filter(PayrollPeriod.year == int(year))
            if month:
                payroll_query = payroll_query.filter(PayrollPeriod.month == int(month))
            if period_id:
                payroll_query = payroll_query.filter(PayrollData.period_id == int(period_id))
            if company and company != 'all':
                payroll_query = payroll_query.filter(PayrollPeriod.company == company)

            records = payroll_query.order_by(
                PayrollPeriod.year.desc(),
                PayrollPeriod.month.desc(),
                PayrollData.id.desc()
            ).limit(max(1, min(limit, 120))).all()

            payrolls = []
            total_net = 0.0
            total_gross = 0.0

            for payroll, period in records:
                gross_salary = float(payroll.gross_salary or 0)
                net_salary = float(payroll.net_salary or 0)
                total_gross += gross_salary
                total_net += net_salary

                period_name = period.period_name if period else f'Período {payroll.period_id}'

                payrolls.append({
                    'id': payroll.id,
                    'period': {
                        'id': payroll.period_id,
                        'year': period.year if period else None,
                        'month': period.month if period else None,
                        'name': period_name,
                        'company': period.company if period else None
                    },
                    'gross_salary': gross_salary,
                    'net_salary': net_salary,
                    'earnings_data': payroll.earnings_data or {},
                    'deductions_data': payroll.deductions_data or {},
                    'benefits_data': payroll.benefits_data or {},
                    'additional_data': payroll.additional_data or {},
                    'upload_filename': payroll.upload_filename,
                    'upload_date': payroll.upload_date.isoformat() if payroll.upload_date else None,
                    'updated_at': payroll.updated_at.isoformat() if getattr(payroll, 'updated_at', None) else None
                })

            self.send_json_response({
                'employee': {
                    'id': employee.id,
                    'unique_id': employee.unique_id,
                    'name': employee.name,
                },
                'filters': {
                    'year': int(year) if year else None,
                    'month': int(month) if month else None,
                    'period_id': int(period_id) if period_id else None,
                    'company': company,
                    'limit': limit,
                },
                'total_records': len(payrolls),
                'summary': {
                    'total_gross_salary': total_gross,
                    'total_net_salary': total_net,
                    'avg_net_salary': (total_net / len(payrolls)) if payrolls else 0.0,
                },
                'payrolls': payrolls,
            }, 200)

        except Exception as ex:
            self.send_json_response({'error': f'Erro ao buscar folha do colaborador: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_get_employee_movements(self, employee_id: str):
        db = None
        try:
            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            movements = db.query(MovementRecord).filter(
                MovementRecord.employee_id == employee.id
            ).order_by(MovementRecord.date.desc(), MovementRecord.id.desc()).all()

            results = []
            for movement in movements:
                results.append({
                    'id': movement.id,
                    'date': movement.date.isoformat() if movement.date else None,
                    'movement_type': movement.movement_type,
                    'previous_position': movement.previous_position,
                    'new_position': movement.new_position,
                    'previous_department': movement.previous_department,
                    'new_department': movement.new_department,
                    'previous_work_location_id': movement.previous_work_location_id,
                    'new_work_location_id': movement.new_work_location_id,
                    'reason': movement.reason,
                })

            self.send_json_response({'movements': results}, 200)
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao buscar movimentos: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_get_employee_timecard(self, employee_id: str):
        db = None
        try:
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.handler.path).query)
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            limit = int(query_params.get('limit', ['24'])[0] or 24)

            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            timecard_query = db.query(TimecardData, TimecardPeriod).outerjoin(
                TimecardPeriod, TimecardPeriod.id == TimecardData.period_id
            ).filter(TimecardData.employee_id == employee.id)

            if year:
                timecard_query = timecard_query.filter(TimecardPeriod.year == int(year))
            if month:
                timecard_query = timecard_query.filter(TimecardPeriod.month == int(month))

            records = timecard_query.order_by(
                TimecardPeriod.year.desc(),
                TimecardPeriod.month.desc(),
                TimecardData.id.desc(),
            ).limit(max(1, min(limit, 120))).all()

            timecards = []
            total_overtime_50 = 0.0
            total_overtime_100 = 0.0
            total_night_overtime_50 = 0.0
            total_night_overtime_100 = 0.0
            total_night_hours = 0.0

            for timecard, period in records:
                overtime_50 = float(timecard.overtime_50 or 0)
                overtime_100 = float(timecard.overtime_100 or 0)
                night_overtime_50 = float(timecard.night_overtime_50 or 0)
                night_overtime_100 = float(timecard.night_overtime_100 or 0)
                night_hours = float(timecard.night_hours or 0)
                normal_hours = float(timecard.normal_hours or 0)
                absences = float(timecard.absences or 0)
                dsr_debit = float(timecard.dsr_debit or 0)
                bonus_hours = float(timecard.bonus_hours or 0)

                total_overtime_50 += overtime_50
                total_overtime_100 += overtime_100
                total_night_overtime_50 += night_overtime_50
                total_night_overtime_100 += night_overtime_100
                total_night_hours += night_hours

                period_name = period.period_name if period else f'Período {timecard.period_id}'

                timecards.append({
                    'id': timecard.id,
                    'period': {
                        'id': timecard.period_id,
                        'year': period.year if period else None,
                        'month': period.month if period else None,
                        'name': period_name,
                    },
                    'employee_number': timecard.employee_number,
                    'employee_name': timecard.employee_name,
                    'company': timecard.company,
                    'normal_hours': normal_hours,
                    'overtime_50': overtime_50,
                    'overtime_100': overtime_100,
                    'night_overtime_50': night_overtime_50,
                    'night_overtime_100': night_overtime_100,
                    'night_hours': night_hours,
                    'absences': absences,
                    'dsr_debit': dsr_debit,
                    'bonus_hours': bonus_hours,
                    'total_overtime': overtime_50 + overtime_100,
                    'total_night': night_overtime_50 + night_overtime_100 + night_hours,
                    'upload_filename': timecard.upload_filename,
                    'updated_at': timecard.updated_at.isoformat() if getattr(timecard, 'updated_at', None) else None,
                    'created_at': timecard.created_at.isoformat() if getattr(timecard, 'created_at', None) else None,
                })

            total_records = len(timecards)
            self.send_json_response({
                'employee': {
                    'id': employee.id,
                    'unique_id': employee.unique_id,
                    'name': employee.name,
                },
                'filters': {
                    'year': int(year) if year else None,
                    'month': int(month) if month else None,
                    'limit': limit,
                },
                'total_records': total_records,
                'summary': {
                    'total_overtime_50': total_overtime_50,
                    'total_overtime_100': total_overtime_100,
                    'total_overtime': total_overtime_50 + total_overtime_100,
                    'total_night_overtime_50': total_night_overtime_50,
                    'total_night_overtime_100': total_night_overtime_100,
                    'total_night_hours': total_night_hours,
                    'total_night': total_night_overtime_50 + total_night_overtime_100 + total_night_hours,
                    'avg_overtime': ((total_overtime_50 + total_overtime_100) / total_records) if total_records else 0.0,
                },
                'timecards': timecards,
            }, 200)

        except Exception as ex:
            if 'timecard_' in str(ex) and 'does not exist' in str(ex):
                self.send_json_response({
                    'employee': {
                        'id': int(employee_id) if str(employee_id).isdigit() else employee_id,
                    },
                    'filters': {
                        'year': int(year) if year else None,
                        'month': int(month) if month else None,
                        'limit': limit,
                    },
                    'total_records': 0,
                    'summary': {
                        'total_overtime_50': 0.0,
                        'total_overtime_100': 0.0,
                        'total_overtime': 0.0,
                        'total_night_overtime_50': 0.0,
                        'total_night_overtime_100': 0.0,
                        'total_night_hours': 0.0,
                        'total_night': 0.0,
                        'avg_overtime': 0.0,
                    },
                    'timecards': [],
                }, 200)
            else:
                self.send_json_response({'error': f'Erro ao buscar cartão ponto do colaborador: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_get_employee_leaves(self, employee_id: str):
        db = None
        try:
            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            leaves = db.query(LeaveRecord).filter(
                LeaveRecord.employee_id == employee.id
            ).order_by(LeaveRecord.start_date.desc()).all()

            leaves_data = [{
                'id': leave.id,
                'leave_type': leave.leave_type,
                'start_date': leave.start_date.isoformat() if leave.start_date else None,
                'end_date': leave.end_date.isoformat() if leave.end_date else None,
                'days': leave.days,
                'notes': leave.notes,
                'created_at': leave.created_at.isoformat() if leave.created_at else None,
            } for leave in leaves]

            self.send_json_response(leaves_data, 200)
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao buscar afastamentos: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_get_employee_leave_detail(self, employee_id: str, leave_id: str):
        db = None
        try:
            try:
                leave_id_int = int(leave_id)
            except ValueError:
                self.send_json_response({'error': 'ID de afastamento inválido'}, 400)
                return

            db = SessionLocal()
            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            leave = db.query(LeaveRecord).filter(
                LeaveRecord.id == leave_id_int,
                LeaveRecord.employee_id == employee.id
            ).first()

            if not leave:
                self.send_json_response({'error': 'Afastamento não encontrado'}, 404)
                return

            self.send_json_response({
                'id': leave.id,
                'leave_type': leave.leave_type,
                'start_date': leave.start_date.isoformat() if leave.start_date else None,
                'end_date': leave.end_date.isoformat() if leave.end_date else None,
                'days': leave.days,
                'notes': leave.notes,
                'created_at': leave.created_at.isoformat() if leave.created_at else None,
            }, 200)
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao buscar afastamento: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_create_employee_leave(self, employee_id: str):
        db = None
        try:
            data = self.get_request_data()
            db = SessionLocal()

            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            if not data.get('leave_type') or not data.get('start_date') or not data.get('end_date'):
                self.send_json_response({'error': 'Campos obrigatórios: leave_type, start_date, end_date'}, 400)
                return

            leave = LeaveRecord(
                employee_id=employee.id,
                unified_code=employee.unique_id,
                leave_type=data['leave_type'],
                start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
                days=float(data.get('days', 0)) if data.get('days') else None,
                notes=data.get('notes'),
                created_at=datetime.now(),
            )

            db.add(leave)
            db.commit()
            db.refresh(leave)

            self.send_json_response({
                'id': leave.id,
                'leave_type': leave.leave_type,
                'start_date': leave.start_date.isoformat(),
                'end_date': leave.end_date.isoformat(),
                'days': leave.days,
                'notes': leave.notes,
            }, 201)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro ao criar afastamento: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_update_employee_leave(self, employee_id: str, leave_id: str):
        db = None
        try:
            try:
                leave_id_int = int(leave_id)
            except ValueError:
                self.send_json_response({'error': 'ID de afastamento inválido'}, 400)
                return

            data = self.get_request_data()
            db = SessionLocal()

            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            leave = db.query(LeaveRecord).filter(
                LeaveRecord.id == leave_id_int,
                LeaveRecord.employee_id == employee.id
            ).first()

            if not leave:
                self.send_json_response({'error': 'Afastamento não encontrado'}, 404)
                return

            if 'leave_type' in data:
                leave.leave_type = data['leave_type']
            if 'start_date' in data:
                leave.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if 'end_date' in data:
                leave.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            if 'days' in data:
                leave.days = float(data['days']) if data['days'] else None
            if 'notes' in data:
                leave.notes = data['notes']

            db.commit()
            db.refresh(leave)

            self.send_json_response({
                'id': leave.id,
                'leave_type': leave.leave_type,
                'start_date': leave.start_date.isoformat(),
                'end_date': leave.end_date.isoformat(),
                'days': leave.days,
                'notes': leave.notes,
            }, 200)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro ao atualizar afastamento: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()

    def handle_delete_employee_leave(self, employee_id: str, leave_id: str):
        db = None
        try:
            try:
                leave_id_int = int(leave_id)
            except ValueError:
                self.send_json_response({'error': 'ID de afastamento inválido'}, 400)
                return

            db = SessionLocal()

            employee = self._resolve_employee(db, employee_id)
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            leave = db.query(LeaveRecord).filter(
                LeaveRecord.id == leave_id_int,
                LeaveRecord.employee_id == employee.id
            ).first()

            if not leave:
                self.send_json_response({'error': 'Afastamento não encontrado'}, 404)
                return

            db.delete(leave)
            db.commit()
            self.send_json_response({'message': 'Afastamento removido com sucesso'}, 200)
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'error': f'Erro ao deletar afastamento: {str(ex)}'}, 500)
        finally:
            if db is not None:
                db.close()
