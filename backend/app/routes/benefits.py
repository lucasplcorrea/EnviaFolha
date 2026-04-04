"""Modular route handlers for benefits endpoints."""

import os
import re
import tempfile
import urllib.parse

from app.models.base import SessionLocal
from app.models.employee import Employee
from app.models.payroll import BenefitsData, BenefitsPeriod, BenefitsProcessingLog
from app.routes.base import BaseRouter
from app.services.benefits_xlsx_processor import BenefitsXLSXProcessor


class BenefitsRouter(BaseRouter):
    """Router para endpoints de benefícios no servidor HTTP legado."""

    def handle_get(self, path: str):
        if path == '/api/v1/benefits/periods':
            self.handle_benefits_periods_list()
            return

        if path == '/api/v1/benefits/processing-logs':
            self.handle_benefits_processing_logs()
            return

        if path.startswith('/api/v1/benefits/periods/'):
            period_id = path.split('/')[5]
            self.handle_benefits_period_detail(period_id)
            return

        parts = path.split('/')
        if len(parts) >= 6 and parts[1] == 'api' and parts[2] == 'v1' and parts[3] == 'employees' and parts[5] == 'benefits':
            self.handle_get_employee_benefits(parts[4])
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/benefits/upload-xlsx':
            self.handle_upload_benefits_file()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_delete(self, path: str):
        if path.startswith('/api/v1/benefits/periods/'):
            period_id = path.split('/')[5]
            self.handle_delete_benefits_period(period_id)
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_upload_benefits_file(self):
        """POST /api/v1/benefits/upload-xlsx (CSV/XLSX)."""
        db = None
        tmp_filepath = None
        try:
            content_type = self.handler.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_response({"error": "Content-Type deve ser multipart/form-data"}, 400)
                return

            boundary = None
            for part in content_type.split(';'):
                if 'boundary=' in part:
                    boundary = part.split('boundary=')[1].strip()
                    break

            if not boundary:
                self.send_json_response({"error": "Boundary não encontrado"}, 400)
                return

            content_length = int(self.handler.headers.get('Content-Length', 0))
            body = self.handler.rfile.read(content_length)

            boundary_bytes = f'--{boundary}'.encode()
            parts = body.split(boundary_bytes)

            file_data = None
            original_filename = None
            year = None
            month = None
            company = '0060'
            merge_mode = 'sum'
            source_label = None

            for part in parts:
                if not part or part == b'--\r\n' or part == b'--':
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

                elif b'name="company"' in part:
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        company = part[split_point + 4:].strip().decode('utf-8')

                elif b'name="merge_mode"' in part:
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        merge_mode = part[split_point + 4:].strip().decode('utf-8')

                elif b'name="source_label"' in part:
                    split_point = part.find(b'\r\n\r\n')
                    if split_point != -1:
                        source_label = part[split_point + 4:].strip().decode('utf-8')

            if not file_data:
                self.send_json_response({"error": "Arquivo não enviado"}, 400)
                return

            if not year or not month:
                self.send_json_response({"error": "Ano e mês são obrigatórios"}, 400)
                return

            if not (1 <= month <= 12):
                self.send_json_response({"error": "Mês deve estar entre 1 e 12"}, 400)
                return

            if company not in ['0060', '0059']:
                self.send_json_response({"error": "Empresa deve ser '0060' ou '0059'"}, 400)
                return

            if merge_mode not in ['sum', 'replace']:
                self.send_json_response({"error": "merge_mode deve ser 'sum' ou 'replace'"}, 400)
                return

            _, original_ext = os.path.splitext(original_filename or '')
            normalized_ext = original_ext.lower()
            if normalized_ext not in ['.xlsx', '.xlsm', '.xltx', '.xltm', '.csv', '.txt']:
                self.send_json_response({"error": "Arquivo deve ser CSV ou XLSX"}, 400)
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=normalized_ext or '.tmp') as tmp_file:
                tmp_file.write(file_data)
                tmp_filepath = tmp_file.name

            db = SessionLocal()

            user_id = None
            authenticated_user = self.handler.get_authenticated_user(db)
            if authenticated_user:
                user_id = authenticated_user.id

            processor = BenefitsXLSXProcessor(db, user_id=user_id)
            result = processor.process_xlsx_file(
                file_path=tmp_filepath,
                year=year,
                month=month,
                company=company,
                merge_mode=merge_mode,
                source_label=source_label,
                original_filename=original_filename,
            )

            if result.get('success'):
                self.send_json_response(result, 200)
            else:
                self.send_json_response(result, 400)

        except Exception as ex:
            self.send_json_response({"success": False, "error": f"Erro interno: {str(ex)}"}, 500)

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

    def handle_benefits_periods_list(self):
        db = None
        try:
            db = SessionLocal()
            periods = db.query(BenefitsPeriod).filter(
                BenefitsPeriod.is_active == True
            ).order_by(
                BenefitsPeriod.year.desc(),
                BenefitsPeriod.month.desc()
            ).all()

            periods_data = []
            for period in periods:
                company_name = 'Empreendimentos' if period.company == '0060' else 'Infraestrutura' if period.company == '0059' else period.company
                total_records = db.query(BenefitsData).filter(BenefitsData.period_id == period.id).count()

                periods_data.append({
                    'id': period.id,
                    'year': period.year,
                    'month': period.month,
                    'period_name': period.period_name,
                    'company': period.company,
                    'company_name': company_name,
                    'description': period.description,
                    'total_records': total_records,
                    'created_at': period.created_at.isoformat() if period.created_at else None,
                })

            self.send_json_response({'periods': periods_data, 'total': len(periods_data)})

        except Exception as ex:
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_benefits_period_detail(self, period_id: str):
        db = None
        try:
            db = SessionLocal()
            period = db.query(BenefitsPeriod).filter(BenefitsPeriod.id == int(period_id)).first()

            if not period:
                self.send_json_response({'error': 'Período não encontrado'}, 404)
                return

            benefits_records = db.query(BenefitsData, Employee).join(
                Employee, BenefitsData.employee_id == Employee.id
            ).filter(BenefitsData.period_id == period.id).all()

            records_data = []
            for benefit, employee in benefits_records:
                records_data.append({
                    'id': benefit.id,
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'cpf': benefit.cpf,
                    'refeicao': float(benefit.refeicao) if benefit.refeicao else 0,
                    'alimentacao': float(benefit.alimentacao) if benefit.alimentacao else 0,
                    'mobilidade': float(benefit.mobilidade) if benefit.mobilidade else 0,
                    'livre': float(benefit.livre) if benefit.livre else 0,
                    'total': benefit.get_total_benefits(),
                })

            logs = db.query(BenefitsProcessingLog).filter(
                BenefitsProcessingLog.period_id == period.id
            ).order_by(BenefitsProcessingLog.created_at.desc()).all()

            logs_data = []
            for log in logs:
                logs_data.append({
                    'id': log.id,
                    'filename': log.filename,
                    'status': log.status,
                    'total_rows': log.total_rows,
                    'processed_rows': log.processed_rows,
                    'error_rows': log.error_rows,
                    'processing_time': float(log.processing_time) if log.processing_time else 0,
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                })

            self.send_json_response({
                'period': {
                    'id': period.id,
                    'year': period.year,
                    'month': period.month,
                    'period_name': period.period_name,
                    'company': period.company,
                    'company_name': 'Empreendimentos' if period.company == '0060' else 'Infraestrutura',
                    'description': period.description,
                },
                'records': records_data,
                'logs': logs_data,
                'total_records': len(records_data),
            })

        except Exception as ex:
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_delete_benefits_period(self, period_id: str):
        db = None
        try:
            db = SessionLocal()
            period = db.query(BenefitsPeriod).filter(BenefitsPeriod.id == int(period_id)).first()
            if not period:
                self.send_json_response({'success': False, 'error': 'Período não encontrado'}, 404)
                return

            period_name = period.period_name
            db.delete(period)
            db.commit()

            self.send_json_response({'success': True, 'message': f"Período '{period_name}' deletado com sucesso"})

        except Exception as ex:
            if db is not None:
                db.rollback()
            self.send_json_response({'success': False, 'error': f'Erro interno: {str(ex)}'}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_benefits_processing_logs(self):
        db = None
        try:
            db = SessionLocal()
            logs = db.query(
                BenefitsProcessingLog,
                BenefitsPeriod.year,
                BenefitsPeriod.month,
                BenefitsPeriod.company,
                BenefitsPeriod.period_name,
            ).join(
                BenefitsPeriod,
                BenefitsProcessingLog.period_id == BenefitsPeriod.id,
            ).order_by(
                BenefitsProcessingLog.created_at.desc()
            ).limit(50).all()

            logs_data = []
            for log, year, month, company, period_name in logs:
                company_name = 'Empreendimentos' if company == '0060' else 'Infraestrutura' if company == '0059' else company
                logs_data.append({
                    'id': log.id,
                    'filename': log.filename,
                    'year': year,
                    'month': month,
                    'company': company,
                    'company_name': company_name,
                    'period_name': period_name,
                    'status': log.status,
                    'total_rows': log.total_rows,
                    'processed_rows': log.processed_rows,
                    'error_rows': log.error_rows,
                    'processing_time': float(log.processing_time) if log.processing_time else 0,
                    'processing_summary': log.processing_summary or {},
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                })

            self.send_json_response({'logs': logs_data, 'total': len(logs_data)})

        except Exception as ex:
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass

    def handle_get_employee_benefits(self, employee_id: str):
        db = None
        try:
            query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.handler.path).query)
            year = query_params.get('year', [None])[0]
            month = query_params.get('month', [None])[0]
            period_id = query_params.get('period_id', [None])[0]
            company = query_params.get('company', [None])[0]
            limit = int(query_params.get('limit', ['24'])[0] or 24)

            employee_id_str = str(employee_id).strip()
            employee_id_int = int(employee_id_str) if employee_id_str.isdigit() else None

            db = SessionLocal()

            employee_filter = (Employee.unique_id == employee_id_str)
            if employee_id_int is not None:
                employee_filter = (Employee.id == employee_id_int) | employee_filter

            employee = db.query(Employee).filter(employee_filter).first()
            if not employee:
                self.send_json_response({'error': 'Funcionário não encontrado'}, 404)
                return

            benefits_query = db.query(BenefitsData, BenefitsPeriod).outerjoin(
                BenefitsPeriod, BenefitsPeriod.id == BenefitsData.period_id
            ).filter(BenefitsData.employee_id == employee.id)

            if year:
                benefits_query = benefits_query.filter(BenefitsPeriod.year == int(year))
            if month:
                benefits_query = benefits_query.filter(BenefitsPeriod.month == int(month))
            if period_id:
                benefits_query = benefits_query.filter(BenefitsData.period_id == int(period_id))
            if company and company != 'all':
                benefits_query = benefits_query.filter(BenefitsPeriod.company == company)

            records = benefits_query.order_by(
                BenefitsPeriod.year.desc(),
                BenefitsPeriod.month.desc(),
                BenefitsData.id.desc(),
            ).limit(max(1, min(limit, 120))).all()

            benefits = []
            total_refeicao = 0.0
            total_alimentacao = 0.0
            total_mobilidade = 0.0
            total_livre = 0.0

            for benefit, period in records:
                refeicao = float(benefit.refeicao or 0)
                alimentacao = float(benefit.alimentacao or 0)
                mobilidade = float(benefit.mobilidade or 0)
                livre = float(benefit.livre or 0)
                total = refeicao + alimentacao + mobilidade + livre

                period_year = period.year if period else None
                period_month = period.month if period else None
                period_name = period.period_name if period else f"Período {benefit.period_id}"
                period_company = period.company if period else None

                total_refeicao += refeicao
                total_alimentacao += alimentacao
                total_mobilidade += mobilidade
                total_livre += livre

                benefits.append({
                    'id': benefit.id,
                    'period': {
                        'id': benefit.period_id,
                        'year': period_year,
                        'month': period_month,
                        'name': period_name,
                        'company': period_company,
                    },
                    'cpf': benefit.cpf,
                    'refeicao': refeicao,
                    'alimentacao': alimentacao,
                    'mobilidade': mobilidade,
                    'livre': livre,
                    'total': total,
                    'upload_filename': benefit.upload_filename,
                    'updated_at': benefit.updated_at.isoformat() if getattr(benefit, 'updated_at', None) else None,
                })

            response = {
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
                'total_records': len(benefits),
                'summary': {
                    'total_refeicao': total_refeicao,
                    'total_alimentacao': total_alimentacao,
                    'total_mobilidade': total_mobilidade,
                    'total_livre': total_livre,
                    'total_benefits': total_refeicao + total_alimentacao + total_mobilidade + total_livre,
                },
                'benefits': benefits,
            }

            self.send_json_response(response, 200)

        except Exception as ex:
            self.send_json_response({'error': f'Erro interno: {str(ex)}'}, 500)

        finally:
            try:
                if db is not None:
                    db.close()
            except Exception:
                pass
