"""Service for processing annual tax statement PDFs (Informe de Rendimentos)."""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import PyPDF2
from sqlalchemy.orm import Session

from app.models.tax_statement import TaxStatement
from app.models.employee import Employee


START_MARKER_REGEX = re.compile(r"Pessoa F[ií]sica Benefici[aá]ria dos Rendimentos", re.IGNORECASE)
CPF_REGEX = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CNPJ_FORMATTED_REGEX = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
CNPJ_DIGITS_REGEX = re.compile(r"\b\d{13,14}\b")
YEAR_REGEX = re.compile(r"Ano-calend[aA]rio\s*(\d{4})", re.IGNORECASE)

CNPJ_COMPANY_MAP = {
    "05220639000104": "AB EMPREENDIMENTOS",
    "07847003000104": "AB INFRAESTRUTURA",
}


@dataclass
class Chunk:
    source_pdf: str
    start_page: int
    end_page: int
    page_indexes: List[int]
    cpf_formatted: Optional[str]
    cpf_normalized: str
    cnpj_formatted: Optional[str]
    cnpj_normalized: str
    inferred_company: Optional[str]
    year: int


def normalize_cpf(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", value)


def normalize_cnpj(value: Optional[str]) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 13:
        digits = f"0{digits}"
    return digits


def extract_cnpj(text: str) -> tuple[Optional[str], str]:
    formatted_match = CNPJ_FORMATTED_REGEX.search(text or "")
    if formatted_match:
        formatted = formatted_match.group(0)
        return formatted, normalize_cnpj(formatted)

    digits_match = CNPJ_DIGITS_REGEX.search(text or "")
    if digits_match:
        normalized = normalize_cnpj(digits_match.group(0))
        return digits_match.group(0), normalized

    return None, ""


def infer_company_from_cnpj(value: Optional[str]) -> Optional[str]:
    normalized = normalize_cnpj(value)
    return CNPJ_COMPANY_MAP.get(normalized)


def output_unique_id(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", str(value or "").strip())
    stripped = digits.lstrip("0")
    return stripped or "0"


def extract_year(text: str, fallback_year: Optional[int]) -> int:
    match = YEAR_REGEX.search(text or "")
    if match:
        return int(match.group(1))
    if fallback_year:
        return fallback_year
    return datetime.now().year


def normalize_company(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", str(value).strip())
    return cleaned or None


def infer_company_from_filename(filename: str) -> Optional[str]:
    name = (filename or "").upper()
    if "INFRA" in name:
        return "AB INFRAESTRUTURA"
    if "EMPRE" in name:
        return "AB EMPREENDIMENTOS"
    return None


def split_pdf_into_chunks(pdf_path: Path, fallback_year: Optional[int]) -> List[Chunk]:
    chunks: List[Chunk] = []

    with open(pdf_path, "rb") as fp:
        reader = PyPDF2.PdfReader(fp)
        total_pages = len(reader.pages)

        current_start = None
        current_indexes: List[int] = []
        current_cpf = None
        current_cnpj_formatted = None
        current_cnpj_normalized = ""
        current_company = None
        current_year = fallback_year or datetime.now().year

        for idx in range(total_pages):
            page_no = idx + 1
            text = reader.pages[idx].extract_text() or ""
            marker = bool(START_MARKER_REGEX.search(text))

            if marker:
                if current_start is not None and current_indexes:
                    cpf_norm = normalize_cpf(current_cpf)
                    chunks.append(
                        Chunk(
                            source_pdf=pdf_path.name,
                            start_page=current_start,
                            end_page=page_no - 1,
                            page_indexes=current_indexes,
                            cpf_formatted=current_cpf,
                            cpf_normalized=cpf_norm,
                            cnpj_formatted=current_cnpj_formatted,
                            cnpj_normalized=current_cnpj_normalized,
                            inferred_company=current_company,
                            year=current_year,
                        )
                    )

                cpf_match = CPF_REGEX.search(text)
                cnpj_formatted, cnpj_normalized = extract_cnpj(text)
                current_cpf = cpf_match.group(0) if cpf_match else None
                current_cnpj_formatted = cnpj_formatted
                current_cnpj_normalized = cnpj_normalized
                current_company = infer_company_from_cnpj(cnpj_normalized)
                current_year = extract_year(text, fallback_year)
                current_start = page_no
                current_indexes = [idx]
            else:
                if current_start is not None:
                    current_indexes.append(idx)
                    if not current_cnpj_normalized:
                        cnpj_formatted, cnpj_normalized = extract_cnpj(text)
                        if cnpj_normalized:
                            current_cnpj_formatted = cnpj_formatted
                            current_cnpj_normalized = cnpj_normalized
                            current_company = infer_company_from_cnpj(cnpj_normalized)

        if current_start is not None and current_indexes:
            cpf_norm = normalize_cpf(current_cpf)
            chunks.append(
                Chunk(
                    source_pdf=pdf_path.name,
                    start_page=current_start,
                    end_page=total_pages,
                    page_indexes=current_indexes,
                    cpf_formatted=current_cpf,
                    cpf_normalized=cpf_norm,
                    cnpj_formatted=current_cnpj_formatted,
                    cnpj_normalized=current_cnpj_normalized,
                    inferred_company=current_company,
                    year=current_year,
                )
            )

    return chunks


def save_encrypted_segment(source_pdf: Path, output_pdf: Path, page_indexes: List[int], password: str) -> None:
    writer = PyPDF2.PdfWriter()

    with open(source_pdf, "rb") as fp:
        reader = PyPDF2.PdfReader(fp)
        for page_idx in page_indexes:
            writer.add_page(reader.pages[page_idx])

    writer.encrypt(password)
    with open(output_pdf, "wb") as out_fp:
        writer.write(out_fp)


def find_employee_by_cpf(db: Session, cpf_formatted: str, cpf_normalized: str) -> Optional[Employee]:
    candidates = []
    if cpf_formatted:
        candidates.append(cpf_formatted)
    if cpf_normalized:
        candidates.append(cpf_normalized)
    if not candidates:
        return None

    return db.query(Employee).filter(Employee.cpf.in_(candidates)).first()


def _build_unique_statement_id(db: Session, base_id: str) -> str:
    if not db.query(TaxStatement).filter(TaxStatement.unique_id == base_id).first():
        return base_id

    suffix = 1
    while True:
        candidate = f"{base_id}_DUP{suffix}"
        if not db.query(TaxStatement).filter(TaxStatement.unique_id == candidate).first():
            return candidate
        suffix += 1


def _write_logs(logs_dir: Path, success_rows: List[Dict], error_rows: List[Dict], summary: Dict) -> Dict[str, str]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    success_csv = logs_dir / f"success_{ts}.csv"
    error_csv = logs_dir / f"errors_{ts}.csv"
    summary_json = logs_dir / f"summary_{ts}.json"

    with open(success_csv, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "source_pdf",
                "output_file",
                "statement_id",
                "employee_id",
                "employee_unique_id_db",
                "employee_unique_id_output",
                "employee_name",
                "cpf",
                "cnpj",
                "company",
                "company_validation",
                "year",
                "password_first4",
                "pages_count",
                "page_range",
            ],
        )
        writer.writeheader()
        for row in success_rows:
            writer.writerow(row)

    with open(error_csv, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "source_pdf",
                "reason",
                "cpf",
                "cnpj",
                "company",
                "year",
                "pages_count",
                "page_range",
                "details",
            ],
        )
        writer.writeheader()
        for row in error_rows:
            writer.writerow(row)

    with open(summary_json, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)

    return {
        "success_csv": str(success_csv),
        "error_csv": str(error_csv),
        "summary_json": str(summary_json),
    }


def process_tax_statement_pdf(
    db: Session,
    source_pdf_path: str,
    uploaded_by: int,
    company: Optional[str] = None,
    fallback_year: Optional[int] = None,
    output_root_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict], None]] = None,
) -> Dict:
    source_pdf = Path(source_pdf_path)
    if not source_pdf.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {source_pdf}")

    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = Path(output_root_dir) if output_root_dir else Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    output_base = root / "processed" / "tax_statements" / now_tag
    success_dir = output_base / "success"
    failed_dir = output_base / "failed"
    logs_dir = output_base / "logs"

    success_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    chunks = split_pdf_into_chunks(source_pdf, fallback_year)
    resolved_company = normalize_company(company) or infer_company_from_filename(source_pdf.name)
    detected_companies = sorted({ch.inferred_company for ch in chunks if ch.inferred_company})

    print(f"📄 [IR] Iniciando processamento de {source_pdf.name}")
    print(f"📊 [IR] {len(chunks)} informe(s) detectado(s)")
    if detected_companies:
        print(f"🏢 [IR] Empresas detectadas por CNPJ: {', '.join(detected_companies)}")
    elif resolved_company:
        print(f"🏢 [IR] Empresa inferida pelo lote: {resolved_company}")

    if progress_callback:
        progress_callback(
            {
                "message": "Segmentação concluída, iniciando análise dos informes",
                "total_chunks": len(chunks),
                "processed_chunks": 0,
                "successful_chunks": 0,
                "failed_chunks": 0,
                "current_chunk": 0,
                "current_page_range": None,
            }
        )

    success_rows: List[Dict] = []
    error_rows: List[Dict] = []

    created_ok = 0
    created_failed = 0
    cnpj_mismatch_count = 0
    pending_writes = 0
    batch_commit_size = 25

    for index, ch in enumerate(chunks, start=1):
        page_range = f"{ch.start_page}-{ch.end_page}"
        pages_count = len(ch.page_indexes)
        chunk_company = ch.inferred_company or resolved_company
        company_validation = "ok"

        print(
            f"🔎 [IR] [{index}/{len(chunks)}] Páginas {page_range} | CPF={ch.cpf_formatted or 'N/A'} | "
            f"CNPJ={ch.cnpj_formatted or ch.cnpj_normalized or 'N/A'} | Empresa={chunk_company or 'N/A'}"
        )

        if progress_callback:
            progress_callback(
                {
                    "message": f"Processando informe {index}/{len(chunks)}",
                    "total_chunks": len(chunks),
                    "processed_chunks": created_ok + created_failed,
                    "successful_chunks": created_ok,
                    "failed_chunks": created_failed,
                    "current_chunk": index,
                    "current_page_range": page_range,
                }
            )

        if resolved_company and ch.inferred_company and resolved_company != ch.inferred_company:
            company_validation = "cnpj_diverge_do_lote"
            cnpj_mismatch_count += 1

        if not ch.cpf_formatted:
            created_failed += 1
            print(f"⚠️  [IR] [{index}/{len(chunks)}] Falha: CPF não encontrado no chunk")
            error_rows.append(
                {
                    "source_pdf": ch.source_pdf,
                    "reason": "cpf_nao_encontrado",
                    "cpf": "",
                    "cnpj": ch.cnpj_formatted or ch.cnpj_normalized,
                    "company": chunk_company,
                    "year": ch.year,
                    "pages_count": pages_count,
                    "page_range": page_range,
                    "details": "Marcador de inicio sem CPF formatado.",
                }
            )
            continue

        password = (ch.cpf_normalized or "")[:4]
        if len(password) < 4:
            created_failed += 1
            print(f"⚠️  [IR] [{index}/{len(chunks)}] Falha: senha inválida para CPF {ch.cpf_formatted}")
            error_rows.append(
                {
                    "source_pdf": ch.source_pdf,
                    "reason": "senha_invalida",
                    "cpf": ch.cpf_formatted,
                    "cnpj": ch.cnpj_formatted or ch.cnpj_normalized,
                    "company": chunk_company,
                    "year": ch.year,
                    "pages_count": pages_count,
                    "page_range": page_range,
                    "details": "Nao foi possivel gerar senha com 4 digitos.",
                }
            )
            continue

        employee = find_employee_by_cpf(db, ch.cpf_formatted, ch.cpf_normalized)

        if employee:
            matricula_out = output_unique_id(employee.unique_id)
            base_name = f"IR_{matricula_out}_{ch.year}"
            statement_id = _build_unique_statement_id(db, base_name)
            output_file_name = f"{statement_id}.pdf"
            output_pdf = success_dir / output_file_name

            save_encrypted_segment(source_pdf, output_pdf, ch.page_indexes, password)

            statement = TaxStatement(
                unique_id=statement_id,
                original_filename=source_pdf.name,
                file_path=str(output_pdf),
                file_size=output_pdf.stat().st_size,
                ref_year=ch.year,
                cpf=ch.cpf_formatted,
                pages_count=pages_count,
                employee_id=employee.id,
                employee_unique_id=str(employee.unique_id),
                employee_name=employee.name,
                status="processed",
                password=password,
                uploaded_by=uploaded_by,
                company=chunk_company,
                processing_error=None,
            )
            db.add(statement)
            db.flush()
            pending_writes += 1

            created_ok += 1
            print(f"✅ [IR] [{index}/{len(chunks)}] {employee.name} -> {output_file_name}")
            success_rows.append(
                {
                    "source_pdf": ch.source_pdf,
                    "output_file": output_file_name,
                    "statement_id": statement_id,
                    "employee_id": employee.id,
                    "employee_unique_id_db": str(employee.unique_id),
                    "employee_unique_id_output": matricula_out,
                    "employee_name": employee.name,
                    "cpf": ch.cpf_formatted,
                    "cnpj": ch.cnpj_formatted or ch.cnpj_normalized,
                    "company": chunk_company,
                    "company_validation": company_validation,
                    "year": ch.year,
                    "password_first4": password,
                    "pages_count": pages_count,
                    "page_range": page_range,
                }
            )
        else:
            failed_name = f"IR_CPF_{ch.cpf_normalized or 'SEMCPF'}_{ch.year}_NAO_ENCONTRADO.pdf"
            failed_pdf = failed_dir / failed_name
            save_encrypted_segment(source_pdf, failed_pdf, ch.page_indexes, password)

            base_name = f"IR_CPF_{ch.cpf_normalized or 'SEMCPF'}_{ch.year}"
            statement_id = _build_unique_statement_id(db, base_name)

            statement = TaxStatement(
                unique_id=statement_id,
                original_filename=source_pdf.name,
                file_path=str(failed_pdf),
                file_size=failed_pdf.stat().st_size,
                ref_year=ch.year,
                cpf=ch.cpf_formatted,
                pages_count=pages_count,
                employee_id=None,
                employee_unique_id=None,
                employee_name=None,
                status="failed",
                password=password,
                uploaded_by=uploaded_by,
                company=chunk_company,
                processing_error="cpf_nao_cadastrado",
            )
            db.add(statement)
            db.flush()
            pending_writes += 1

            created_failed += 1
            print(f"⚠️  [IR] [{index}/{len(chunks)}] CPF não cadastrado: {ch.cpf_formatted}")
            error_rows.append(
                {
                    "source_pdf": ch.source_pdf,
                    "reason": "cpf_nao_cadastrado",
                    "cpf": ch.cpf_formatted,
                    "cnpj": ch.cnpj_formatted or ch.cnpj_normalized,
                    "company": chunk_company,
                    "year": ch.year,
                    "pages_count": pages_count,
                    "page_range": page_range,
                    "details": f"Arquivo salvo para revisao: {failed_pdf.name}",
                }
            )

        if pending_writes >= batch_commit_size:
            db.commit()
            pending_writes = 0
            print(f"💾 [IR] Commit parcial realizado após {created_ok + created_failed} chunk(s)")

    if pending_writes > 0:
        db.commit()
        print(f"💾 [IR] Commit final realizado")

    summary = {
        "source_pdf": str(source_pdf),
        "output_base": str(output_base),
        "company": detected_companies[0] if len(detected_companies) == 1 else ("MISTO" if len(detected_companies) > 1 else resolved_company),
        "companies_detected": detected_companies,
        "mixed_companies": len(detected_companies) > 1,
        "cnpj_mismatch_count": cnpj_mismatch_count,
        "chunks_detected": len(chunks),
        "processed_success": created_ok,
        "processed_failed": created_failed,
        "success_rate": round((created_ok / len(chunks) * 100), 2) if chunks else 0,
    }

    logs = _write_logs(logs_dir, success_rows, error_rows, summary)
    summary.update(logs)

    print(
        f"🏁 [IR] Concluído | sucesso={created_ok} | falha={created_failed} | "
        f"misto={'sim' if len(detected_companies) > 1 else 'não'}"
    )

    if progress_callback:
        progress_callback(
            {
                "message": "Processamento concluído",
                "total_chunks": len(chunks),
                "processed_chunks": len(chunks),
                "successful_chunks": created_ok,
                "failed_chunks": created_failed,
                "current_chunk": len(chunks),
                "current_page_range": None,
            }
        )

    return summary
