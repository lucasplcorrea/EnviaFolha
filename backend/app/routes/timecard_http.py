"""HTTP router for timecard endpoints used by the React frontend."""

import os
import re
import tempfile
import urllib.parse
import unicodedata
from decimal import Decimal
from sqlalchemy import func

from app.core.database import Base, engine
from app.routes.base import BaseRouter
from app.services.runtime_compat import SessionLocal
from app.models.employee import Employee
from app.models.timecard import TimecardData, TimecardPeriod, TimecardProcessingLog, TimecardEmployeeAlias
from app.services.timecard_xlsx_processor import TimecardXLSXProcessor


class TimecardRouter(BaseRouter):
    def handle_get(self, path: str):
        if path == '/api/v1/timecard/periods':
            self.handle_timecard_periods_list()
            return

        if path == '/api/v1/timecard/processing-logs':
            self.handle_timecard_processing_logs()
            return

        if path == '/api/v1/timecard/stats':
            self.handle_timecard_stats()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/timecard/upload-xlsx':
            self.handle_upload_timecard_xlsx()
            return

        if path == '/api/v1/timecard/manual-approvals':
            self.handle_timecard_manual_approvals()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_delete(self, path: str):
        if path.startswith('/api/v1/timecard/periods/'):
            period_id = path.split('/')[-1]
            self.handle_delete_timecard_period(period_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_timecard_periods_list(self):
        db = SessionLocal()
        try:
            periods = db.query(TimecardPeriod).order_by(TimecardPeriod.year.desc(), TimecardPeriod.month.desc()).limit(100).all()

            rows = []
            for period in periods:
                employee_count = db.query(TimecardData).filter(TimecardData.period_id == period.id).count()
                totals = db.query(
                    func.sum(TimecardData.overtime_50).label('overtime_50'),
                    func.sum(TimecardData.overtime_100).label('overtime_100'),
                    func.sum(TimecardData.night_overtime_50).label('night_overtime_50'),
                    func.sum(TimecardData.night_overtime_100).label('night_overtime_100'),
                    func.sum(TimecardData.night_hours).label('night_hours'),
                ).filter(TimecardData.period_id == period.id).first()

                ot50 = totals.overtime_50 or Decimal('0')
                ot100 = totals.overtime_100 or Decimal('0')
                not50 = totals.night_overtime_50 or Decimal('0')
                not100 = totals.night_overtime_100 or Decimal('0')
                nh = totals.night_hours or Decimal('0')

                rows.append({
                    'id': period.id,
                    'year': period.year,
                    'month': period.month,
                    'period_name': period.period_name,
                    'start_date': period.start_date.isoformat() if period.start_date else None,
                    'end_date': period.end_date.isoformat() if period.end_date else None,
                    'description': period.description,
                    'is_active': period.is_active,
                    'created_at': period.created_at.isoformat() if period.created_at else None,
                    'employee_count': employee_count,
                    'overtime_50': float(ot50),
                    'overtime_100': float(ot100),
                    'night_overtime_50': float(not50),
                    'night_overtime_100': float(not100),
                    'night_hours': float(nh),
                    'total_overtime': float(ot50 + ot100),
                    'total_night_hours': float(not50 + not100 + nh),
                })

            self.send_json_response(rows)
        except Exception as ex:
            if 'does not exist' in str(ex) and 'timecard_' in str(ex):
                self.send_json_response([])
                return
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_timecard_processing_logs(self):
        db = SessionLocal()
        try:
            logs = db.query(TimecardProcessingLog).order_by(TimecardProcessingLog.created_at.desc()).limit(100).all()
            payload = []
            for log in logs:
                payload.append({
                    'id': log.id,
                    'period_id': log.period_id,
                    'filename': log.filename,
                    'file_size': log.file_size,
                    'total_rows': log.total_rows,
                    'processed_rows': log.processed_rows,
                    'error_rows': log.error_rows,
                    'status': log.status,
                    'error_message': log.error_message,
                    'processing_summary': log.processing_summary,
                    'processing_time': float(log.processing_time) if log.processing_time is not None else None,
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                })

            self.send_json_response({'logs': payload})
        except Exception as ex:
            if 'does not exist' in str(ex) and 'timecard_' in str(ex):
                self.send_json_response({'logs': []})
                return
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_timecard_stats(self):
        db = SessionLocal()
        try:
            query = urllib.parse.urlparse(self.handler.path).query
            params = urllib.parse.parse_qs(query)

            year = params.get('year', [None])[0]
            month = params.get('month', [None])[0]
            period_id = params.get('period_id', [None])[0]
            employees = params.get('employees', [None])[0]
            companies = params.get('companies', [None])[0]
            departments = params.get('departments', [None])[0]
            employee_ids = []
            selected_employee_names = {}

            def _normalize_name(value: str) -> str:
                if not value:
                    return ''
                normalized = unicodedata.normalize('NFKD', str(value))
                normalized = normalized.encode('ascii', 'ignore').decode('ascii')
                normalized = normalized.lower()
                normalized = ''.join(ch if ch.isalnum() else ' ' for ch in normalized)
                return ' '.join(normalized.split())

            def _names_consistent(left: str, right: str) -> bool:
                a = _normalize_name(left)
                b = _normalize_name(right)
                if not a or not b:
                    return False
                return a == b or a in b or b in a

            stats_query = db.query(TimecardData)

            if period_id:
                stats_query = stats_query.filter(TimecardData.period_id == int(period_id))
            elif year and month:
                period = db.query(TimecardPeriod).filter(
                    TimecardPeriod.year == int(year),
                    TimecardPeriod.month == int(month),
                ).order_by(TimecardPeriod.id.desc()).first()
                if period:
                    stats_query = stats_query.filter(TimecardData.period_id == period.id)
                else:
                    self.send_json_response({
                        'total_employees': 0,
                        'overtime_50': 0.0,
                        'overtime_100': 0.0,
                        'night_overtime_50': 0.0,
                        'night_overtime_100': 0.0,
                        'night_hours': 0.0,
                        'intrajornada_hours': 0.0,
                        'dsr_debit_hours': 0.0,
                        'total_overtime_hours': 0.0,
                        'total_night_hours': 0.0,
                        'employees_with_overtime': 0,
                        'employees_with_night_hours': 0,
                        'employees_with_intrajornada': 0,
                        'employees_with_dsr_debit': 0,
                        'average_overtime': 0.0,
                        'average_night_hours': 0.0,
                        'average_intrajornada': 0.0,
                        'average_dsr_debit': 0.0,
                        'by_company': {},
                    })
                    return

            if employees:
                try:
                    employee_ids = [int(item.strip()) for item in employees.split(',') if item.strip()]
                    if employee_ids:
                        selected = db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
                        selected_employee_names = {int(emp.id): str(emp.name or '') for emp in selected}
                        stats_query = stats_query.filter(TimecardData.employee_id.in_(employee_ids))
                except Exception:
                    pass

            if companies:
                try:
                    company_codes = [item.strip() for item in companies.split(',') if item.strip()]
                    if company_codes:
                        stats_query = stats_query.filter(TimecardData.company.in_(company_codes))
                except Exception:
                    pass

            if departments:
                try:
                    department_names = [item.strip() for item in departments.split(',') if item.strip()]
                    if department_names:
                        normalized_departments = [item.lower() for item in department_names]
                        stats_query = stats_query.join(Employee, Employee.id == TimecardData.employee_id).filter(
                            func.lower(Employee.department).in_(normalized_departments)
                        )
                except Exception:
                    pass

            timecard_data = stats_query.all()

            # Defesa contra vínculos incorretos (employee_id divergente do nome em timecard_data).
            # Sem isso, um registro mal associado pode inflar os cards do colaborador selecionado.
            if employee_ids and selected_employee_names:
                timecard_data = [
                    row for row in timecard_data
                    if row.employee_id in selected_employee_names
                    and _names_consistent(row.employee_name or '', selected_employee_names[row.employee_id])
                ]

            if not timecard_data:
                self.send_json_response({
                    'total_employees': 0,
                    'overtime_50': 0.0,
                    'overtime_100': 0.0,
                    'night_overtime_50': 0.0,
                    'night_overtime_100': 0.0,
                    'night_hours': 0.0,
                    'intrajornada_hours': 0.0,
                    'dsr_debit_hours': 0.0,
                    'total_overtime_hours': 0.0,
                    'total_night_hours': 0.0,
                    'employees_with_overtime': 0,
                    'employees_with_night_hours': 0,
                    'employees_with_intrajornada': 0,
                    'employees_with_dsr_debit': 0,
                    'average_overtime': 0.0,
                    'average_night_hours': 0.0,
                    'average_intrajornada': 0.0,
                    'average_dsr_debit': 0.0,
                    'by_company': {},
                })
                return

            total_employees = len(timecard_data)
            sum_overtime_50 = sum((d.overtime_50 or Decimal('0') for d in timecard_data), Decimal('0'))
            sum_overtime_100 = sum((d.overtime_100 or Decimal('0') for d in timecard_data), Decimal('0'))
            sum_night_overtime_50 = sum((d.night_overtime_50 or Decimal('0') for d in timecard_data), Decimal('0'))
            sum_night_overtime_100 = sum((d.night_overtime_100 or Decimal('0') for d in timecard_data), Decimal('0'))
            sum_night_hours = sum((d.night_hours or Decimal('0') for d in timecard_data), Decimal('0'))
            sum_intrajornada = sum((d.absences or Decimal('0') for d in timecard_data), Decimal('0'))
            sum_dsr_debit = sum((d.dsr_debit or Decimal('0') for d in timecard_data), Decimal('0'))

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

            by_company = {}
            for company in ['0059', '0060']:
                company_data = [d for d in timecard_data if d.company == company]
                if company_data:
                    company_intrajornada = sum((d.absences or Decimal('0') for d in company_data), Decimal('0'))
                    company_dsr = sum((d.dsr_debit or Decimal('0') for d in company_data), Decimal('0'))
                    by_company[company] = {
                        'employees': len(company_data),
                        'total_overtime': float(sum((d.get_total_overtime() for d in company_data), Decimal('0'))),
                        'total_night_hours': float(sum((d.get_total_night_hours() for d in company_data), Decimal('0'))),
                        'total_intrajornada': float(company_intrajornada),
                        'total_dsr_debit': float(company_dsr),
                        'average_overtime': float(sum((d.get_total_overtime() for d in company_data), Decimal('0')) / len(company_data)),
                        'average_night_hours': float(sum((d.get_total_night_hours() for d in company_data), Decimal('0')) / len(company_data)),
                        'average_intrajornada': float(company_intrajornada / len(company_data)),
                        'average_dsr_debit': float(company_dsr / len(company_data)),
                    }

            self.send_json_response({
                'total_employees': total_employees,
                'overtime_50': float(sum_overtime_50),
                'overtime_100': float(sum_overtime_100),
                'night_overtime_50': float(sum_night_overtime_50),
                'night_overtime_100': float(sum_night_overtime_100),
                'night_hours': float(sum_night_hours),
                'intrajornada_hours': float(sum_intrajornada),
                'dsr_debit_hours': float(sum_dsr_debit),
                'total_overtime_hours': float(total_overtime),
                'total_night_hours': float(total_night),
                'employees_with_overtime': employees_with_overtime,
                'employees_with_night_hours': employees_with_night,
                'employees_with_intrajornada': employees_with_intrajornada,
                'employees_with_dsr_debit': employees_with_dsr_debit,
                'average_overtime': float(avg_overtime),
                'average_night_hours': float(avg_night),
                'average_intrajornada': float(avg_intrajornada),
                'average_dsr_debit': float(avg_dsr_debit),
                'by_company': by_company,
            })
        except Exception as ex:
            if 'does not exist' in str(ex) and 'timecard_' in str(ex):
                self.send_json_response({
                    'total_employees': 0,
                    'overtime_50': 0.0,
                    'overtime_100': 0.0,
                    'night_overtime_50': 0.0,
                    'night_overtime_100': 0.0,
                    'night_hours': 0.0,
                    'intrajornada_hours': 0.0,
                    'dsr_debit_hours': 0.0,
                    'total_overtime_hours': 0.0,
                    'total_night_hours': 0.0,
                    'employees_with_overtime': 0,
                    'employees_with_night_hours': 0,
                    'employees_with_intrajornada': 0,
                    'employees_with_dsr_debit': 0,
                    'average_overtime': 0.0,
                    'average_night_hours': 0.0,
                    'average_intrajornada': 0.0,
                    'average_dsr_debit': 0.0,
                    'by_company': {},
                })
                return
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_delete_timecard_period(self, period_id: str):
        db = SessionLocal()
        try:
            try:
                period_id_int = int(period_id)
            except ValueError:
                self.send_json_response({'error': 'ID de período inválido'}, 400)
                return

            period = db.query(TimecardPeriod).filter(TimecardPeriod.id == period_id_int).first()
            if not period:
                self.send_json_response({'error': 'Período não encontrado'}, 404)
                return

            db.delete(period)
            db.commit()
            self.send_json_response({'success': True, 'message': 'Período removido com sucesso'})
        except Exception as ex:
            db.rollback()
            self.send_json_response({'error': str(ex)}, 500)
        finally:
            db.close()

    def handle_upload_timecard_xlsx(self):
        db = None
        tmp_filepath = None
        try:
            content_type = self.handler.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_response({'error': 'Content-Type deve ser multipart/form-data'}, 400)
                return

            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break

            if not boundary:
                self.send_json_response({'error': 'Boundary não encontrado'}, 400)
                return

            content_length = int(self.handler.headers.get('Content-Length', 0))
            body = self.handler.rfile.read(content_length)

            boundary_bytes = f'--{boundary}'.encode()
            parts = body.split(boundary_bytes)

            file_data = None
            original_filename = None
            year = None
            month = None
            dry_run = False

            for part in parts:
                if not part or part in (b'--\r\n', b'--'):
                    continue
                if b'Content-Disposition' not in part:
                    continue

                if b'name="file"' in part:
                    header_blob = part.split(b'\r\n\r\n', 1)[0].decode('utf-8', errors='ignore')
                    filename_match = re.search(r'filename="([^"]+)"', header_blob)
                    if filename_match:
                        original_filename = filename_match.group(1)
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        file_data = part[split_point + 4:].rstrip(b'\r\n')
                elif b'name="year"' in part:
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        year = int(part[split_point + 4:].strip())
                elif b'name="month"' in part:
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        month = int(part[split_point + 4:].strip())
                elif b'name="dry_run"' in part:
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        raw_value = part[split_point + 4:].strip().lower()
                        dry_run = raw_value in (b'1', b'true', b'yes', b'on')

            if not file_data:
                self.send_json_response({'error': 'Arquivo não enviado'}, 400)
                return
            if not year or not month:
                self.send_json_response({'error': 'Ano e mês são obrigatórios'}, 400)
                return
            if month < 1 or month > 12:
                self.send_json_response({'error': 'Mês deve estar entre 1 e 12'}, 400)
                return

            _, original_ext = os.path.splitext(original_filename or '')
            normalized_ext = original_ext.lower()
            if normalized_ext != '.xlsx':
                self.send_json_response({'error': 'Arquivo deve ser XLSX (.xlsx)'}, 400)
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=normalized_ext or '.xlsx') as tmp_file:
                tmp_file.write(file_data)
                tmp_filepath = tmp_file.name

            db = SessionLocal()
            authenticated_user = self.handler.get_authenticated_user(db)
            user_id = authenticated_user.id if authenticated_user else None

            processor = TimecardXLSXProcessor(db=db, user_id=user_id)
            result = processor.process_xlsx_file(
                file_path=tmp_filepath,
                year=year,
                month=month,
                dry_run=dry_run,
            )

            if result.get('success'):
                self.send_json_response(result, 201)
            else:
                self.send_json_response(result, 400)
        except Exception as ex:
            self.send_json_response({'success': False, 'error': f'Erro interno: {str(ex)}'}, 500)
        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

            if tmp_filepath and os.path.exists(tmp_filepath):
                try:
                    os.unlink(tmp_filepath)
                except Exception:
                    pass

    def _normalize_name(self, value: str) -> str:
        if not value:
            return ''
        text = unicodedata.normalize('NFKD', str(value))
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = text.lower()
        text = ''.join(ch if ch.isalnum() else ' ' for ch in text)
        return ' '.join(text.split())

    def _extract_digits(self, value: str) -> str:
        return ''.join(ch for ch in str(value or '') if ch.isdigit())

    def handle_timecard_manual_approvals(self):
        db = SessionLocal()
        try:
            data = self.get_request_data()
            approvals = data.get('approvals') or []
            if not isinstance(approvals, list) or not approvals:
                self.send_json_response({'success': False, 'error': 'Lista approvals obrigatória'}, 400)
                return

            Base.metadata.create_all(bind=engine, tables=[TimecardEmployeeAlias.__table__], checkfirst=True)

            applied = 0
            ignored = 0
            invalid = []

            for index, item in enumerate(approvals, start=1):
                company_code = str(item.get('company_code', '')).strip()
                employee_number_file = str(item.get('employee_number_file', '')).strip().upper()
                employee_name_file = str(item.get('employee_name_file', '')).strip()
                source = str(item.get('source', 'manual_ui')).strip() or 'manual_ui'

                candidate_employee_id = item.get('candidate_employee_id')
                if candidate_employee_id in (None, ''):
                    ignored += 1
                    continue

                try:
                    candidate_employee_id = int(candidate_employee_id)
                except Exception:
                    invalid.append({'index': index, 'error': 'candidate_employee_id inválido'})
                    continue

                if not company_code or not employee_number_file or not employee_name_file:
                    invalid.append({'index': index, 'error': 'company_code, employee_number_file e employee_name_file são obrigatórios'})
                    continue

                employee = db.query(Employee).filter(Employee.id == candidate_employee_id).first()
                if not employee:
                    invalid.append({'index': index, 'error': f'Colaborador {candidate_employee_id} não encontrado'})
                    continue

                normalized_name_file = self._normalize_name(employee_name_file)
                if not normalized_name_file:
                    invalid.append({'index': index, 'error': 'employee_name_file inválido'})
                    continue

                existing = db.query(TimecardEmployeeAlias).filter(
                    TimecardEmployeeAlias.company_code == company_code,
                    TimecardEmployeeAlias.employee_number_file == employee_number_file,
                    TimecardEmployeeAlias.normalized_name_file == normalized_name_file,
                ).first()

                if existing:
                    existing.employee_id = candidate_employee_id
                    existing.employee_name_file = employee_name_file
                    existing.employee_number_digits = self._extract_digits(employee_number_file)
                    existing.source = source
                    existing.is_active = True
                else:
                    db.add(TimecardEmployeeAlias(
                        company_code=company_code,
                        employee_number_file=employee_number_file,
                        employee_number_digits=self._extract_digits(employee_number_file),
                        employee_name_file=employee_name_file,
                        normalized_name_file=normalized_name_file,
                        source=source,
                        is_active=True,
                        employee_id=candidate_employee_id,
                    ))

                applied += 1

            db.commit()
            self.send_json_response({
                'success': True,
                'applied': applied,
                'ignored': ignored,
                'invalid_count': len(invalid),
                'invalid': invalid,
            }, 200)
        except Exception as ex:
            db.rollback()
            self.send_json_response({'success': False, 'error': f'Erro interno: {str(ex)}'}, 500)
        finally:
            db.close()
