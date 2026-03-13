"""Queue and WhatsApp send workflow for tax statements."""

from __future__ import annotations

import asyncio
import json
import os
import random
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.models.base import SessionLocal
from app.models.send_queue import SendQueue, SendQueueItem
from app.models.system_log import LogCategory, LogLevel, SystemLog
from app.models.tax_statement import TaxStatement
from app.services.evolution_api import EvolutionAPIService
from app.services.instance_manager import get_instance_manager
from app.services.phone_validator import PhoneValidator
from app.services.queue_manager import QueueManagerService


_tax_send_jobs: Dict[str, Dict] = {}
_tax_send_jobs_lock = threading.Lock()


def _build_default_message(employee_name: Optional[str], ref_year: int) -> str:
    name = employee_name or "Colaborador"
    return (
        f"Olá {name}, segue seu Informe de Rendimentos referente ao ano-calendário {ref_year}. "
        "A senha para abrir o PDF são os 4 primeiros dígitos do seu CPF. "
        "Esta é uma mensagem automática do RH."
    )


def _render_message_template(template: Optional[str], employee_name: Optional[str], ref_year: int) -> str:
    if not template:
        return _build_default_message(employee_name, ref_year)

    full_name = employee_name or "Colaborador"
    first_name = full_name.split()[0] if full_name else "Colaborador"

    return (
        template.replace("{nome}", full_name)
        .replace("{primeiro_nome}", first_name)
        .replace("{ano}", str(ref_year))
        .replace("{ano_calendario}", str(ref_year))
    )


def _run_send_loop(queue_id: str, statement_ids: List[int], templates: List[str]) -> None:
    with _tax_send_jobs_lock:
        job = _tax_send_jobs.get(queue_id)
        if job:
            job["status"] = "processing"
            job["started_at"] = datetime.now().isoformat()

    db = SessionLocal()
    try:
        queue_service = QueueManagerService(db)
        instance_manager = get_instance_manager()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for idx, statement_id in enumerate(statement_ids):
            # Renova sessão por item para evitar uso de conexão stale em loops longos.
            db.close()
            db = SessionLocal()
            queue_service = QueueManagerService(db)

            queue = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
            if queue and queue.status == "cancelled":
                with _tax_send_jobs_lock:
                    job = _tax_send_jobs.get(queue_id)
                    if job:
                        job["status"] = "cancelled"
                        job["finished_at"] = datetime.now().isoformat()
                return

            while queue and queue.status == "paused":
                time.sleep(5)
                queue = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
                if queue and queue.status == "cancelled":
                    with _tax_send_jobs_lock:
                        job = _tax_send_jobs.get(queue_id)
                        if job:
                            job["status"] = "cancelled"
                            job["finished_at"] = datetime.now().isoformat()
                    return

            if idx > 0:
                delay_seconds = random.uniform(120, 180)
                time.sleep(delay_seconds)

                if idx % 20 == 0:
                    long_pause_seconds = random.uniform(600, 900)
                    time.sleep(long_pause_seconds)

            statement = db.query(TaxStatement).filter(TaxStatement.id == statement_id).first()
            if not statement:
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                continue

            # Access queue item by metadata statement_id without changing current schema.
            queue_item = None
            for qi in db.query(SendQueueItem).filter(SendQueueItem.queue_id == queue_id).all():
                metadata = qi.item_metadata or {}
                if metadata.get("statement_id") == statement_id:
                    queue_item = qi
                    break

            if not statement.employee or not statement.employee.phone:
                statement.status = "failed"
                statement.processing_error = "telefone_nao_cadastrado"
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "failed", "Telefone não cadastrado")

                db.add(
                    SystemLog(
                        level=LogLevel.ERROR,
                        category=LogCategory.PAYROLL,
                        message=f"Falha no envio de IR: telefone ausente ({statement.unique_id})",
                        details=json.dumps(
                            {
                                "queue_id": queue_id,
                                "statement_id": statement.id,
                                "employee_id": statement.employee_id,
                                "reason": "telefone_nao_cadastrado",
                            },
                            ensure_ascii=False,
                        ),
                        entity_type="TaxStatement",
                        entity_id=str(statement.id),
                    )
                )
                db.commit()
                continue

            phone_ok, formatted_phone, phone_error = PhoneValidator.validate_and_format(statement.employee.phone)
            if not phone_ok or not formatted_phone:
                statement.status = "failed"
                statement.processing_error = f"telefone_invalido: {phone_error or 'formato_invalido'}"
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "failed", f"Telefone inválido: {phone_error or 'formato_invalido'}")

                db.add(
                    SystemLog(
                        level=LogLevel.ERROR,
                        category=LogCategory.PAYROLL,
                        message=f"Falha no envio de IR: telefone inválido ({statement.unique_id})",
                        details=json.dumps(
                            {
                                "queue_id": queue_id,
                                "statement_id": statement.id,
                                "employee_id": statement.employee_id,
                                "phone_original": statement.employee.phone,
                                "phone_error": phone_error,
                                "reason": "telefone_invalido",
                            },
                            ensure_ascii=False,
                        ),
                        entity_type="TaxStatement",
                        entity_id=str(statement.id),
                    )
                )
                db.commit()
                continue

            if not statement.file_path:
                statement.status = "failed"
                statement.processing_error = "arquivo_nao_informado"
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "failed", "Arquivo não informado")
                continue

            if not os.path.exists(statement.file_path):
                statement.status = "failed"
                statement.processing_error = "arquivo_nao_encontrado"
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "failed", "Arquivo não encontrado")
                continue

            next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
            if not next_instance:
                statement.status = "failed"
                statement.processing_error = "nenhuma_instancia_online"
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "failed", "Nenhuma instância WhatsApp online")

                db.add(
                    SystemLog(
                        level=LogLevel.ERROR,
                        category=LogCategory.WHATSAPP,
                        message=f"Falha no envio de IR: nenhuma instância online ({statement.unique_id})",
                        details=json.dumps(
                            {
                                "queue_id": queue_id,
                                "statement_id": statement.id,
                                "reason": "nenhuma_instancia_online",
                            },
                            ensure_ascii=False,
                        ),
                        entity_type="TaxStatement",
                        entity_id=str(statement.id),
                    )
                )
                db.commit()
                continue

            service = EvolutionAPIService(instance_name=next_instance)
            selected_template = random.choice(templates) if templates else None
            message = _render_message_template(selected_template, statement.employee_name, statement.ref_year)
            result = loop.run_until_complete(
                service.send_communication_message(
                    phone=formatted_phone,
                    message_text=message,
                    file_path=statement.file_path,
                )
            )
            instance_manager.register_send(next_instance)

            if result.get("success"):
                statement.status = "sent"
                statement.sent_at = datetime.now()
                statement.whatsapp_instance = next_instance
                statement.whatsapp_status = "sent"
                statement.whatsapp_message_id = result.get("message_id")
                statement.processing_error = None
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, successful=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "sent")

                db.add(
                    SystemLog(
                        level=LogLevel.INFO,
                        category=LogCategory.PAYROLL,
                        message=f"IR enviado com sucesso ({statement.unique_id})",
                        details=json.dumps(
                            {
                                "queue_id": queue_id,
                                "statement_id": statement.id,
                                "employee_id": statement.employee_id,
                                "phone": formatted_phone,
                                "instance": next_instance,
                                "template_used": bool(selected_template),
                            },
                            ensure_ascii=False,
                        ),
                        entity_type="TaxStatement",
                        entity_id=str(statement.id),
                    )
                )
                db.commit()
            else:
                statement.status = "failed"
                statement.whatsapp_instance = next_instance
                statement.whatsapp_status = "failed"
                statement.processing_error = result.get("message", "erro_envio")
                db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if queue_item:
                    queue_service.update_item_status(queue_item.id, "failed", result.get("message", "Erro de envio"))

                db.add(
                    SystemLog(
                        level=LogLevel.ERROR,
                        category=LogCategory.WHATSAPP,
                        message=f"Falha ao enviar IR ({statement.unique_id})",
                        details=json.dumps(
                            {
                                "queue_id": queue_id,
                                "statement_id": statement.id,
                                "employee_id": statement.employee_id,
                                "phone": formatted_phone,
                                "instance": next_instance,
                                "error": result.get("message", "erro_envio"),
                            },
                            ensure_ascii=False,
                        ),
                        entity_type="TaxStatement",
                        entity_id=str(statement.id),
                    )
                )
                db.commit()

        queue = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
        with _tax_send_jobs_lock:
            job = _tax_send_jobs.get(queue_id)
            if job:
                job["status"] = "completed"
                job["finished_at"] = datetime.now().isoformat()
                if queue:
                    job["processed_items"] = queue.processed_items
                    job["successful_items"] = queue.successful_items
                    job["failed_items"] = queue.failed_items

        loop.close()

    except Exception as exc:
        with _tax_send_jobs_lock:
            job = _tax_send_jobs.get(queue_id)
            if job:
                job["status"] = "failed"
                job["finished_at"] = datetime.now().isoformat()
                job["error"] = str(exc)
    finally:
        db.close()


def start_tax_statement_send_job(
    user_id: int,
    statement_ids: List[int],
    message_template: Optional[str],
    message_templates: Optional[List[str]],
    computer_name: Optional[str],
    ip_address: Optional[str],
) -> Dict:
    db = SessionLocal()
    try:
        queue_service = QueueManagerService(db)
        statements = (
            db.query(TaxStatement)
            .filter(TaxStatement.id.in_(statement_ids))
            .all()
        )

        valid_statements = [s for s in statements if s.status in ["processed", "failed"] and s.employee_id]
        templates = [t.strip() for t in (message_templates or []) if isinstance(t, str) and t.strip()]
        if not templates and message_template and message_template.strip():
            templates = [message_template.strip()]

        queue_id = queue_service.create_queue(
            queue_type="tax_statement",
            total_items=len(valid_statements),
            description=f"Envio de {len(valid_statements)} informes de rendimentos",
            user_id=user_id,
            file_name="tax_statements_batch",
            computer_name=computer_name,
            ip_address=ip_address,
            metadata={
                "statement_ids": statement_ids,
                "message_template": message_template,
                "message_templates": templates,
                "anti_softban": True,
            },
        )

        for statement in valid_statements:
            phone = statement.employee.phone if statement.employee else None
            queue_service.add_queue_item(
                queue_id=queue_id,
                employee_id=statement.employee_id,
                phone_number=phone or "",
                file_path=statement.file_path,
                metadata={
                    "statement_id": statement.id,
                    "statement_unique_id": statement.unique_id,
                    "ref_year": statement.ref_year,
                },
            )

        with _tax_send_jobs_lock:
            _tax_send_jobs[queue_id] = {
                "queue_id": queue_id,
                "status": "pending",
                "total_items": len(valid_statements),
                "processed_items": 0,
                "successful_items": 0,
                "failed_items": 0,
                "started_at": None,
                "finished_at": None,
                "templates_count": len(templates),
                "anti_softban": True,
            }

        if len(valid_statements) == 0:
            queue_row = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
            if queue_row:
                queue_row.status = "completed"
                queue_row.completed_at = datetime.now()
                db.commit()
            with _tax_send_jobs_lock:
                _tax_send_jobs[queue_id]["status"] = "completed"
                _tax_send_jobs[queue_id]["started_at"] = datetime.now().isoformat()
                _tax_send_jobs[queue_id]["finished_at"] = datetime.now().isoformat()

            return {
                "queue_id": queue_id,
                "accepted_items": 0,
                "requested_items": len(statement_ids),
                "status": "completed",
            }

        thread = threading.Thread(
            target=_run_send_loop,
            args=(queue_id, [s.id for s in valid_statements], templates),
            daemon=True,
        )
        thread.start()

        return {
            "queue_id": queue_id,
            "accepted_items": len(valid_statements),
            "requested_items": len(statement_ids),
            "status": "pending",
        }
    finally:
        db.close()


def get_tax_statement_send_job(queue_id: str) -> Optional[Dict]:
    with _tax_send_jobs_lock:
        return _tax_send_jobs.get(queue_id)
