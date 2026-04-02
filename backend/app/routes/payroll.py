"""Modular route handlers for payroll upload and statistics."""

import urllib.parse
from datetime import datetime
from typing import List, Optional

from app.models.base import SessionLocal, engine
from app.services.payroll_csv_processor import PayrollCSVProcessor
from app.services.payroll_statistics import calculate_payroll_statistics
from app.routes.base import BaseRouter


class PayrollRouter(BaseRouter):
    """Router para endpoints de folha de pagamento."""

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
        elif path == '/api/v1/payroll/periods' or path == '/api/v1/payrolls/periods':
            self.handle_list_payroll_periods()
        elif path == '/api/v1/payroll/processing-history':
            self.handle_payroll_processing_history()
        elif path.startswith('/api/v1/payroll/statistics-debug'):
            self.handle_payroll_statistics_debug()
        elif path.startswith('/api/v1/payroll/statistics-filtered'):
            self.handle_payroll_statistics_filtered()
        elif path == '/api/v1/payrolls/processed':
            self.handle_payrolls_processed()
        elif path == '/api/v1/payrolls/periods':
            self.handle_list_payroll_periods()
        else:
            self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/payroll/upload-csv':
            self.handle_upload_payroll_csv()
        elif path == '/api/v1/payroll/process' or path == '/api/v1/payrolls/process':
            self.handle_process_payroll_file()
        elif path == '/api/v1/payrolls/export-batch':
            self.handle_export_payroll_batch()
        elif path == '/api/v1/payrolls/bulk-send':
            self.handle_bulk_send_payrolls()
        elif path == '/api/v1/payrolls/delete-file':
            self.handle_delete_payroll_file()
        else:
            self.send_error('Endpoint não encontrado', 404)

    def handle_upload_payroll_csv(self):
        """POST /api/v1/payroll/upload-csv"""
        try:
            data = self.get_request_data()
            file_path = data.get('file_path')
            division_code = data.get('division_code', '0060')
            auto_create_employees = data.get('auto_create_employees', False)

            if not file_path:
                self.send_json_response({'success': False, 'error': "Parâmetro 'file_path' obrigatório"}, 400)
                return

            if division_code not in ['0060', '0059']:
                self.send_json_response({'success': False, 'error': "division_code deve ser '0060' (Empreendimentos) ou '0059' (Infraestrutura)"}, 400)
                return

            db = SessionLocal()
            user_id = None
            processor = PayrollCSVProcessor(db, user_id=user_id)

            result = processor.process_csv_file(
                file_path=file_path,
                division_code=division_code,
                auto_create_employees=auto_create_employees
            )

            if result.get('success'):
                self.send_json_response(result, 200)
            else:
                self.send_json_response(result, 400)

        except Exception as ex:
            self.send_json_response({'success': False, 'error': f"Erro interno: {str(ex)}"}, 500)

        finally:
            try:
                db.close()
            except Exception:
                pass

    def handle_payroll_statistics(self):
        """GET /api/v1/payroll/statistics"""
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
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                result = conn.execute(text('''
                    SELECT p.id, p.filename, p.status, p.created_at
                    FROM payroll_processing_logs p
                    ORDER BY p.created_at DESC
                    LIMIT 50
                '''))
                rows = [dict(row._mapping) for row in result]
                self.send_json_response({'success': True, 'processed_files': rows})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    def handle_list_payroll_periods(self):
        from sqlalchemy import text
        try:
            with engine.connect() as conn:
                result = conn.execute(text('''
                    SELECT id, year, month, period_name, company, is_active, is_closed
                    FROM payroll_periods
                    ORDER BY year DESC, month DESC
                    LIMIT 100
                '''))
                rows = [dict(row._mapping) for row in result]
                self.send_json_response({'success': True, 'periods': rows})
        except Exception as ex:
            self.send_json_response({'success': False, 'error': str(ex)}, 500)

    # Stand-in methods for exports/bulk-send/delete
    def handle_export_payroll_batch(self):
        self.send_json_response({'success': False, 'error': 'Não implementado' }, 501)

    def handle_bulk_send_payrolls(self):
        self.send_json_response({'success': False, 'error': 'Não implementado' }, 501)

    def handle_delete_payroll_file(self):
        self.send_json_response({'success': False, 'error': 'Não implementado' }, 501)
