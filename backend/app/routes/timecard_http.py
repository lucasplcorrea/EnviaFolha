"""HTTP router for timecard endpoints used by the React frontend."""

import os
import re
import tempfile
from decimal import Decimal
from sqlalchemy import func

from app.routes.base import BaseRouter
from app.services.runtime_compat import SessionLocal
from app.models.timecard import TimecardData, TimecardPeriod, TimecardProcessingLog
from app.services.timecard_xlsx_processor import TimecardXLSXProcessor


class TimecardRouter(BaseRouter):
    def handle_get(self, path: str):
        if path == '/api/v1/timecard/periods':
            self.handle_timecard_periods_list()
            return

        if path == '/api/v1/timecard/processing-logs':
            self.handle_timecard_processing_logs()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/timecard/upload-xlsx':
            self.handle_upload_timecard_xlsx()
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
            if normalized_ext not in ['.xlsx', '.xls']:
                self.send_json_response({'error': 'Arquivo deve ser XLSX ou XLS'}, 400)
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
