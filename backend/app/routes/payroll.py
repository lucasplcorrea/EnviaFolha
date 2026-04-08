"""Modular route handlers for payroll upload and statistics."""

import os
import asyncio
import urllib.parse
import zipfile
import re
import PyPDF2
from io import BytesIO
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


class PayrollRouter(BaseRouter):
    """Router para endpoints de folha de pagamento."""

    PAYROLL_TYPE_DIRS = {
        '11': 'Mensal',
        '31': 'Adiantamento_13',
        '32': '13_Integral',
        '91': 'Adiantamento_Salarial',
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
        ])

        base_dirs = []
        for candidate in candidates:
            abs_path = os.path.abspath(candidate)
            if abs_path not in base_dirs and os.path.isdir(abs_path):
                base_dirs.append(abs_path)

        return base_dirs

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

    def _collect_processed_files(self):
        employees_payload = load_employees_data(include_inactive=True)
        employees = employees_payload.get('employees', [])

        employees_by_uid = {}
        for emp in employees:
            normalized_uid = self._normalize_unique_id(emp.get('unique_id'))
            if normalized_uid:
                employees_by_uid.setdefault(normalized_uid, []).append(emp)

        files = []
        for base_dir in self._get_processed_base_dirs():
            for root, _, filenames in os.walk(base_dir):
                folder_name = os.path.basename(root)
                month_year = self._build_month_year_label(folder_name)

                for filename in filenames:
                    if not filename.lower().endswith('.pdf'):
                        continue

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

                    files.append({
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
                    })

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
            # Ainda usa implementacao consolidada do legado
            self.handler.handle_period_comparison()
        elif path == '/api/v1/payroll/processing-history':
            self.handle_payroll_processing_history()
        elif path.startswith('/api/v1/payroll/statistics-debug'):
            self.handle_payroll_statistics_debug()
        elif path.startswith('/api/v1/payroll/statistics-filtered'):
            self.handle_payroll_statistics_filtered()
        elif path == '/api/v1/payrolls/processed':
            self.handle_payrolls_processed()
        elif path.startswith('/api/v1/payrolls/bulk-send/') and path.endswith('/status'):
            job_id = path.split('/')[-2]
            self.handle_bulk_send_status(job_id)
        else:
            self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/payroll/upload-csv' or path == '/api/v1/payroll-data/upload-csv':
            self.handle_upload_payroll_csv()
        elif path == '/api/v1/payroll/process' or path == '/api/v1/payrolls/process':
            self.handle_process_payroll_file()
        elif path == '/api/v1/payrolls/export-batch':
            self.handle_export_payroll_batch()
        elif path == '/api/v1/payrolls/bulk-send':
            self.handle_bulk_send_payrolls()
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

            files = self._collect_processed_files()
            if month_filter:
                files = [f for f in files if str(f.get('month_year', '')).lower() == month_filter]

            total = len(files)
            orphan = sum(1 for f in files if f.get('is_orphan'))
            ready = sum(1 for f in files if f.get('can_send'))
            associated = sum(1 for f in files if f.get('associated_employee'))

            self.send_json_response({
                'success': True,
                'files': files,
                'statistics': {
                    'total': total,
                    'orphan': orphan,
                    'ready': ready,
                    'associated': associated,
                },
            })
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_list_payroll_periods(self):
        try:
            periods = []
            seen = set()

            for base_dir in self._get_processed_base_dirs():
                for folder in os.listdir(base_dir):
                    folder_path = os.path.join(base_dir, folder)
                    if not os.path.isdir(folder_path):
                        continue

                    parsed_period = self._parse_period_from_folder(folder)
                    if not parsed_period:
                        continue

                    payroll_type, month, year = parsed_period
                    key = (payroll_type, month, year)
                    if key in seen:
                        continue

                    file_count = sum(
                        1
                        for item in os.listdir(folder_path)
                        if item.lower().endswith('.pdf') and os.path.isfile(os.path.join(folder_path, item))
                    )

                    periods.append({
                        'folder': folder,
                        'file_count': file_count,
                        'payroll_type': payroll_type,
                        'month': month,
                        'year': year,
                    })
                    seen.add(key)

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

            folder_name = f"{self.PAYROLL_TYPE_DIRS[payroll_type]}_{month:02d}_{year}"
            source_dir = None
            for base_dir in self._get_processed_base_dirs():
                candidate = os.path.join(base_dir, folder_name)
                if os.path.isdir(candidate):
                    source_dir = candidate
                    break

            if not source_dir:
                self.send_json_response({'success': False, 'error': f'Pasta de período não encontrada: {folder_name}'}, 404)
                return

            pdf_files = [
                item
                for item in os.listdir(source_dir)
                if item.lower().endswith('.pdf') and os.path.isfile(os.path.join(source_dir, item))
            ]
            if not pdf_files:
                self.send_json_response({'success': False, 'error': 'Nenhum PDF encontrado para o período informado'}, 404)
                return

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for pdf_name in sorted(pdf_files):
                    full_path = os.path.join(source_dir, pdf_name)
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

            user = self.handler.get_authenticated_user()
            user_id = user.id if user else 0

            computer_name = self.handler.headers.get('X-Computer-Name')
            ip_address = self.handler.client_address[0] if self.handler.client_address else None

            job = start_payroll_send_job(
                user_id=user_id,
                selected_files=selected_files,
                message_templates=message_templates,
                computer_name=computer_name,
                ip_address=ip_address,
            )

            self.send_json_response(job, 202)
        except Exception as ex:
            self.send_json_response({'success': False, 'detail': str(ex)}, 500)

    def handle_bulk_send_status(self, job_id: str):
        try:
            job = get_payroll_send_job(job_id)
            if not job:
                self.send_json_response({'success': False, 'detail': 'Job não encontrado'}, 404)
                return

            self.send_json_response(job, 200)
        except Exception as ex:
            self.send_json_response({'success': False, 'detail': str(ex)}, 500)

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
