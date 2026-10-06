"""Queue and WhatsApp send workflow for tax statements."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
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
logger = logging.getLogger(__name__)


def _queue_log(queue_id: str, message: str) -> None:
    """Emite log operacional da fila em formato legivel no stdout e logger."""
    text = f"[IR-QUEUE {queue_id}] {message}"
    print(text)
    logger.info(text)


def _update_runtime_job(
    queue_id: str,
    *,
    processed_inc: int = 0,
    successful_inc: int = 0,
    failed_inc: int = 0,
    status: Optional[str] = None,
    current_item: Optional[str] = None,
    next_delay_seconds: Optional[float] = None,
) -> None:
    with _tax_send_jobs_lock:
        job = _tax_send_jobs.get(queue_id)
        if not job:
            return

        if processed_inc:
            job["processed_items"] = job.get("processed_items", 0) + processed_inc
        if successful_inc:
            job["successful_items"] = job.get("successful_items", 0) + successful_inc
        if failed_inc:
            job["failed_items"] = job.get("failed_items", 0) + failed_inc
        if status:
            job["status"] = status
        if current_item is not None:
            job["current_item"] = current_item
        if next_delay_seconds is not None:
            job["next_delay_seconds"] = round(next_delay_seconds, 1)


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
    _queue_log(queue_id, f"Fila iniciada com {len(statement_ids)} item(ns)")

    db = SessionLocal()
    try:
        instance_manager = get_instance_manager()

        bootstrap_loop = asyncio.new_event_loop()
        online_status = bootstrap_loop.run_until_complete(instance_manager.check_all_instances_status())
        bootstrap_loop.close()

        online_instances = [instance for instance, is_online in online_status.items() if is_online]
        if not online_instances:
            _queue_log(queue_id, "Nenhuma instância WhatsApp online no início da fila")
            queue_service = QueueManagerService(db)
            for statement_id in statement_ids:
                statement = db.query(TaxStatement).filter(TaxStatement.id == statement_id).first()
                if statement:
                    statement.status = "failed"
                    statement.processing_error = "nenhuma_instancia_online"
                    db.commit()
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                _update_runtime_job(queue_id, processed_inc=1, failed_inc=1)

            _update_runtime_job(queue_id, status="failed")
            with _tax_send_jobs_lock:
                job = _tax_send_jobs.get(queue_id)
                if job:
                    job["finished_at"] = datetime.now().isoformat()
                    job["error"] = "Nenhuma instância WhatsApp online"
            return

        statement_queue: queue.Queue[int] = queue.Queue()
        for statement_id in statement_ids:
            statement_queue.put(statement_id)

        queue_item_map: Dict[int, int] = {}
        items = db.query(SendQueueItem).filter(SendQueueItem.queue_id == queue_id).all()
        for item in items:
            metadata = item.item_metadata or {}
            sid = metadata.get("statement_id")
            if isinstance(sid, int):
                queue_item_map[sid] = item.id

        progress_lock = threading.Lock()
        stop_event = threading.Event()
        paused_last_log = [0.0]

        def update_progress_and_item(queue_service: QueueManagerService, queue_item_id: Optional[int], *, successful: bool, error_message: Optional[str] = None) -> None:
            with progress_lock:
                if successful:
                    queue_service.update_queue_progress(queue_id=queue_id, processed=1, successful=1)
                    _update_runtime_job(queue_id, processed_inc=1, successful_inc=1)
                    if queue_item_id:
                        queue_service.update_item_status(queue_item_id, "sent")
                else:
                    queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                    _update_runtime_job(queue_id, processed_inc=1, failed_inc=1)
                    if queue_item_id:
                        queue_service.update_item_status(queue_item_id, "failed", error_message or "Erro de envio")

        def wait_if_paused_or_cancelled(local_db) -> bool:
            while True:
                queue_row = local_db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
                if queue_row and queue_row.status == "cancelled":
                    stop_event.set()
                    _update_runtime_job(queue_id, status="cancelled")
                    _queue_log(queue_id, "Fila cancelada durante processamento")
                    return False

                if not queue_row or queue_row.status != "paused":
                    return True

                now = time.time()
                if now - paused_last_log[0] >= 10:
                    _queue_log(queue_id, "Fila pausada, aguardando retomada...")
                    paused_last_log[0] = now
                time.sleep(2)

        def worker(worker_name: str, preferred_instance: str) -> None:
            local_db = SessionLocal()
            queue_service = QueueManagerService(local_db)
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)

            sent_count = 0
            instance_name = preferred_instance

            _queue_log(queue_id, f"{worker_name} iniciado com instância {instance_name}")

            try:
                while not stop_event.is_set():
                    if not wait_if_paused_or_cancelled(local_db):
                        return

                    try:
                        statement_id = statement_queue.get(timeout=1)
                    except queue.Empty:
                        return

                    if sent_count > 0:
                        delay_seconds = random.uniform(120, 180)
                        _update_runtime_job(queue_id, current_item=f"aguardando próximo envio ({worker_name})", next_delay_seconds=delay_seconds)
                        _queue_log(queue_id, f"{worker_name}: próximo disparo em {delay_seconds:.1f}s")
                        time.sleep(delay_seconds)

                        if sent_count % 20 == 0:
                            long_pause_seconds = random.uniform(600, 900)
                            _queue_log(queue_id, f"{worker_name}: pausa longa anti-softban de {long_pause_seconds:.1f}s")
                            time.sleep(long_pause_seconds)

                    statement = local_db.query(TaxStatement).filter(TaxStatement.id == statement_id).first()
                    queue_item_id = queue_item_map.get(statement_id)

                    if not statement:
                        update_progress_and_item(queue_service, queue_item_id, successful=False, error_message="Informe não encontrado")
                        statement_queue.task_done()
                        continue

                    current_label = f"{statement.unique_id}.pdf -> {statement.employee_name or 'Sem nome'}"
                    _update_runtime_job(queue_id, current_item=current_label, next_delay_seconds=0)
                    _queue_log(queue_id, f"{worker_name}: processando {current_label}")

                    if not statement.employee or not statement.employee.phone:
                        statement.status = "failed"
                        statement.processing_error = "telefone_nao_cadastrado"
                        local_db.commit()
                        update_progress_and_item(queue_service, queue_item_id, successful=False, error_message="Telefone não cadastrado")
                        _queue_log(queue_id, f"{worker_name}: falha em {statement.unique_id} (telefone não cadastrado)")
                        statement_queue.task_done()
                        continue

                    phone_ok, formatted_phone, phone_error = PhoneValidator.validate_and_format(statement.employee.phone)
                    if not phone_ok or not formatted_phone:
                        statement.status = "failed"
                        statement.processing_error = f"telefone_invalido: {phone_error or 'formato_invalido'}"
                        local_db.commit()
                        update_progress_and_item(
                            queue_service,
                            queue_item_id,
                            successful=False,
                            error_message=f"Telefone inválido: {phone_error or 'formato_invalido'}",
                        )
                        _queue_log(queue_id, f"{worker_name}: falha em {statement.unique_id} (telefone inválido)")
                        statement_queue.task_done()
                        continue

                    if not statement.file_path:
                        statement.status = "failed"
                        statement.processing_error = "arquivo_nao_informado"
                        local_db.commit()
                        update_progress_and_item(queue_service, queue_item_id, successful=False, error_message="Arquivo não informado")
                        _queue_log(queue_id, f"{worker_name}: falha em {statement.unique_id} (arquivo não informado)")
                        statement_queue.task_done()
                        continue

                    if not os.path.exists(statement.file_path):
                        statement.status = "failed"
                        statement.processing_error = "arquivo_nao_encontrado"
                        local_db.commit()
                        update_progress_and_item(queue_service, queue_item_id, successful=False, error_message="Arquivo não encontrado")
                        _queue_log(queue_id, f"{worker_name}: falha em {statement.unique_id} (arquivo não encontrado)")
                        statement_queue.task_done()
                        continue

                    service = EvolutionAPIService(instance_name=instance_name)
                    is_instance_online = worker_loop.run_until_complete(service.check_instance_status())
                    if not is_instance_online:
                        replacement = worker_loop.run_until_complete(instance_manager.get_next_available_instance())
                        if not replacement:
                            statement.status = "failed"
                            statement.processing_error = "nenhuma_instancia_online"
                            local_db.commit()
                            update_progress_and_item(queue_service, queue_item_id, successful=False, error_message="Nenhuma instância WhatsApp online")
                            _queue_log(queue_id, f"{worker_name}: falha em {statement.unique_id} (nenhuma instância online)")
                            statement_queue.task_done()
                            continue

                        instance_name = replacement
                        service = EvolutionAPIService(instance_name=instance_name)
                        _queue_log(queue_id, f"{worker_name}: instância anterior offline, alternando para {instance_name}")

                    selected_template = random.choice(templates) if templates else None
                    message = _render_message_template(selected_template, statement.employee_name, statement.ref_year)

                    _queue_log(
                        queue_id,
                        f"{worker_name}: enviando {statement.unique_id} para {formatted_phone} via {instance_name}",
                    )

                    result = worker_loop.run_until_complete(
                        service.send_communication_message(
                            phone=formatted_phone,
                            message_text=message,
                            file_path=statement.file_path,
                        )
                    )
                    instance_manager.register_send(instance_name)

                    if result.get("success"):
                        statement.status = "sent"
                        statement.sent_at = datetime.now()
                        statement.whatsapp_instance = instance_name
                        statement.whatsapp_status = "sent"
                        statement.whatsapp_message_id = result.get("message_id")
                        statement.processing_error = None
                        local_db.commit()

                        update_progress_and_item(queue_service, queue_item_id, successful=True)
                        sent_count += 1
                        _queue_log(queue_id, f"{worker_name}: sucesso em {statement.unique_id} (instância {instance_name})")

                        local_db.add(
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
                                        "instance": instance_name,
                                        "worker": worker_name,
                                        "template_used": bool(selected_template),
                                    },
                                    ensure_ascii=False,
                                ),
                                entity_type="TaxStatement",
                                entity_id=str(statement.id),
                            )
                        )
                        local_db.commit()
                    else:
                        statement.status = "failed"
                        statement.whatsapp_instance = instance_name
                        statement.whatsapp_status = "failed"
                        statement.processing_error = result.get("message", "erro_envio")
                        local_db.commit()

                        update_progress_and_item(
                            queue_service,
                            queue_item_id,
                            successful=False,
                            error_message=result.get("message", "Erro de envio"),
                        )
                        _queue_log(
                            queue_id,
                            f"{worker_name}: falha em {statement.unique_id} via {instance_name} ({result.get('message', 'erro_envio')})",
                        )

                        local_db.add(
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
                                        "instance": instance_name,
                                        "worker": worker_name,
                                        "error": result.get("message", "erro_envio"),
                                    },
                                    ensure_ascii=False,
                                ),
                                entity_type="TaxStatement",
                                entity_id=str(statement.id),
                            )
                        )
                        local_db.commit()

                    statement_queue.task_done()
            finally:
                worker_loop.close()
                local_db.close()
                _queue_log(queue_id, f"{worker_name} finalizado")

        workers: List[threading.Thread] = []
        total_workers = min(len(online_instances), len(statement_ids))
        _queue_log(queue_id, f"Iniciando {total_workers} worker(s): {online_instances[:total_workers]}")

        for index, instance_name in enumerate(online_instances[:total_workers], start=1):
            worker_thread = threading.Thread(
                target=worker,
                args=(f"worker-{index}", instance_name),
                daemon=True,
            )
            workers.append(worker_thread)
            worker_thread.start()

        for worker_thread in workers:
            worker_thread.join()

        queue_row = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
        final_status = "completed"
        if queue_row and queue_row.status == "cancelled":
            final_status = "cancelled"
        elif queue_row and queue_row.status == "failed":
            final_status = "failed"

        _update_runtime_job(queue_id, status=final_status)
        with _tax_send_jobs_lock:
            job = _tax_send_jobs.get(queue_id)
            if job:
                job["finished_at"] = datetime.now().isoformat()
                if queue_row:
                    job["processed_items"] = queue_row.processed_items
                    job["successful_items"] = queue_row.successful_items
                    job["failed_items"] = queue_row.failed_items

        _queue_log(
            queue_id,
            f"Fila finalizada com status={final_status} | processados={queue_row.processed_items if queue_row else 0} | sucessos={queue_row.successful_items if queue_row else 0} | falhas={queue_row.failed_items if queue_row else 0}",
        )

    except Exception as exc:
        _queue_log(queue_id, f"Erro fatal na fila: {exc}")
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
