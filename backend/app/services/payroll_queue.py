"""Queue and WhatsApp send workflow for payroll files."""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import random
import shutil
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from app.models.base import SessionLocal
from app.models.send_queue import SendQueue, SendQueueItem
from app.services.evolution_api import EvolutionAPIService
from app.services.instance_manager import get_instance_manager
from app.services.phone_validator import PhoneValidator
from app.services.queue_manager import QueueManagerService

logger = logging.getLogger(__name__)

_payroll_send_jobs: Dict[str, Dict] = {}
_payroll_send_jobs_lock = threading.Lock()


def _get_sent_base_dir() -> str:
    candidates = [
        os.getenv("SENT_DIR", "").strip(),
        "sent",
        os.path.join("backend", "sent"),
        "/app/sent",
    ]
    for candidate in candidates:
        if candidate:
            abs_path = os.path.abspath(candidate)
            if os.path.isdir(abs_path):
                return abs_path

    fallback = os.path.abspath("sent")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _move_file_to_sent(file_path: str, month_year: str) -> str:
    sent_base = _get_sent_base_dir()
    period_label = (month_year or "desconhecido").replace("/", "_")
    target_dir = os.path.join(sent_base, period_label)
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.basename(file_path)
    target_path = os.path.join(target_dir, filename)

    if os.path.abspath(file_path) == os.path.abspath(target_path):
        return target_path

    if os.path.exists(target_path):
        base, ext = os.path.splitext(filename)
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        target_path = os.path.join(target_dir, f"{base}_{stamp}{ext}")

    shutil.move(file_path, target_path)
    return target_path


def _update_runtime_job(
    queue_id: str,
    *,
    processed_inc: int = 0,
    successful_inc: int = 0,
    failed_inc: int = 0,
    status: Optional[str] = None,
    current_item: Optional[str] = None,
    error_message: Optional[str] = None,
):
    with _payroll_send_jobs_lock:
        job = _payroll_send_jobs.get(queue_id)
        if not job:
            return

        if processed_inc:
            job["processed_files"] = job.get("processed_files", 0) + processed_inc
        if successful_inc:
            job["successful_sends"] = job.get("successful_sends", 0) + successful_inc
        if failed_inc:
            job["failed_sends"] = job.get("failed_sends", 0) + failed_inc
        if status:
            job["status"] = status
        if current_item is not None:
            job["current_file"] = current_item
        if error_message is not None:
            job["error_message"] = error_message


def _run_send_loop(queue_id: str, items: List[Dict], templates: List[str]) -> None:
    with _payroll_send_jobs_lock:
        job = _payroll_send_jobs.get(queue_id)
        if job:
            job["status"] = "running"
            job["started_at"] = datetime.now().isoformat()

    db = SessionLocal()
    try:
        instance_manager = get_instance_manager()

        bootstrap_loop = asyncio.new_event_loop()
        online_status = bootstrap_loop.run_until_complete(instance_manager.check_all_instances_status())
        bootstrap_loop.close()

        online_instances = [instance for instance, is_online in online_status.items() if is_online]
        queue_service = QueueManagerService(db)

        if not online_instances:
            for item in items:
                queue_service.update_queue_progress(queue_id=queue_id, processed=1, failed=1)
                if item.get("queue_item_id"):
                    queue_service.update_item_status(item["queue_item_id"], "failed", "Nenhuma instância online")
                _update_runtime_job(queue_id, processed_inc=1, failed_inc=1)

            _update_runtime_job(queue_id, status="failed", error_message="Nenhuma instância WhatsApp online")
            return

        work_queue: queue.Queue[Dict] = queue.Queue()
        for item in items:
            work_queue.put(item)

        progress_lock = threading.Lock()
        stop_event = threading.Event()
        paused_last_log = [0.0]

        def update_progress(queue_item_id: Optional[int], *, successful: bool, error_message: Optional[str] = None) -> None:
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
                    _update_runtime_job(queue_id, status="cancelled", error_message="Envio cancelado")
                    return False

                if not queue_row or queue_row.status != "paused":
                    return True

                now = time.time()
                if now - paused_last_log[0] >= 10:
                    logger.info("[PAYROLL-QUEUE %s] Fila pausada, aguardando retomada...", queue_id)
                    paused_last_log[0] = now
                time.sleep(2)

        def worker(worker_name: str, instance_name: str) -> None:
            local_db = SessionLocal()
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
            sends_local = 0
            service = EvolutionAPIService(instance_name=instance_name)

            try:
                while not stop_event.is_set():
                    if not wait_if_paused_or_cancelled(local_db):
                        return

                    # Cooldown por instância: só busca próximo item quando estiver pronta.
                    if sends_local > 0:
                        delay_seconds = random.uniform(120, 180)
                        _update_runtime_job(
                            queue_id,
                            current_item=f"Aguardando {delay_seconds:.1f}s ({worker_name}:{instance_name})",
                        )
                        time.sleep(delay_seconds)

                        if sends_local % 20 == 0:
                            long_pause = random.uniform(600, 900)
                            _update_runtime_job(
                                queue_id,
                                current_item=f"Pausa longa {long_pause:.1f}s ({worker_name}:{instance_name})",
                            )
                            time.sleep(long_pause)

                    if not wait_if_paused_or_cancelled(local_db):
                        return

                    try:
                        item = work_queue.get(timeout=1)
                    except queue.Empty:
                        return

                    queue_item_id = item.get("queue_item_id")
                    file_path = item.get("filepath")
                    employee_name = item.get("employee_name") or "Colaborador"
                    month_year = item.get("month_year") or "desconhecido"
                    phone = item.get("phone_number")
                    label = item.get("filename") or file_path or "arquivo"

                    _update_runtime_job(queue_id, current_item=f"{label} ({worker_name}:{instance_name})")

                    phone_ok, formatted_phone, phone_error = PhoneValidator.validate_and_format(phone)
                    if not phone_ok or not formatted_phone:
                        update_progress(queue_item_id, successful=False, error_message=f"Telefone inválido: {phone_error or 'formato_invalido'}")
                        work_queue.task_done()
                        sends_local += 1
                        continue

                    if not file_path:
                        update_progress(queue_item_id, successful=False, error_message="Arquivo não informado")
                        work_queue.task_done()
                        sends_local += 1
                        continue

                    selected_template = random.choice(templates) if templates else None

                    result = worker_loop.run_until_complete(
                        service.send_payroll_message(
                            phone=formatted_phone,
                            employee_name=employee_name,
                            file_path=file_path,
                            month_year=month_year,
                            message_template=selected_template,
                        )
                    )

                    instance_manager.register_send(instance_name)

                    if result.get("success"):
                        try:
                            new_path = _move_file_to_sent(file_path, month_year)
                            if queue_item_id:
                                queue_item_row = local_db.query(SendQueueItem).filter(SendQueueItem.id == queue_item_id).first()
                                if queue_item_row:
                                    queue_item_row.file_path = new_path
                                    local_db.commit()
                        except Exception as move_error:
                            logger.warning("Falha ao mover arquivo enviado para 'sent': %s", move_error)
                        update_progress(queue_item_id, successful=True)
                    else:
                        update_progress(queue_item_id, successful=False, error_message=result.get("message", "Erro de envio"))

                    work_queue.task_done()
                    sends_local += 1
            finally:
                worker_loop.close()
                local_db.close()

        workers: List[threading.Thread] = []
        worker_instances = online_instances[: max(1, min(len(online_instances), len(items)))]

        for i, instance_name in enumerate(worker_instances):
            thread = threading.Thread(
                target=worker,
                args=(f"worker-{i + 1}", instance_name),
                daemon=True,
            )
            workers.append(thread)
            thread.start()

        for thread in workers:
            thread.join()

        queue_row = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
        final_status = "completed"
        if queue_row and queue_row.status == "cancelled":
            final_status = "cancelled"
        elif queue_row and queue_row.status == "failed":
            final_status = "failed"

        _update_runtime_job(queue_id, status=final_status, current_item="")

        with _payroll_send_jobs_lock:
            job = _payroll_send_jobs.get(queue_id)
            if job:
                job["finished_at"] = datetime.now().isoformat()
                if queue_row:
                    job["processed_files"] = queue_row.processed_items
                    job["successful_sends"] = queue_row.successful_items
                    job["failed_sends"] = queue_row.failed_items

    except Exception as exc:
        logger.exception("Erro fatal na fila de holerites %s", queue_id)
        _update_runtime_job(queue_id, status="failed", error_message=str(exc))
    finally:
        db.close()


def start_payroll_send_job(
    user_id: int,
    selected_files: List[Dict],
    message_templates: Optional[List[str]],
    computer_name: Optional[str],
    ip_address: Optional[str],
) -> Dict:
    db = SessionLocal()
    try:
        templates = [t.strip() for t in (message_templates or []) if isinstance(t, str) and t.strip()]
        queue_service = QueueManagerService(db)

        valid_items: List[Dict] = []
        for file_item in selected_files:
            employee = file_item.get("employee") or {}
            filepath = file_item.get("filepath")
            filename = file_item.get("filename")

            if not filepath or not filename:
                continue

            valid_items.append(
                {
                    "filename": filename,
                    "filepath": filepath,
                    "month_year": file_item.get("month_year") or "desconhecido",
                    "employee_id": employee.get("id"),
                    "employee_name": employee.get("full_name") or "Colaborador",
                    "phone_number": employee.get("phone_number"),
                }
            )

        queue_id = queue_service.create_queue(
            queue_type="payroll",
            total_items=len(valid_items),
            description=f"Envio de {len(valid_items)} holerites",
            user_id=user_id,
            file_name="payroll_batch",
            computer_name=computer_name,
            ip_address=ip_address,
            metadata={
                "selected_files_count": len(selected_files),
                "templates_count": len(templates),
                "anti_softban": True,
            },
        )

        for item in valid_items:
            queue_item = queue_service.add_queue_item(
                queue_id=queue_id,
                employee_id=item.get("employee_id"),
                phone_number=item.get("phone_number") or "",
                file_path=item.get("filepath"),
                metadata={
                    "filename": item.get("filename"),
                    "month_year": item.get("month_year"),
                    "employee_name": item.get("employee_name"),
                },
            )
            item["queue_item_id"] = queue_item.id

        with _payroll_send_jobs_lock:
            _payroll_send_jobs[queue_id] = {
                "job_id": queue_id,
                "queue_id": queue_id,
                "status": "pending",
                "total_files": len(valid_items),
                "processed_files": 0,
                "successful_sends": 0,
                "failed_sends": 0,
                "current_file": "",
                "error_message": "",
                "started_at": None,
                "finished_at": None,
            }

        if len(valid_items) == 0:
            queue_row = db.query(SendQueue).filter(SendQueue.queue_id == queue_id).first()
            if queue_row:
                queue_row.status = "completed"
                queue_row.completed_at = datetime.now()
                db.commit()
            with _payroll_send_jobs_lock:
                _payroll_send_jobs[queue_id]["status"] = "completed"
                _payroll_send_jobs[queue_id]["started_at"] = datetime.now().isoformat()
                _payroll_send_jobs[queue_id]["finished_at"] = datetime.now().isoformat()

            return {"job_id": queue_id, "total_files": 0, "status": "completed"}

        thread = threading.Thread(target=_run_send_loop, args=(queue_id, valid_items, templates), daemon=True)
        thread.start()

        return {"job_id": queue_id, "total_files": len(valid_items), "status": "pending"}
    finally:
        db.close()


def get_payroll_send_job(queue_id: str) -> Optional[Dict]:
    with _payroll_send_jobs_lock:
        job = _payroll_send_jobs.get(queue_id)
        if not job:
            return None
        result = dict(job)

    started_at = result.get("started_at")
    elapsed_seconds = 0
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
            elapsed_seconds = int((datetime.now() - started).total_seconds())
        except Exception:
            elapsed_seconds = 0

    total = result.get("total_files", 0) or 0
    processed = result.get("processed_files", 0) or 0
    progress = round((processed / total) * 100, 2) if total > 0 else 0

    result["elapsed_seconds"] = elapsed_seconds
    result["progress_percentage"] = progress
    return result
