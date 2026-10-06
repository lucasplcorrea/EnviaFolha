"""Background processing jobs for tax statement PDF uploads."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Dict, Optional

from app.models.base import SessionLocal
from app.models.tax_statement import TaxStatementUpload
from app.services.tax_statement_processing import process_tax_statement_pdf


_tax_processing_jobs: Dict[str, Dict] = {}
_tax_processing_jobs_lock = threading.Lock()


def _update_job(job_id: str, **updates) -> None:
    with _tax_processing_jobs_lock:
        job = _tax_processing_jobs.get(job_id)
        if job:
            job.update(updates)


def _run_processing_job(
    job_id: str,
    batch_id: int,
    source_pdf_path: str,
    uploaded_by: int,
    company: Optional[str],
    fallback_year: Optional[int],
    output_root_dir: str,
) -> None:
    print(f"📥 [IR JOB {job_id[:8]}] Iniciando processamento assíncrono do arquivo: {source_pdf_path}")
    db = SessionLocal()
    try:
        batch = db.query(TaxStatementUpload).filter(TaxStatementUpload.id == batch_id).first()
        if batch:
            batch.status = "processing"
            batch.processing_started_at = datetime.now()
            db.commit()

        _update_job(job_id, status="processing", started_at=datetime.now().isoformat(), message="Processando PDF")

        def progress_callback(progress: Dict) -> None:
            _update_job(job_id, **progress)

        result = process_tax_statement_pdf(
            db=db,
            source_pdf_path=source_pdf_path,
            uploaded_by=uploaded_by,
            company=company,
            fallback_year=fallback_year,
            output_root_dir=output_root_dir,
            progress_callback=progress_callback,
        )

        batch = db.query(TaxStatementUpload).filter(TaxStatementUpload.id == batch_id).first()
        if batch:
            batch.status = "completed"
            batch.total_statements = result.get("chunks_detected", 0)
            batch.statements_processed = result.get("processed_success", 0)
            batch.statements_failed = result.get("processed_failed", 0)
            batch.company = result.get("company") or company
            batch.processing_completed_at = datetime.now()
            batch.processing_log = str(result)
            db.commit()

        _update_job(
            job_id,
            status="completed",
            finished_at=datetime.now().isoformat(),
            message="Processamento concluído",
            result=result,
            total_chunks=result.get("chunks_detected", 0),
            processed_chunks=result.get("chunks_detected", 0),
            successful_chunks=result.get("processed_success", 0),
            failed_chunks=result.get("processed_failed", 0),
            batch_id=batch_id,
        )
        print(f"✅ [IR JOB {job_id[:8]}] Processamento concluído: {result.get('processed_success', 0)} sucesso(s), {result.get('processed_failed', 0)} falha(s)")
    except Exception as exc:
        print(f"❌ [IR JOB {job_id[:8]}] Falha no processamento: {exc}")
        batch = db.query(TaxStatementUpload).filter(TaxStatementUpload.id == batch_id).first()
        if batch:
            batch.status = "failed"
            batch.processing_completed_at = datetime.now()
            batch.processing_log = str(exc)
            db.commit()

        _update_job(
            job_id,
            status="failed",
            finished_at=datetime.now().isoformat(),
            message=str(exc),
            error=str(exc),
            batch_id=batch_id,
        )
    finally:
        db.close()


def start_tax_statement_processing_job(
    batch_id: int,
    source_pdf_path: str,
    uploaded_by: int,
    company: Optional[str],
    fallback_year: Optional[int],
    output_root_dir: str,
) -> Dict:
    job_id = str(uuid.uuid4())
    with _tax_processing_jobs_lock:
        _tax_processing_jobs[job_id] = {
            "job_id": job_id,
            "batch_id": batch_id,
            "status": "pending",
            "message": "Aguardando processamento",
            "source_pdf_path": source_pdf_path,
            "total_chunks": 0,
            "processed_chunks": 0,
            "successful_chunks": 0,
            "failed_chunks": 0,
            "current_chunk": 0,
            "current_page_range": None,
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }

    thread = threading.Thread(
        target=_run_processing_job,
        args=(job_id, batch_id, source_pdf_path, uploaded_by, company, fallback_year, output_root_dir),
        daemon=True,
    )
    thread.start()

    return _tax_processing_jobs[job_id]


def get_tax_statement_processing_job(job_id: str) -> Optional[Dict]:
    with _tax_processing_jobs_lock:
        return _tax_processing_jobs.get(job_id)
