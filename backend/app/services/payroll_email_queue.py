"""Background SMTP delivery for payroll files."""

from __future__ import annotations

import hashlib
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from app.core.config import settings
from app.models.base import SessionLocal
from app.models.employee import Employee
from app.models.payroll_send import PayrollSend
from app.models.send_queue import SendQueue
from app.services.email_service import DEFAULT_PAYROLL_BODY, DEFAULT_PAYROLL_SUBJECT, EmailService
from app.services.queue_manager import QueueManagerService


_jobs: Dict[str, Dict] = {}
_jobs_lock = threading.Lock()


def _update_job(job_id: str, **values) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.update(values)
        total = job.get('total_files', 0) or 0
        processed = job.get('processed_files', 0) or 0
        job['progress_percentage'] = round(processed * 100 / total, 2) if total else 100


def _increment_job(job_id: str, *, success: bool = False, skipped: bool = False) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job['processed_files'] += 1
        if success:
            job['successful_sends'] += 1
        elif skipped:
            job['skipped_sends'] += 1
        else:
            job['failed_sends'] += 1
        total = job.get('total_files', 0) or 0
        job['progress_percentage'] = round(job['processed_files'] * 100 / total, 2) if total else 100


def _run_job(
    job_id: str,
    selected_files: List[Dict],
    subject_template: str,
    body_template: str,
    user_id: int,
    force_resend: bool,
    resolve_file: Callable[[str], Optional[str]],
) -> None:
    db = SessionLocal()
    queue_service = QueueManagerService(db)
    _update_job(job_id, status='running', started_at=datetime.now().isoformat())

    try:
        queue_row = db.query(SendQueue).filter(SendQueue.queue_id == job_id).first()
        if queue_row:
            queue_row.status = 'processing'
            db.commit()

        email_service = EmailService()
        retries = max(1, settings.SMTP_MAX_RETRIES)

        for index, file_info in enumerate(selected_files):
            filename = os.path.basename(str(file_info.get('filename') or ''))
            employee_info = file_info.get('employee') or {}
            employee_id = employee_info.get('id')
            employee = db.query(Employee).filter(Employee.id == employee_id).first() if employee_id else None
            recipient = (employee.email or '').strip() if employee else ''
            employee_name = employee.name if employee and employee.name else employee_info.get('full_name', 'Colaborador(a)')
            competence = str(file_info.get('month_year') or 'desconhecido')
            file_path = resolve_file(filename)

            _update_job(job_id, current_file=filename)
            queue_row = db.query(SendQueue).filter(SendQueue.queue_id == job_id).first()
            if queue_row and queue_row.status == 'cancelled':
                _update_job(job_id, status='cancelled', finished_at=datetime.now().isoformat())
                return
            while queue_row and queue_row.status == 'paused':
                time.sleep(2)
                db.refresh(queue_row)
                if queue_row.status == 'cancelled':
                    _update_job(job_id, status='cancelled', finished_at=datetime.now().isoformat())
                    return

            item = queue_row.items[index] if queue_row and index < len(queue_row.items) else None
            validation_error = None
            if not employee:
                validation_error = 'Colaborador não encontrado'
            elif not file_path:
                validation_error = 'Arquivo não encontrado nos diretórios autorizados'
            else:
                try:
                    recipient = email_service.validate_recipient(recipient)
                except ValueError:
                    validation_error = 'Colaborador sem e-mail válido'

            previous_delivery = None
            if employee:
                previous_delivery = db.query(PayrollSend).filter(
                    PayrollSend.employee_id == employee.id,
                    PayrollSend.status.in_(['accepted', 'sent']),
                ).all()
                previous_delivery = next(
                    (delivery for delivery in previous_delivery if os.path.basename(delivery.file_path or '').lower() == filename.lower()),
                    None,
                )

            if previous_delivery and not force_resend:
                if item:
                    queue_service.update_item_status(item.id, 'skipped', 'Arquivo já entregue anteriormente')
                queue_service.update_queue_progress(job_id, processed=1)
                _increment_job(job_id, skipped=True)
                continue

            if validation_error:
                if item:
                    queue_service.update_item_status(item.id, 'failed', validation_error)
                queue_service.update_queue_progress(job_id, processed=1, failed=1)
                with _jobs_lock:
                    _jobs[job_id]['failed_employees'].append({'employee': employee_name, 'reason': validation_error})
                _increment_job(job_id)
                continue

            key_source = f'{employee.id}|{competence}|{filename.lower()}|email|{recipient.lower()}'
            delivery_key = hashlib.sha256(key_source.encode('utf-8')).hexdigest()
            if force_resend:
                delivery_key = f'{delivery_key}:{uuid.uuid4().hex[:12]}'

            delivery = PayrollSend(
                employee_id=employee.id,
                month=competence,
                file_path=filename,
                channel='email',
                recipient=recipient,
                status='sending',
                attempt_count=0,
                idempotency_key=delivery_key,
                user_id=user_id,
                extra_data={'resend_of': previous_delivery.id} if previous_delivery else {},
            )
            db.add(delivery)
            db.commit()

            result = None
            for attempt in range(1, retries + 1):
                delivery.attempt_count = attempt
                result = email_service.send_payroll(
                    recipient=recipient,
                    employee_name=employee_name,
                    file_path=file_path,
                    competence=competence,
                    subject_template=subject_template or DEFAULT_PAYROLL_SUBJECT,
                    body_template=body_template or DEFAULT_PAYROLL_BODY,
                )
                if result.success:
                    break
                if attempt < retries:
                    time.sleep(max(0, settings.SMTP_RETRY_DELAY_SECONDS))

            if result and result.success:
                delivery.status = 'accepted'
                delivery.provider_message_id = result.message_id
                delivery.sent_at = datetime.now()
                if item:
                    queue_service.update_item_status(item.id, 'sent')
                queue_service.update_queue_progress(job_id, processed=1, successful=1)
                _increment_job(job_id, success=True)
            else:
                error = result.error_message if result else 'Falha no envio SMTP'
                delivery.status = 'failed'
                delivery.error_message = error
                if item:
                    queue_service.update_item_status(item.id, 'failed', error)
                queue_service.update_queue_progress(job_id, processed=1, failed=1)
                with _jobs_lock:
                    _jobs[job_id]['failed_employees'].append({'employee': employee_name, 'reason': error})
                _increment_job(job_id)
            db.commit()

        _update_job(job_id, status='completed', current_file='', finished_at=datetime.now().isoformat())
    except Exception as exc:
        if queue_row := db.query(SendQueue).filter(SendQueue.queue_id == job_id).first():
            queue_row.status = 'failed'
            queue_row.error_message = str(exc)
            queue_row.completed_at = datetime.now()
            db.commit()
        _update_job(job_id, status='failed', error_message=str(exc), finished_at=datetime.now().isoformat())
    finally:
        db.close()


def start_email_job(
    *,
    selected_files: List[Dict],
    subject_template: str,
    body_template: str,
    user_id: int,
    force_resend: bool,
    resolve_file: Callable[[str], Optional[str]],
) -> Dict:
    db = SessionLocal()
    try:
        queue_service = QueueManagerService(db)
        job_id = queue_service.create_queue(
            queue_type='payroll_email',
            total_items=len(selected_files),
            description=f'Envio por e-mail de {len(selected_files)} holerites',
            user_id=user_id,
            metadata={'channel': 'email', 'force_resend': force_resend},
        )
        for file_info in selected_files:
            employee = file_info.get('employee') or {}
            queue_service.add_queue_item(
                queue_id=job_id,
                employee_id=employee.get('id'),
                file_path=os.path.basename(str(file_info.get('filename') or '')),
                channel='email',
                recipient=employee.get('email'),
                metadata={'month_year': file_info.get('month_year', '')},
            )

        with _jobs_lock:
            _jobs[job_id] = {
                'job_id': job_id,
                'queue_id': job_id,
                'channel': 'email',
                'status': 'pending',
                'total_files': len(selected_files),
                'processed_files': 0,
                'successful_sends': 0,
                'failed_sends': 0,
                'skipped_sends': 0,
                'failed_employees': [],
                'current_file': '',
                'error_message': '',
                'progress_percentage': 0,
            }

        thread = threading.Thread(
            target=_run_job,
            args=(job_id, selected_files, subject_template, body_template, user_id, force_resend, resolve_file),
            daemon=True,
        )
        thread.start()
        return {'job_id': job_id, 'total_files': len(selected_files), 'status': 'pending', 'channel': 'email'}
    finally:
        db.close()


def get_email_job(job_id: str) -> Optional[Dict]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
