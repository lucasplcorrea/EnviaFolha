"""Export helpers for sent tax statements."""

from __future__ import annotations

import csv
import os
import zipfile
from datetime import datetime
from io import BytesIO, StringIO
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.tax_statement import TaxStatement


def build_sent_tax_statements_zip(
    db: Session,
    ref_year: Optional[int] = None,
    company: Optional[str] = None,
) -> Dict[str, object]:
    query = db.query(TaxStatement).filter(TaxStatement.status == "sent")

    if ref_year:
        query = query.filter(TaxStatement.ref_year == ref_year)
    if company:
        query = query.filter(TaxStatement.company == company)

    rows = query.order_by(TaxStatement.company.asc(), TaxStatement.employee_name.asc(), TaxStatement.id.asc()).all()

    if not rows:
        return {
            "file_name": None,
            "zip_bytes": None,
            "count": 0,
        }

    zip_buffer = BytesIO()
    manifest_buffer = StringIO()
    manifest_writer = csv.DictWriter(
        manifest_buffer,
        fieldnames=[
            "statement_id",
            "unique_id",
            "employee_name",
            "employee_unique_id",
            "cpf",
            "company",
            "ref_year",
            "sent_at",
            "whatsapp_instance",
            "source_file",
        ],
    )
    manifest_writer.writeheader()

    added_count = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for row in rows:
            if not row.file_path or not os.path.exists(row.file_path):
                continue

            archive_company = (row.company or "SEM_EMPRESA").replace("/", "-")
            archive_name = f"{archive_company}/{row.ref_year}/{row.unique_id}.pdf"
            zip_file.write(row.file_path, archive_name)
            added_count += 1

            manifest_writer.writerow(
                {
                    "statement_id": row.id,
                    "unique_id": row.unique_id,
                    "employee_name": row.employee_name or "",
                    "employee_unique_id": row.employee_unique_id or "",
                    "cpf": row.cpf,
                    "company": row.company or "",
                    "ref_year": row.ref_year,
                    "sent_at": row.sent_at.isoformat() if row.sent_at else "",
                    "whatsapp_instance": row.whatsapp_instance or "",
                    "source_file": row.file_path,
                }
            )

        zip_file.writestr("manifest.csv", manifest_buffer.getvalue().encode("utf-8-sig"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"Informes_Enviados_{timestamp}.zip"

    return {
        "file_name": file_name,
        "zip_bytes": zip_buffer.getvalue(),
        "count": added_count,
    }