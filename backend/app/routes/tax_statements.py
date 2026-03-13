"""Modular routes for tax statements (Informe de Rendimentos)."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from datetime import datetime

from app.core.auth import verify_token
from app.models.base import SessionLocal
from app.models.tax_statement import TaxStatement, TaxStatementUpload
from app.models.user import User
from app.services.tax_statement_export import build_sent_tax_statements_zip
from app.services.tax_statement_processing_job import (
    get_tax_statement_processing_job,
    start_tax_statement_processing_job,
)
from app.services.tax_statement_queue import get_tax_statement_send_job, start_tax_statement_send_job

from .base import BaseRouter


class TaxStatementsRouter(BaseRouter):
    """Router for tax statement processing and send workflows."""

    @staticmethod
    def _resolve_writable_upload_dir(backend_root: str) -> tuple[str, str]:
        """Resolve diretório de upload gravável e raiz de saída correspondente.

        Retorna:
            (uploads_dir, output_root_dir)
        """
        candidates = [
            (os.path.join(backend_root, "uploads", "tax_statements"), backend_root),
            (os.path.join("/tmp", "enviafolha", "uploads", "tax_statements"), os.path.join("/tmp", "enviafolha")),
        ]

        for upload_dir, root_dir in candidates:
            try:
                os.makedirs(upload_dir, exist_ok=True)
                if os.access(upload_dir, os.W_OK):
                    return upload_dir, root_dir
            except Exception:
                continue

        raise PermissionError("Nenhum diretório de upload gravável disponível")

    def _get_authenticated_user(self):
        auth_header = self.handler.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.replace("Bearer ", "")
        payload = verify_token(token)
        if not payload:
            return None

        username = payload.get("sub")
        if not username:
            return None

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
            return {"id": user.id, "username": user.username} if user else None
        finally:
            db.close()

    def _parse_multipart_file(self):
        content_type = self.handler.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return None, None, "Content-Type deve ser multipart/form-data"

        boundary = None
        for part in content_type.split(";"):
            if "boundary=" in part:
                boundary = part.split("boundary=")[1].strip()
                break

        if not boundary:
            return None, None, "Boundary não encontrado"

        content_length = int(self.handler.headers.get("Content-Length", 0))
        body = self.handler.rfile.read(content_length)

        boundary_bytes = boundary.encode("utf-8")
        parts = body.split(b"--" + boundary_bytes)

        for part in parts:
            if b"Content-Disposition" not in part or b"filename=" not in part:
                continue

            filename = None
            for line in part.split(b"\r\n")[:8]:
                if b"filename=\"" in line:
                    start = line.find(b"filename=\"") + 10
                    end = line.find(b"\"", start)
                    if end != -1:
                        filename = line[start:end].decode("utf-8", errors="ignore")
                        break

            if not filename:
                continue

            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue

            file_data = part[header_end + 4 :]
            if file_data.endswith(b"\r\n"):
                file_data = file_data[:-2]
            return file_data, filename, None

        return None, None, "Arquivo não encontrado no upload"

    def _safe_remove_file(self, file_path: str) -> bool:
        if not file_path:
            return False
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            return False
        return False

    def handle_process(self):
        """POST /api/v1/tax-statements/process"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        file_data, filename, parse_error = self._parse_multipart_file()
        if parse_error:
            self.send_error(parse_error, 400)
            return

        if not filename.lower().endswith(".pdf"):
            self.send_error("Apenas arquivos PDF são aceitos", 400)
            return

        parsed = urllib.parse.urlparse(self.handler.path)
        query = urllib.parse.parse_qs(parsed.query)
        company = query.get("company", [None])[0]
        ref_year_raw = query.get("ref_year", [None])[0]
        ref_year = int(ref_year_raw) if ref_year_raw and str(ref_year_raw).isdigit() else None

        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            uploads_dir, output_root_dir = self._resolve_writable_upload_dir(backend_root)
        except PermissionError as exc:
            self.send_error(str(exc), 500)
            return

        safe_name = f"{int(time.time())}_{filename}"
        upload_path = os.path.join(uploads_dir, safe_name)

        with open(upload_path, "wb") as fp:
            fp.write(file_data)

        db = SessionLocal()
        try:
            batch = TaxStatementUpload(
                original_filename=filename,
                file_path=upload_path,
                file_size=len(file_data),
                ref_year=ref_year or datetime.now().year,
                company=company,
                status="processing",
                total_statements=0,
                statements_processed=0,
                statements_failed=0,
                processing_started_at=datetime.now(),
                uploaded_by=user["id"],
            )
            db.add(batch)
            db.commit()
            db.refresh(batch)

            job = start_tax_statement_processing_job(
                batch_id=batch.id,
                source_pdf_path=upload_path,
                uploaded_by=user["id"],
                company=company,
                fallback_year=ref_year,
                output_root_dir=output_root_dir,
            )

            self.send_json_response(
                {
                    "success": True,
                    "message": "Processamento de informes iniciado",
                    "batch_id": batch.id,
                    "job": job,
                },
                202,
            )
        except Exception as exc:
            db.rollback()
            self.send_error(f"Erro ao processar IR: {str(exc)}", 500)
        finally:
            db.close()

    def handle_process_status(self, job_id: str):
        """GET /api/v1/tax-statements/process/{job_id}/status"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        status = get_tax_statement_processing_job(job_id)
        if not status:
            self.send_error("Job de processamento não encontrado", 404)
            return

        self.send_json_response(status, 200)

    def handle_list(self):
        """GET /api/v1/tax-statements"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        parsed = urllib.parse.urlparse(self.handler.path)
        query = urllib.parse.parse_qs(parsed.query)

        page = max(int(query.get("page", ["1"])[0]), 1)
        page_size = min(max(int(query.get("page_size", ["50"])[0]), 1), 200)
        ref_year = query.get("ref_year", [None])[0]
        status = query.get("status", [None])[0]
        company = query.get("company", [None])[0]

        db = SessionLocal()
        try:
            q = db.query(TaxStatement)
            if ref_year and str(ref_year).isdigit():
                q = q.filter(TaxStatement.ref_year == int(ref_year))
            if status:
                q = q.filter(TaxStatement.status == status)
            if company:
                q = q.filter(TaxStatement.company == company)

            total = q.count()
            rows = (
                q.order_by(TaxStatement.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            payload = []
            for row in rows:
                payload.append(
                    {
                        "id": row.id,
                        "unique_id": row.unique_id,
                        "ref_year": row.ref_year,
                        "cpf": row.cpf,
                        "employee_id": row.employee_id,
                        "employee_unique_id": row.employee_unique_id,
                        "employee_name": row.employee_name,
                        "status": row.status,
                        "processing_error": row.processing_error,
                        "file_path": row.file_path,
                        "pages_count": row.pages_count,
                        "company": row.company,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                )

            self.send_json_response(
                {
                    "tax_statements": payload,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                },
                200,
            )
        finally:
            db.close()

    def handle_export_sent(self):
        """GET /api/v1/tax-statements/export/sent"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        parsed = urllib.parse.urlparse(self.handler.path)
        query = urllib.parse.parse_qs(parsed.query)

        ref_year_raw = query.get("ref_year", [None])[0]
        company = query.get("company", [None])[0]
        ref_year = int(ref_year_raw) if ref_year_raw and str(ref_year_raw).isdigit() else None

        db = SessionLocal()
        try:
            result = build_sent_tax_statements_zip(db=db, ref_year=ref_year, company=company)
            if not result.get("zip_bytes"):
                self.send_error("Nenhum informe enviado encontrado para exportação", 404)
                return

            self.send_binary_response(
                data=result["zip_bytes"],
                content_type="application/zip",
                filename=result["file_name"],
            )
        finally:
            db.close()

    def handle_send(self):
        """POST /api/v1/tax-statements/send"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        data = self.get_request_data()
        statement_ids = data.get("statement_ids", [])
        message_template = data.get("message_template")
        message_templates = data.get("message_templates")

        if message_templates is not None and not isinstance(message_templates, list):
            self.send_error("message_templates deve ser uma lista", 400)
            return

        if not isinstance(statement_ids, list) or not statement_ids:
            self.send_error("statement_ids é obrigatório", 400)
            return

        result = start_tax_statement_send_job(
            user_id=user["id"],
            statement_ids=[int(x) for x in statement_ids],
            message_template=message_template,
            message_templates=message_templates,
            computer_name=self.handler.headers.get("X-Computer-Name"),
            ip_address=self.handler.client_address[0] if self.handler.client_address else None,
        )

        self.send_json_response(
            {
                "success": True,
                "message": "Fila de envio de informes iniciada",
                "queue": result,
            },
            202,
        )

    def handle_delete(self):
        """POST /api/v1/tax-statements/delete"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        data = self.get_request_data()
        statement_ids = data.get("statement_ids") or []
        ref_year = data.get("ref_year")
        company = data.get("company")
        status = data.get("status")

        db = SessionLocal()
        try:
            query = db.query(TaxStatement)

            if statement_ids:
                try:
                    ids = [int(x) for x in statement_ids]
                except Exception:
                    self.send_error("statement_ids inválido", 400)
                    return
                query = query.filter(TaxStatement.id.in_(ids))
            else:
                if ref_year is not None:
                    if str(ref_year).isdigit():
                        query = query.filter(TaxStatement.ref_year == int(ref_year))
                    else:
                        self.send_error("ref_year inválido", 400)
                        return

                if company:
                    query = query.filter(TaxStatement.company == company)
                if status:
                    query = query.filter(TaxStatement.status == status)

            rows = query.all()
            if not rows:
                self.send_json_response(
                    {
                        "success": True,
                        "message": "Nenhum informe encontrado para exclusão",
                        "deleted_records": 0,
                        "deleted_files": 0,
                        "missing_files": 0,
                    },
                    200,
                )
                return

            deleted_files = 0
            missing_files = 0

            for row in rows:
                if row.file_path and os.path.exists(row.file_path):
                    if self._safe_remove_file(row.file_path):
                        deleted_files += 1
                    else:
                        missing_files += 1
                else:
                    missing_files += 1

                db.delete(row)

            db.commit()

            self.send_json_response(
                {
                    "success": True,
                    "message": "Informes excluídos com sucesso",
                    "deleted_records": len(rows),
                    "deleted_files": deleted_files,
                    "missing_files": missing_files,
                },
                200,
            )
        except Exception as exc:
            db.rollback()
            self.send_error(f"Erro ao excluir informes: {str(exc)}", 500)
        finally:
            db.close()

    def handle_send_status(self, queue_id: str):
        """GET /api/v1/tax-statements/send/{queue_id}/status"""
        user = self._get_authenticated_user()
        if not user:
            self.send_error("Token de acesso necessário", 401)
            return

        status = get_tax_statement_send_job(queue_id)
        if not status:
            self.send_error("Fila não encontrada", 404)
            return

        self.send_json_response(status, 200)
