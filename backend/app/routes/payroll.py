"""Modular route handlers for payroll upload and statistics."""

import os
import asyncio
import urllib.parse
import zipfile
import re
import PyPDF2
from io import BytesIO
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from app.models.base import SessionLocal, engine
from app.services.payroll_formatter import segment_pdf_by_employee
from app.services.payroll_queue import get_payroll_send_job, start_payroll_send_job, _move_file_to_sent
from app.services.payroll_csv_processor import PayrollCSVProcessor
from app.services.payroll_statistics import calculate_payroll_statistics
from app.services.instance_manager import get_instance_manager
from app.services.evolution_api import EvolutionAPIService
from app.services.phone_validator import PhoneValidator
from app.services.runtime_compat import load_employees_data
from app.routes.base import BaseRouter
from app.models.payroll import PayrollPeriod, PayrollData, PayrollProcessingLog
from app.models.payroll_send import PayrollSend
from app.services.payroll_email_queue import get_email_job, start_email_job


class PayrollRouter(BaseRouter):
    """Router para endpoints de folha de pagamento."""

    PAYROLL_TYPE_DIRS = {
        '11': 'Mensal',
        '31': 'Adiantamento_13',
        '32': '13_Integral',
        '91': 'Adiantamento_Salarial',
    }

    MONTH_NAMES = {
        'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3,
        'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7,
        'agosto': 8, 'setembro': 9, 'outubro': 10,
        'novembro': 11, 'dezembro': 12,
    }

    @staticmethod
    def _normalize_unique_id(value: Optional[str]) -> str:
        digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
        if not digits:
            return ''
        return digits.lstrip('0') or '0'

    @staticmethod
    def _extract_unique_id_from_filename(filename: str) -> str:
        # Novo formato: EN_MATRICULA_TIPO_MES_ANO.pdf
        if filename.startswith('EN_'):
            parts = filename[:-4].split('_') if filename.lower().endswith('.pdf') else filename.split('_')
            if len(parts) >= 5:
                return PayrollRouter._normalize_unique_id(parts[1])

        # Formato legado: MATRICULA_holerite_mes_ano.pdf
        if '_holerite_' in filename.lower():
            return PayrollRouter._normalize_unique_id(filename.split('_', 1)[0])

        return ''

    @classmethod
    def _parse_period_from_filename(cls, filename: str):
        match = re.match(r'^EN_(.+)_([0-9]+)_([0-9]{2})_([0-9]{4})\.pdf$', os.path.basename(filename), re.IGNORECASE)
        if match:
            payroll_type, month, year = match.group(2), int(match.group(3)), int(match.group(4))
            if payroll_type in cls.PAYROLL_TYPE_DIRS and 1 <= month <= 12:
                return payroll_type, month, year

        legacy = re.match(r'^(.+)_holerite_([a-zçã]+)_([0-9]{4})\.pdf$', os.path.basename(filename), re.IGNORECASE)
        if legacy:
            month = cls.MONTH_NAMES.get(legacy.group(2).lower())
            if month:
                return '11', month, int(legacy.group(3))
        return None

    @staticmethod
    def _build_month_year_label(folder_name: str) -> str:
        # Ex.: Mensal_03_2026 -> 03/2026
        parts = folder_name.rsplit('_', 2)
        if len(parts) == 3:
            month, year = parts[1], parts[2]
            if month.isdigit() and year.isdigit() and len(year) == 4:
                return f"{month.zfill(2)}/{year}"
        return 'desconhecido'

    @staticmethod
    def _parse_period_from_folder(folder_name: str):
        parts = folder_name.rsplit('_', 2)
        if len(parts) != 3:
            return None
        payroll_name, month, year = parts
        if not month.isdigit() or not year.isdigit():
            return None

        payroll_type = None
        for type_code, type_name in PayrollRouter.PAYROLL_TYPE_DIRS.items():
            if payroll_name == type_name:
                payroll_type = type_code
                break

        if not payroll_type:
            return None

        return payroll_type, int(month), int(year)

    def _get_processed_base_dirs(self) -> List[str]:
        candidates = []

        env_dir = os.getenv('PROCESSED_DIR', '').strip()
        if env_dir:
            candidates.append(env_dir)

        candidates.extend([
            'processed',
            os.path.join('backend', 'processed'),
            '/app/processed',
            'holerites_formatados_final',
            os.path.join('backend', 'holerites_formatados_final'),
            '/app/holerites_formatados_final',
        ])

        base_dirs = []
        for candidate in candidates:
            abs_path = os.path.abspath(candidate)
            if abs_path not in base_dirs and os.path.isdir(abs_path):
                base_dirs.append(abs_path)

        return base_dirs

    def _get_sent_base_dirs(self) -> List[str]:
        candidates = []
        env_dir = os.getenv('SENT_DIR', '').strip()
        if env_dir:
            candidates.append(env_dir)
        candidates.extend([
            'enviados', 'sent',
            os.path.join('backend', 'enviados'), os.path.join('backend', 'sent'),
            '/app/enviados', '/app/sent',
        ])
        base_dirs = []
        for candidate in candidates:
            abs_path = os.path.abspath(candidate)
            if abs_path not in base_dirs and os.path.isdir(abs_path):
                base_dirs.append(abs_path)
        return base_dirs

    def _resolve_payroll_file(self, filename: str) -> Optional[str]:
        safe_name = os.path.basename(filename or '')
        if not safe_name or safe_name != filename or not safe_name.lower().endswith('.pdf'):
            return None
        for base_dir in self._get_processed_base_dirs() + self._get_sent_base_dirs():
            for root, _, filenames in os.walk(base_dir):
                if safe_name in filenames:
                    return os.path.join(root, safe_name)
        return None

    @staticmethod
    def _extract_cpf_from_pdf(file_path: str) -> str:
        """Extrai CPF do primeiro conteúdo relevante do PDF para desempate de matrícula duplicada."""
        try:
            with open(file_path, 'rb') as file_obj:
                pdf_reader = PyPDF2.PdfReader(file_obj)
                all_text = []
                for page in pdf_reader.pages[:2]:
                    all_text.append(page.extract_text() or '')

            text = '\n'.join(all_text)

            # Priorizar CPF explicitamente rotulado
            labeled = re.search(r'CPF\s*[:\-]?\s*(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', text, re.IGNORECASE)
            if labeled:
                return re.sub(r'\D', '', labeled.group(1))

            # Fallback: primeiro padrão de CPF válido encontrado
            generic = re.search(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}', text)
            if generic:
                return re.sub(r'\D', '', generic.group(0))
        except Exception:
            pass

        return ''

    @staticmethod
    def _employee_active_score(emp: dict) -> int:
        score = 0
        if emp.get('is_active'):
            score += 100
        if not str(emp.get('termination_date') or '').strip():
            score += 30
        status_reason = str(emp.get('status_reason') or '').lower()
        if 'deslig' in status_reason or 'demit' in status_reason:
            score -= 100
        return score

    def _resolve_employee_for_file(self, candidates: List[dict], full_path: str) -> Optional[dict]:
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        pdf_cpf = self._extract_cpf_from_pdf(full_path)
        if pdf_cpf:
            cpf_matches = [e for e in candidates if re.sub(r'\D', '', str(e.get('cpf') or '')) == pdf_cpf]
            if len(cpf_matches) == 1:
                return cpf_matches[0]
            if cpf_matches:
                return max(cpf_matches, key=self._employee_active_score)

        # Se não há CPF confiável, ainda preferir o vínculo ativo para reduzir falso positivo.
        return max(candidates, key=self._employee_active_score)

    def _collect_processed_files(self, include_sent: bool = False):
        employees_payload = load_employees_data(include_inactive=True)
        employees = employees_payload.get('employees', [])

        employees_by_uid = {}
        for emp in employees:
            normalized_uid = self._normalize_unique_id(emp.get('unique_id'))
            if normalized_uid:
                employees_by_uid.setdefault(normalized_uid, []).append(emp)

        files_by_name = {}
        roots = [(base_dir, 'processed') for base_dir in self._get_processed_base_dirs()]
        if include_sent:
            roots.extend((base_dir, 'sent') for base_dir in self._get_sent_base_dirs())

        for base_dir, location in roots:
            for root, _, filenames in os.walk(base_dir):
                folder_name = os.path.basename(root)

                for filename in filenames:
                    if not filename.lower().endswith('.pdf'):
                        continue

                    period = self._parse_period_from_filename(filename)
                    month_year = f'{period[2]}-{period[1]:02d}' if period else self._build_month_year_label(folder_name)

                    full_path = os.path.join(root, filename)
                    if not os.path.isfile(full_path):
                        continue

                    unique_id = self._extract_unique_id_from_filename(filename)
                    associated_employee = self._resolve_employee_for_file(
                        employees_by_uid.get(unique_id, []),
                        full_path,
                    )
                    can_send = bool(associated_employee and associated_employee.get('phone_number'))
                    is_orphan = associated_employee is None

                    file_info = {
                        'filename': filename,
                        'filepath': full_path,
                        'size': os.path.getsize(full_path),
                        'created_at': datetime.fromtimestamp(os.path.getctime(full_path)).isoformat(),
                        'unique_id': unique_id or 'desconhecido',
                        'month_year': month_year,
                        'associated_employee': associated_employee,
                        'can_send': can_send,
                        'is_orphan': is_orphan,
                        'source_dir': base_dir,
                        'location': location,
                        'folder': folder_name,
                        'can_send_email': bool(associated_employee and associated_employee.get('email')),
                    }
                    # Processados têm prioridade se houver uma cópia com o mesmo nome.
                    if filename not in files_by_name or location == 'processed':
                        files_by_name[filename] = file_info

        files = list(files_by_name.values())
        files.sort(key=lambda item: item.get('created_at', ''), reverse=True)
        return files

    def handle_process_payroll_file(self):
        """Processa PDF consolidado de holerites e segmenta por colaborador."""
        try:
            data = self.get_request_data()
            uploaded_file = data.get('uploadedFile') or {}
            payroll_type = str(data.get('payrollType') or '').strip()
            month = data.get('month')
            year = data.get('year')

            if not uploaded_file:
                self.send_json_response({'success': False, 'error': 'Arquivo enviado não informado'}, 400)
                return

            if not payroll_type or month is None or year is None:
                self.send_json_response({'success': False, 'error': 'payrollType, month e year são obrigatórios'}, 400)
                return

            try:
                month = int(month)
                year = int(year)
            except Exception:
                self.send_json_response({'success': False, 'error': 'month/year inválidos'}, 400)
                return

            file_path = uploaded_file.get('file_path')
            if not file_path:
                filename = uploaded_file.get('filename')
                if filename:
                    candidate = os.path.join('uploads', filename)
                    if os.path.exists(candidate):
                        file_path = candidate

            if not file_path or not os.path.exists(file_path):
                self.send_json_response({'success': False, 'error': 'Arquivo de upload não encontrado no servidor'}, 400)
                return

            employees_payload = load_employees_data(include_inactive=True)
            employees = employees_payload.get('employees', [])

            result = segment_pdf_by_employee(
                pdf_path=file_path,
                employees_data=employees,
                payroll_type=payroll_type,
                month=month,
                year=year,
            )

            if result.get('success'):
                self.send_json_response(result, 200)
            else:
                self.send_json_response(result, 400)
        except Exception as ex:
            self.send_json_response({'success': False, 'error': f'Erro ao processar holerites: {str(ex)}'}, 500)

    def handle_get(self, path: str):
        if path == '/api/v1/payroll/statistics':
            self.handle_payroll_statistics()
        elif path == '/api/v1/payroll/employees':
            self.handle_payroll_employees()
        elif path == '/api/v1/payroll/divisions':
            self.handle_payroll_divisions()
        elif path == '/api/v1/payroll/companies':
            self.handle_payroll_companies()
        elif path == '/api/v1/payroll/years':
            self.handle_payroll_years()
        elif path == '/api/v1/payroll/months':
            self.handle_payroll_months()
        elif path == '/api/v1/payroll/periods':
            self.handle_list_payroll_data_periods()
        elif path == '/api/v1/payrolls/periods':
            self.handle_list_payroll_periods()
        elif path == '/api/v1/payroll/period-comparison':
            self.handle_period_comparison()
        elif path == '/api/v1/payroll/processing-history':
            self.handle_payroll_processing_history()
        elif path.startswith('/api/v1/payroll/statistics-debug'):
            self.handle_payroll_statistics_debug()
        elif path.startswith('/api/v1/payroll/statistics-filtered'):
            self.handle_payroll_statistics_filtered()
        elif path == '/api/v1/payrolls/processed':
            self.handle_payrolls_processed()
        elif path == '/api/v1/email/status':
            self.handle_email_status()
        elif path.startswith('/api/v1/payrolls/bulk-send/') and path.endswith('/status'):
            job_id = path.split('/')[-2]
            self.handle_bulk_send_status(job_id)
        else:
            self.send_error('Endpoint não encontrado', 404)

    def handle_period_comparison(self):
        """Retorna totais consolidados por competência de folha."""
        db = None
        try:
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.handler.path).query)
            company = query_params.get('company', ['all'])[0]
            period_filter = query_params.get('period', ['all'])[0]
            start_month = query_params.get('start_month', [None])[0]
            end_month = query_params.get('end_month', [None])[0]

            if not SessionLocal:
                self.send_error('PostgreSQL não disponível', 500)
                return

            db = SessionLocal()
            periods_query = db.query(PayrollPeriod)

            if company != 'all':
                periods_query = periods_query.filter(PayrollPeriod.company == company)

            if period_filter == 'mensal':
                periods_query = periods_query.filter(~PayrollPeriod.period_name.ilike('%13%'))
            elif period_filter == '13':
                periods_query = periods_query.filter(PayrollPeriod.period_name.ilike('%13%'))

            if start_month:
                start_year, start_mon = self._parse_comparison_month(start_month)
                periods_query = periods_query.filter(
                    (PayrollPeriod.year > start_year)
                    | ((PayrollPeriod.year == start_year) & (PayrollPeriod.month >= start_mon))
                )

            if end_month:
                end_year, end_mon = self._parse_comparison_month(end_month)
                periods_query = periods_query.filter(
                    (PayrollPeriod.year < end_year)
                    | ((PayrollPeriod.year == end_year) & (PayrollPeriod.month <= end_mon))
                )

            grouped_data = defaultdict(lambda: {
                'period_names': set(),
                'employee_ids': set(),
                'total_earnings': Decimal('0'),
                'total_net': Decimal('0'),
            })

            for period in periods_query.all():
                key = (period.year, period.month)
                group = grouped_data[key]
                group['period_names'].add(period.period_name)

                records = db.query(PayrollData).filter(PayrollData.period_id == period.id).all()
                for record in records:
                    group['employee_ids'].add(record.employee_id)
                    group['total_earnings'] += Decimal(str(record.gross_salary or 0))
                    group['total_net'] += Decimal(str(record.net_salary or 0))

            periods_data = []
            for (year, month), data in sorted(grouped_data.items(), reverse=True):
                total_deductions = data['total_earnings'] - data['total_net']
                periods_data.append({
                    'year': year,
                    'month': month,
                    'period_names': ', '.join(sorted(data['period_names'])),
                    'employee_count': len(data['employee_ids']),
                    'total_earnings': float(data['total_earnings']),
                    'total_deductions': float(total_deductions),
                    'total_net': float(data['total_net']),
                })

            self.send_json_response({'periods': periods_data})
        except ValueError as ex:
            self.send_error(str(ex), 400)
        except Exception as ex:
            print(f'❌ Erro ao buscar comparativo de períodos: {ex}')
            self.send_error(f'Erro interno: {str(ex)}', 500)
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def _parse_comparison_month(value: str):
        try:
            year, month = map(int, value.split('-', 1))
        except (TypeError, ValueError):
            raise ValueError('Período deve estar no formato YYYY-MM')
        if year < 1900 or month < 1 or month > 12:
            raise ValueError('Período deve estar no formato YYYY-MM')
        return year, month

    def handle_post(self, path: str):
        if path == '/api/v1/payroll/upload-csv' or path == '/api/v1/payroll-data/upload-csv':
            self.handle_upload_payroll_csv()
        elif path == '/api/v1/payroll/process' or path == '/api/v1/payrolls/process':
            self.handle_process_payroll_file()
        elif path == '/api/v1/payrolls/export-batch':
            self.handle_export_payroll_batch()
        elif path == '/api/v1/payrolls/bulk-send':
            self.handle_bulk_send_payrolls()
        elif path == '/api/v1/payrolls/email/bulk-send':
            self.handle_bulk_send_payrolls_email()
        elif path == '/api/v1/email/test-connection':
            self.handle_test_email_connection()
        elif path == '/api/v1/payrolls/send-individual':
            self.handle_send_payroll_individual()
        elif path == '/api/v1/payrolls/delete-file':
            self.handle_delete_payroll_file()
        else:
            self.send_error('Endpoint não encontrado', 404)

    def handle_delete(self, path: str):
        if path.startswith('/api/v1/payroll/periods/'):
            period_id = path.rsplit('/', 1)[-1]
            try:
                self.handle_delete_payroll_period(int(period_id))
            except ValueError:
                self.send_json_response({'success': False, 'error': 'ID de período inválido'}, 400)
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_upload_payroll_csv(self):
        """POST /api/v1/payroll/upload-csv"""
        db = None
        try:
            data = self.get_request_data()
            file_path = data.get('file_path')
            division_code = data.get('division_code', '0060')
            auto_create_employees = data.get('auto_create_employees', False)
            forced_year = data.get('year')
            forced_month = data.get('month')
            forced_payroll_type = data.get('payroll_type')

            if not file_path:
                self.send_json_response({'success': False, 'error': "Parâmetro 'file_path' obrigatório"}, 400)
                return

            if division_code not in ['0060', '0059']:
                self.send_json_response({'success': False, 'error': "division_code deve ser '0060' (Empreendimentos) ou '0059' (Infraestrutura)"}, 400)
                return

            allowed_types = {'mensal', '13_adiantamento', '13_integral', 'complementar', 'adiantamento_salario'}
            if forced_payroll_type and forced_payroll_type not in allowed_types:
                self.send_json_response({'success': False, 'error': 'payroll_type inválido'}, 400)
                return

            if forced_month is not None:
                try:
                    forced_month = int(forced_month)
                except Exception:
                    self.send_json_response({'success': False, 'error': 'month inválido'}, 400)
                    return
                if forced_month < 1 or forced_month > 12:
                    self.send_json_response({'success': False, 'error': 'month deve estar entre 1 e 12'}, 400)
                    return

            if forced_year is not None:
                try:
                    forced_year = int(forced_year)
                except Exception:
                    self.send_json_response({'success': False, 'error': 'year inválido'}, 400)
                    return
                if forced_year < 2000 or forced_year > 2100:
                    self.send_json_response({'success': False, 'error': 'year fora da faixa esperada'}, 400)
                    return

            db = SessionLocal()
            user_id = None
            processor = PayrollCSVProcessor(db, user_id=user_id)

            result = processor.process_csv_file(
                file_path=file_path,
                division_code=division_code,
                auto_create_employees=auto_create_employees,
                forced_year=forced_year,
                forced_month=forced_month,
                forced_payroll_type=forced_payroll_type,
            )

            if result.get('success'):
                self.send_json_response(result, 200)
            else:
                self.send_json_response(result, 400)

        except Exception as ex:
            self.send_json_response({'success': False, 'error': f"Erro interno: {str(ex)}"}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_payroll_statistics(self):
        """GET /api/v1/payroll/statistics"""
        db = None
        try:
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.handler.path).query)

            companies = None
            if query_params.get('companies'):
                companies = [c.strip() for c in query_params['companies'][0].split(',') if c.strip()]

            years = None
            if query_params.get('years'):
                years = [int(y.strip()) for y in query_params['years'][0].split(',') if y.strip()]

            months = None
            if query_params.get('months'):
                months = [int(m.strip()) for m in query_params['months'][0].split(',') if m.strip()]

            period_ids = None
            if query_params.get('periods'):
                period_ids = [int(p.strip()) for p in query_params['periods'][0].split(',') if p.strip()]

            department_ids = None
            if query_params.get('departments'):
                department_ids = [d.strip() for d in query_params['departments'][0].split(',') if d.strip()]

            employee_ids = None
            if query_params.get('employees'):
                employee_ids = [int(e.strip()) for e in query_params['employees'][0].split(',') if e.strip()]

            db = SessionLocal()
            result = calculate_payroll_statistics(
                db_session=db,
                companies=companies,
                years=years,
                months=months,
                period_ids=period_ids,
                department_ids=department_ids,
                employee_ids=employee_ids
            )

            self.send_json_response(result)

        except Exception as ex:
            self.send_json_response({'success': False, 'error': f"Erro ao carregar estatísticas: {str(ex)}"}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_payroll_employees(self):
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    """
                    SELECT DISTINCT
                        e.id,
                        e.unique_id,
                        e.name,
                        COALESCE(e.department, e.position, 'Não especificado') as department,
                        e.position,
                        COUNT(DISTINCT pd.period_id) as total_periods
                    FROM employees e
                    INNER JOIN payroll_data pd ON pd.employee_id = e.id
                    GROUP BY e.id, e.unique_id, e.name, e.department, e.position
                    ORDER BY e.name
                    """
                ))

                employees = [
                    {
                        'id': row[0],
                        'unique_id': row[1],
                        'name': row[2],
                        'department': row[3],
                        'position': row[4] or 'Não especificado',
                        'total_periods': row[5]
                    }
                    for row in result
                ]

                self.send_json_response({'success': True, 'employees': employees})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_divisions(self):
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    """
                    SELECT DISTINCT
                        COALESCE(e.department, 'Sem departamento cadastrado') as dept,
                        COUNT(DISTINCT e.id) as total_employees
                    FROM employees e
                    INNER JOIN payroll_data pd ON pd.employee_id = e.id
                    GROUP BY COALESCE(e.department, 'Sem departamento cadastrado')
                    ORDER BY dept
                    """
                ))

                departments = [{'name': row[0], 'total_employees': row[1]} for row in result]
                self.send_json_response({'success': True, 'departments': departments})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_companies(self):
        try:
            companies = [
                {'code': '0060', 'name': 'Empreendimentos', 'full_name': '0060 - Empreendimentos'},
                {'code': '0059', 'name': 'Infraestrutura', 'full_name': '0059 - Infraestrutura'}
            ]
            self.send_json_response({'success': True, 'companies': companies})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_years(self):
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT DISTINCT year FROM payroll_periods WHERE year IS NOT NULL ORDER BY year DESC"
                ))
                self.send_json_response({'success': True, 'years': [row[0] for row in result]})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_months(self):
        from sqlalchemy import text
        try:
            month_names = {
                1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
                5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
                9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
            }
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT DISTINCT month FROM payroll_periods WHERE month IS NOT NULL ORDER BY month"
                ))
                months = [{'number': row[0], 'name': month_names.get(row[0], f'Mês {row[0]}')} for row in result]
                self.send_json_response({'success': True, 'months': months})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_processing_history(self):
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    """
                    SELECT id, period_id, filename, status, total_rows, processed_rows, error_rows, processing_time, created_at
                    FROM payroll_processing_logs
                    ORDER BY created_at DESC LIMIT 50
                    """
                ))
                rows = [dict(row._mapping) for row in result]
                self.send_json_response({'success': True, 'history': rows})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_statistics_debug(self):
        from sqlalchemy import text
        try:
            parsed = urllib.parse.urlparse(self.handler.path)
            params = urllib.parse.parse_qs(parsed.query)
            # Keep the original behavior from monolith: return employee names and status filtered
            where = ''
            if params.get('periods'):
                period_ids = [int(pid.strip()) for pid in params['periods'][0].split(',') if pid.strip()]
                where = f"WHERE pd.period_id IN ({','.join(str(pid) for pid in period_ids)})"
            query = text(f"""
                SELECT DISTINCT e.id, e.name, e.unique_id, pd.additional_data->>'Status' as status
                FROM payroll_data pd
                INNER JOIN employees e ON e.id = pd.employee_id
                {where}
                ORDER BY e.name
            """)
            with engine.connect() as conn:
                result = conn.execute(query)
                rows = [dict(row._mapping) for row in result]
                self.send_json_response({'success': True, 'employees': rows})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payroll_statistics_filtered(self):
        from sqlalchemy import text
        try:
            parsed = urllib.parse.urlparse(self.handler.path)
            params = urllib.parse.parse_qs(parsed.query)
            period_ids = [int(x) for x in params.get('periods', [''])[0].split(',') if x.strip()]
            divisions = [x.strip() for x in params.get('divisions', [''])[0].split(',') if x.strip()]
            employee_ids = [int(x) for x in params.get('employees', [''])[0].split(',') if x.strip()]

            where_clauses = []
            qparams = {}
            if period_ids:
                where_clauses.append('pd.period_id IN :period_ids')
                qparams['period_ids'] = tuple(period_ids)
            if divisions:
                where_clauses.append('COALESCE(e.department, e.position, \'Não especificado\') IN :divisions')
                qparams['divisions'] = tuple(divisions)
            if employee_ids:
                where_clauses.append('e.id IN :employee_ids')
                qparams['employee_ids'] = tuple(employee_ids)

            where_sql = ' AND '.join(where_clauses)
            if where_sql:
                where_sql = 'WHERE ' + where_sql

            stats_query = text(f"""
                SELECT
                  COUNT(DISTINCT e.id) as total_employees,
                  COUNT(DISTINCT pd.period_id) as total_periods,
                  COALESCE(SUM((pd.additional_data->>'Valor Salário')::numeric), 0) as total_valor_salario,
                  -- There are many aggregates here to mirror legacy behavior
                  -- For simplicity, we reuse existing `calculate_payroll_statistics` with filters.
                  0 as placeholder
                FROM payroll_data pd
                INNER JOIN employees e ON e.id = pd.employee_id
                {where_sql}
            """)

            with engine.connect() as conn:
                result = conn.execute(stats_query, qparams).fetchone()
                customers = {
                    'total_employees': int(result[0] if result and result[0] is not None else 0),
                    'total_periods': int(result[1] if result and result[1] is not None else 0),
                    'total_valor_salario': float(result[2] if result and result[2] is not None else 0),
                }
                self.send_json_response({'success': True, 'stats': customers})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_payrolls_processed(self):
        try:
            parsed = urllib.parse.urlparse(self.handler.path)
            params = urllib.parse.parse_qs(parsed.query)
            month_filter = (params.get('month', [''])[0] or '').strip().lower()
            channel = (params.get('channel', ['whatsapp'])[0] or '').strip().lower()
            if channel not in {'whatsapp', 'email'}:
                self.send_json_response({'success': False, 'error': 'Canal de envio inválido'}, 400)
                return
            resend_employee_id = params.get('resend_employee_id', [None])[0]
            if resend_employee_id is not None:
                try:
                    resend_employee_id = int(resend_employee_id)
                except (TypeError, ValueError):
                    self.send_json_response({'success': False, 'error': 'Colaborador para reenvio inválido'}, 400)
                    return

            files = self._collect_processed_files(include_sent=resend_employee_id is not None)

            successful_deliveries = set()
            db = SessionLocal()
            try:
                deliveries = db.query(PayrollSend.employee_id, PayrollSend.file_path).filter(
                    PayrollSend.status.in_(['accepted', 'sent'])
                ).all()
                successful_deliveries = {
                    (delivery.employee_id, os.path.basename(delivery.file_path or '').lower())
                    for delivery in deliveries
                }
            finally:
                db.close()

            visible_files = []
            already_sent = 0
            for file_info in files:
                employee = file_info.get('associated_employee')
                if resend_employee_id is not None:
                    if not employee or employee.get('id') != resend_employee_id:
                        continue
                elif employee and (employee.get('id'), file_info.get('filename', '').lower()) in successful_deliveries:
                    already_sent += 1
                    continue
                visible_files.append(file_info)
            files = visible_files

            if month_filter:
                files = [f for f in files if str(f.get('month_year', '')).lower() == month_filter]

            total = len(files)
            orphan = sum(1 for f in files if f.get('is_orphan'))
            ready = sum(1 for f in files if f.get('can_send'))
            email_ready = sum(1 for f in files if f.get('can_send_email'))
            associated = sum(1 for f in files if f.get('associated_employee'))

            self.send_json_response({
                'success': True,
                'files': files,
                'statistics': {
                    'total': total,
                    'orphan': orphan,
                    'ready': ready,
                    'email_ready': email_ready,
                    'already_sent': already_sent,
                    'associated': associated,
                },
            })
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_list_payroll_periods(self):
        try:
            inventory = {}
            for base_dir in self._get_processed_base_dirs() + self._get_sent_base_dirs():
                for root, _, filenames in os.walk(base_dir):
                    for filename in filenames:
                        parsed_period = self._parse_period_from_filename(filename)
                        if not parsed_period:
                            continue
                        inventory.setdefault(parsed_period, set()).add(filename)

            periods = [
                {
                    'folder': f'{self.PAYROLL_TYPE_DIRS[payroll_type]}_{month:02d}_{year}',
                    'file_count': len(filenames),
                    'payroll_type': payroll_type,
                    'month': month,
                    'year': year,
                }
                for (payroll_type, month, year), filenames in inventory.items()
            ]

            periods.sort(key=lambda p: (p['year'], p['month']), reverse=True)
            self.send_json_response({'success': True, 'periods': periods})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_list_payroll_data_periods(self):
        db = None
        try:
            db = SessionLocal()
            periods = (
                db.query(PayrollPeriod)
                .order_by(PayrollPeriod.year.desc(), PayrollPeriod.month.desc(), PayrollPeriod.id.desc())
                .all()
            )

            data = []
            for period in periods:
                total_records = db.query(PayrollData).filter(PayrollData.period_id == period.id).count()
                company_label = 'Empreendimentos' if period.company == '0060' else 'Infraestrutura' if period.company == '0059' else period.company
                data.append(
                    {
                        'id': period.id,
                        'period_name': period.period_name,
                        'year': period.year,
                        'month': period.month,
                        'company': period.company,
                        'company_name': company_label,
                        'is_closed': bool(period.is_closed),
                        'total_records': total_records,
                    }
                )

            self.send_json_response({'success': True, 'periods': data})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)
        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_delete_payroll_period(self, period_id: int):
        db = None
        try:
            db = SessionLocal()
            period = db.query(PayrollPeriod).filter(PayrollPeriod.id == period_id).first()
            if not period:
                self.send_json_response({'success': False, 'error': 'Período não encontrado'}, 404)
                return

            db.query(PayrollData).filter(PayrollData.period_id == period_id).delete(synchronize_session=False)
            db.query(PayrollProcessingLog).filter(PayrollProcessingLog.period_id == period_id).delete(synchronize_session=False)
            db.delete(period)
            db.commit()

            self.send_json_response({'success': True, 'message': f'Período "{period.period_name}" removido com sucesso'})
        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'success': False, 'error': str(ex)}, 500)
        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    # Stand-in methods for exports/bulk-send/delete
    def handle_export_payroll_batch(self):
        try:
            data = self.get_request_data()
            payroll_type = str(data.get('payrollType') or '').strip()
            month = data.get('month')
            year = data.get('year')

            if payroll_type not in self.PAYROLL_TYPE_DIRS:
                self.send_json_response({'success': False, 'error': 'Tipo de holerite inválido'}, 400)
                return

            try:
                month = int(month)
                year = int(year)
            except Exception:
                self.send_json_response({'success': False, 'error': 'month/year inválidos'}, 400)
                return

            files_by_name = {}
            for base_dir in self._get_sent_base_dirs() + self._get_processed_base_dirs():
                for root, _, filenames in os.walk(base_dir):
                    for pdf_name in filenames:
                        if self._parse_period_from_filename(pdf_name) != (payroll_type, month, year):
                            continue
                        files_by_name[pdf_name] = os.path.join(root, pdf_name)

            if not files_by_name:
                self.send_json_response({'success': False, 'error': 'Nenhum PDF encontrado para o período informado'}, 404)
                return

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for pdf_name, full_path in sorted(files_by_name.items()):
                    if not os.path.exists(full_path):
                        full_path = self._resolve_payroll_file(pdf_name)
                    if not full_path:
                        raise FileNotFoundError(f'Arquivo mudou de local durante a exportação: {pdf_name}')
                    zip_file.write(full_path, arcname=pdf_name)

            zip_bytes = zip_buffer.getvalue()
            zip_name = f"Holerites_{payroll_type}_{month:02d}_{year}.zip"
            self.send_binary_response(zip_bytes, 'application/zip', zip_name)
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_bulk_send_payrolls(self):
        try:
            data = self.get_request_data()
            selected_files = data.get('selected_files') or []
            message_templates = data.get('message_templates') or []

            if not selected_files:
                self.send_json_response({'success': False, 'detail': 'Nenhum arquivo selecionado para envio'}, 400)
                return

            force_resend = bool(data.get('force_resend', False))
            resolved_files = []
            for file_info in selected_files:
                filename = os.path.basename(str(file_info.get('filename') or ''))
                filepath = self._resolve_payroll_file(filename)
                if filepath:
                    resolved_files.append({**file_info, 'filename': filename, 'filepath': filepath})

            if not resolved_files:
                self.send_json_response({'success': False, 'detail': 'Nenhum arquivo selecionado foi encontrado'}, 400)
                return

            user = self.handler.get_authenticated_user()
            user_id = user.id if user else 0

            computer_name = self.handler.headers.get('X-Computer-Name')
            ip_address = self.handler.client_address[0] if self.handler.client_address else None

            job = start_payroll_send_job(
                user_id=user_id,
                selected_files=resolved_files,
                message_templates=message_templates,
                computer_name=computer_name,
                ip_address=ip_address,
                force_resend=force_resend,
            )

            self.send_json_response(job, 202)
        except Exception as ex:
            self.send_json_response({'success': False, 'detail': str(ex)}, 500)

    def handle_bulk_send_status(self, job_id: str):
        try:
            job = get_payroll_send_job(job_id) or get_email_job(job_id)
            if not job:
                self.send_json_response({'success': False, 'detail': 'Job não encontrado'}, 404)
                return

            self.send_json_response(job, 200)
        except Exception as ex:
            self.send_json_response({'success': False, 'detail': str(ex)}, 500)

    def handle_email_status(self):
        user = self.handler.get_authenticated_user()
        if not user:
            self.send_json_response({'detail': 'Token de acesso necessário'}, 401)
            return
        try:
            from app.core.config import settings
            self.send_json_response({
                'configured': settings.has_smtp_configured(),
                'security': settings.get_smtp_security(),
                'from': settings.SMTP_FROM,
                'host_configured': bool(settings.SMTP_HOST),
            })
        except ValueError as ex:
            self.send_json_response({'configured': False, 'error': str(ex)}, 500)

    def handle_test_email_connection(self):
        user = self.handler.get_authenticated_user()
        if not user:
            self.send_json_response({'detail': 'Token de acesso necessário'}, 401)
            return
        from app.services.email_service import EmailService
        result = EmailService().test_connection()
        self.send_json_response(result.to_dict(), 200 if result.success else 503)

    def handle_bulk_send_payrolls_email(self):
        user = self.handler.get_authenticated_user()
        if not user:
            self.send_json_response({'detail': 'Token de acesso necessário'}, 401)
            return
        data = self.get_request_data()
        selected_files = data.get('selected_files') or []
        subject_template = str(data.get('subject_template') or '').strip()
        body_template = str(data.get('body_template') or '').strip()
        if not selected_files:
            self.send_json_response({'error': 'Nenhum arquivo selecionado'}, 400)
            return
        if len(selected_files) > 1000 or len(subject_template) > 200 or len(body_template) > 10000:
            self.send_json_response({'error': 'Lote ou modelo de mensagem excede o limite permitido'}, 400)
            return
        try:
            job = start_email_job(
                selected_files=selected_files,
                subject_template=subject_template,
                body_template=body_template,
                user_id=user.id,
                force_resend=bool(data.get('force_resend', False)),
                resolve_file=self._resolve_payroll_file,
            )
            self.send_json_response(job, 202)
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao iniciar lote de e-mail: {str(ex)}'}, 500)

    def handle_send_payroll_individual(self):
        try:
            data = self.get_request_data()
            filename = str(data.get('filename') or '').strip()
            phone = str(data.get('phone') or data.get('phone_number') or '').strip()
            message = str(data.get('message') or '').strip()

            if not filename:
                self.send_json_response({'success': False, 'detail': 'filename é obrigatório'}, 400)
                return

            if not phone:
                self.send_json_response({'success': False, 'detail': 'phone é obrigatório'}, 400)
                return

            target_file = None
            for file_info in self._collect_processed_files():
                if file_info.get('filename') == filename:
                    target_file = file_info
                    break

            if not target_file:
                self.send_json_response({'success': False, 'detail': 'Arquivo não encontrado'}, 404)
                return

            phone_ok, formatted_phone, phone_error = PhoneValidator.validate_and_format(phone)
            if not phone_ok or not formatted_phone:
                self.send_json_response({'success': False, 'detail': f'Telefone inválido: {phone_error or "formato_invalido"}'}, 400)
                return

            manager = get_instance_manager()
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                instance_name = loop.run_until_complete(manager.get_next_available_instance())
                if not instance_name:
                    self.send_json_response({'success': False, 'detail': 'Nenhuma instância WhatsApp online'}, 503)
                    return

                service = EvolutionAPIService(instance_name=instance_name)
                result = loop.run_until_complete(
                    service.send_communication_message(
                        phone=formatted_phone,
                        message_text=message or None,
                        file_path=target_file.get('filepath'),
                    )
                )
            finally:
                loop.close()

            if result.get('success'):
                try:
                    original_path = target_file.get('filepath')
                    moved_path = _move_file_to_sent(original_path, target_file.get('month_year') or 'desconhecido')
                    self.send_json_response({'success': True, 'message': 'Holerite enviado com sucesso', 'sent_path': moved_path})
                    return
                except Exception as move_ex:
                    self.send_json_response({'success': True, 'message': f'Holerite enviado, mas não foi possível mover arquivo: {str(move_ex)}'})
                    return
            else:
                self.send_json_response({'success': False, 'detail': result.get('message', 'Erro no envio')}, 500)
        except Exception as ex:
            self.send_json_response({'success': False, 'detail': str(ex)}, 500)

    def handle_delete_payroll_file(self):
        try:
            data = self.get_request_data()
            filename = str(data.get('filename') or '').strip()
            if not filename:
                self.send_json_response({'success': False, 'error': 'filename é obrigatório'}, 400)
                return

            if '/' in filename or '\\' in filename or filename in ('.', '..'):
                self.send_json_response({'success': False, 'error': 'filename inválido'}, 400)
                return

            deleted = False
            for base_dir in self._get_processed_base_dirs():
                for root, _, files in os.walk(base_dir):
                    if filename in files:
                        file_path = os.path.join(root, filename)
                        try:
                            os.remove(file_path)
                            deleted = True
                        except Exception:
                            pass

            if not deleted:
                self.send_json_response({'success': False, 'error': 'Arquivo não encontrado'}, 404)
                return

            self.send_json_response({'success': True, 'message': 'Arquivo removido com sucesso'})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)
