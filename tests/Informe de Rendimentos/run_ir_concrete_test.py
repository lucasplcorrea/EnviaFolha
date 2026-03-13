# -*- coding: utf-8 -*-
"""
Teste concreto de processamento de Informes de Rendimentos.

O script:
1. Lê todos os PDFs da pasta "tests/Informe de Rendimentos"
2. Segmenta por colaborador (início detectado por marcador no texto)
3. Busca colaborador por CPF no banco de dados
4. Salva PDF protegido com senha (4 primeiros dígitos do CPF)
5. Nomeia no formato: IR_MATRICULA_ANO.pdf (matrícula sem zeros à esquerda)
6. Gera logs detalhados de sucesso e falha para correção posterior
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import PyPDF2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


START_MARKER_REGEX = re.compile(r"Pessoa F[ií]sica Benefici[aá]ria dos Rendimentos", re.IGNORECASE)
CPF_REGEX = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
YEAR_REGEX = re.compile(r"Ano-calend[aá]rio\s*(\d{4})", re.IGNORECASE)


@dataclass
class InformeChunk:
    source_pdf: str
    start_page: int
    end_page: int
    cpf_formatted: Optional[str]
    cpf_normalized: Optional[str]
    year: str
    page_numbers: List[int]


@dataclass
class SuccessItem:
    source_pdf: str
    output_file: str
    employee_id: int
    unique_id_db: str
    unique_id_output: str
    employee_name: str
    cpf: str
    year: str
    password_first4: str
    page_range: str
    pages_count: int


@dataclass
class ErrorItem:
    source_pdf: str
    reason: str
    cpf: str
    year: str
    start_page: int
    end_page: int
    pages_count: int
    details: str


def find_project_root(start_path: Path) -> Path:
    """Sobe diretórios até encontrar a pasta backend."""
    current = start_path.resolve()
    for candidate in [current] + list(current.parents):
        if (candidate / "backend").exists() and (candidate / "tests").exists():
            return candidate
    raise RuntimeError("Não foi possível localizar raiz do projeto (backend/tests).")


def normalize_cpf(cpf: Optional[str]) -> str:
    if not cpf:
        return ""
    return re.sub(r"\D", "", cpf)


def output_matricula(unique_id: Optional[str]) -> str:
    """Retorna matrícula sem zeros à esquerda, mantendo apenas dígitos."""
    raw = re.sub(r"\D", "", str(unique_id or "").strip())
    stripped = raw.lstrip("0")
    return stripped or "0"


def extract_year(text: str) -> str:
    match = YEAR_REGEX.search(text or "")
    return match.group(1) if match else "2025"


def chunk_pdf_by_informe(pdf_path: Path) -> List[InformeChunk]:
    chunks: List[InformeChunk] = []

    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)

        current_start = None
        current_page_numbers: List[int] = []
        current_cpf_fmt: Optional[str] = None
        current_cpf_norm: Optional[str] = None
        current_year = "2025"

        total_pages = len(reader.pages)
        for idx in range(total_pages):
            page_number = idx + 1
            page = reader.pages[idx]
            text = page.extract_text() or ""

            is_start = bool(START_MARKER_REGEX.search(text))
            if is_start:
                if current_start is not None and current_page_numbers:
                    chunks.append(
                        InformeChunk(
                            source_pdf=pdf_path.name,
                            start_page=current_start,
                            end_page=page_number - 1,
                            cpf_formatted=current_cpf_fmt,
                            cpf_normalized=current_cpf_norm,
                            year=current_year,
                            page_numbers=current_page_numbers,
                        )
                    )

                cpf_match = CPF_REGEX.search(text)
                cpf_fmt = cpf_match.group(0) if cpf_match else None

                current_start = page_number
                current_page_numbers = [idx]
                current_cpf_fmt = cpf_fmt
                current_cpf_norm = normalize_cpf(cpf_fmt)
                current_year = extract_year(text)
            else:
                if current_start is not None:
                    current_page_numbers.append(idx)

        if current_start is not None and current_page_numbers:
            chunks.append(
                InformeChunk(
                    source_pdf=pdf_path.name,
                    start_page=current_start,
                    end_page=total_pages,
                    cpf_formatted=current_cpf_fmt,
                    cpf_normalized=current_cpf_norm,
                    year=current_year,
                    page_numbers=current_page_numbers,
                )
            )

    return chunks


def get_employee_by_cpf(db: Session, cpf_formatted: str, cpf_normalized: str):
    from app.models.employee import Employee

    if not cpf_formatted and not cpf_normalized:
        return None

    candidates = []
    if cpf_formatted:
        candidates.append(cpf_formatted)
    if cpf_normalized:
        candidates.append(cpf_normalized)

    return db.query(Employee).filter(Employee.cpf.in_(candidates)).first()


def save_protected_pdf(source_pdf: Path, output_file: Path, page_numbers: List[int], password: str):
    writer = PyPDF2.PdfWriter()
    with open(source_pdf, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_idx in page_numbers:
            writer.add_page(reader.pages[page_idx])
    writer.encrypt(password)

    with open(output_file, "wb") as out_f:
        writer.write(out_f)


def process_all(project_root: Path) -> Tuple[List[SuccessItem], List[ErrorItem], Dict[str, int]]:
    input_dir = project_root / "tests" / "Informe de Rendimentos"
    output_root = input_dir / "IR Test Output"
    output_success = output_root / "success"
    output_failed = output_root / "failed"
    logs_dir = output_root / "logs"

    output_success.mkdir(parents=True, exist_ok=True)
    output_failed.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    load_dotenv(project_root / ".env")

    # Permite importar app.models a partir de backend/
    backend_path = project_root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL não encontrada no .env")

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"Nenhum PDF encontrado em {input_dir}")

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    success_items: List[SuccessItem] = []
    error_items: List[ErrorItem] = []

    metrics = {
        "pdfs_lidos": 0,
        "informes_detectados": 0,
        "informes_salvos": 0,
        "informes_falha": 0,
    }

    with SessionLocal() as db:
        for pdf in pdf_files:
            metrics["pdfs_lidos"] += 1

            try:
                chunks = chunk_pdf_by_informe(pdf)
            except Exception as exc:
                error_items.append(
                    ErrorItem(
                        source_pdf=pdf.name,
                        reason="falha_segmentacao_pdf",
                        cpf="",
                        year="",
                        start_page=0,
                        end_page=0,
                        pages_count=0,
                        details=str(exc),
                    )
                )
                continue

            metrics["informes_detectados"] += len(chunks)

            for ch in chunks:
                pages_count = len(ch.page_numbers)
                page_range = f"{ch.start_page}-{ch.end_page}"

                if not ch.cpf_formatted:
                    metrics["informes_falha"] += 1
                    error_items.append(
                        ErrorItem(
                            source_pdf=ch.source_pdf,
                            reason="cpf_nao_encontrado_no_inicio",
                            cpf="",
                            year=ch.year,
                            start_page=ch.start_page,
                            end_page=ch.end_page,
                            pages_count=pages_count,
                            details="Marcador de início detectado sem CPF formatado na página inicial",
                        )
                    )
                    continue

                try:
                    employee = get_employee_by_cpf(db, ch.cpf_formatted, ch.cpf_normalized or "")
                except Exception as exc:
                    metrics["informes_falha"] += 1
                    error_items.append(
                        ErrorItem(
                            source_pdf=ch.source_pdf,
                            reason="erro_consulta_banco",
                            cpf=ch.cpf_formatted,
                            year=ch.year,
                            start_page=ch.start_page,
                            end_page=ch.end_page,
                            pages_count=pages_count,
                            details=str(exc),
                        )
                    )
                    continue

                password = (ch.cpf_normalized or "")[:4]
                if len(password) < 4:
                    metrics["informes_falha"] += 1
                    error_items.append(
                        ErrorItem(
                            source_pdf=ch.source_pdf,
                            reason="senha_invalida",
                            cpf=ch.cpf_formatted,
                            year=ch.year,
                            start_page=ch.start_page,
                            end_page=ch.end_page,
                            pages_count=pages_count,
                            details="Não foi possível derivar os 4 primeiros dígitos do CPF",
                        )
                    )
                    continue

                if not employee:
                    # Mantém artefato para diagnóstico manual
                    failed_name = f"IR_CPF_{ch.cpf_normalized or 'SEMCPF'}_{ch.year}_NAO_ENCONTRADO.pdf"
                    failed_file = output_failed / failed_name
                    try:
                        save_protected_pdf(pdf, failed_file, ch.page_numbers, password)
                    except Exception as exc:
                        error_items.append(
                            ErrorItem(
                                source_pdf=ch.source_pdf,
                                reason="falha_salvar_pdf_nao_encontrado",
                                cpf=ch.cpf_formatted,
                                year=ch.year,
                                start_page=ch.start_page,
                                end_page=ch.end_page,
                                pages_count=pages_count,
                                details=str(exc),
                            )
                        )
                        metrics["informes_falha"] += 1
                        continue

                    metrics["informes_falha"] += 1
                    error_items.append(
                        ErrorItem(
                            source_pdf=ch.source_pdf,
                            reason="cpf_nao_cadastrado",
                            cpf=ch.cpf_formatted,
                            year=ch.year,
                            start_page=ch.start_page,
                            end_page=ch.end_page,
                            pages_count=pages_count,
                            details=f"PDF salvo para revisão em failed/{failed_name}",
                        )
                    )
                    continue

                matricula_out = output_matricula(employee.unique_id)
                out_name = f"IR_{matricula_out}_{ch.year}.pdf"
                out_file = output_success / out_name

                # Evita colisão de nome no mesmo lote
                if out_file.exists():
                    suffix = f"_dup_{ch.start_page}"
                    out_name = f"IR_{matricula_out}_{ch.year}{suffix}.pdf"
                    out_file = output_success / out_name

                try:
                    save_protected_pdf(pdf, out_file, ch.page_numbers, password)
                except Exception as exc:
                    metrics["informes_falha"] += 1
                    error_items.append(
                        ErrorItem(
                            source_pdf=ch.source_pdf,
                            reason="falha_salvar_pdf_sucesso",
                            cpf=ch.cpf_formatted,
                            year=ch.year,
                            start_page=ch.start_page,
                            end_page=ch.end_page,
                            pages_count=pages_count,
                            details=str(exc),
                        )
                    )
                    continue

                metrics["informes_salvos"] += 1
                success_items.append(
                    SuccessItem(
                        source_pdf=ch.source_pdf,
                        output_file=out_name,
                        employee_id=employee.id,
                        unique_id_db=str(employee.unique_id),
                        unique_id_output=matricula_out,
                        employee_name=employee.name,
                        cpf=ch.cpf_formatted,
                        year=ch.year,
                        password_first4=password,
                        page_range=page_range,
                        pages_count=pages_count,
                    )
                )

    # Logs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    success_csv = logs_dir / f"success_{ts}.csv"
    error_csv = logs_dir / f"errors_{ts}.csv"
    summary_txt = logs_dir / f"summary_{ts}.txt"
    summary_json = logs_dir / f"summary_{ts}.json"

    with open(success_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_pdf",
                "output_file",
                "employee_id",
                "unique_id_db",
                "unique_id_output",
                "employee_name",
                "cpf",
                "year",
                "password_first4",
                "page_range",
                "pages_count",
            ],
        )
        writer.writeheader()
        for item in success_items:
            writer.writerow(item.__dict__)

    with open(error_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_pdf",
                "reason",
                "cpf",
                "year",
                "start_page",
                "end_page",
                "pages_count",
                "details",
            ],
        )
        writer.writeheader()
        for item in error_items:
            writer.writerow(item.__dict__)

    summary = {
        "timestamp": ts,
        "input_dir": str(input_dir),
        "output_dir": str(output_root),
        "metrics": metrics,
        "success_count": len(success_items),
        "error_count": len(error_items),
        "success_csv": str(success_csv),
        "error_csv": str(error_csv),
    }

    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = [
        "=" * 100,
        "TESTE CONCRETO - INFORME DE RENDIMENTOS",
        "=" * 100,
        f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"PDFs lidos: {metrics['pdfs_lidos']}",
        f"Informes detectados: {metrics['informes_detectados']}",
        f"Informes salvos com sucesso: {metrics['informes_salvos']}",
        f"Informes com falha: {metrics['informes_falha']}",
        f"Taxa de sucesso: {(metrics['informes_salvos'] / metrics['informes_detectados'] * 100):.2f}%" if metrics['informes_detectados'] else "Taxa de sucesso: 0.00%",
        "",
        f"Pasta de saída (sucesso): {output_success}",
        f"Pasta de saída (falha): {output_failed}",
        f"Log de sucessos: {success_csv.name}",
        f"Log de erros: {error_csv.name}",
        f"Resumo JSON: {summary_json.name}",
        "=" * 100,
    ]

    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))

    return success_items, error_items, {
        **metrics,
        "output_root": str(output_root),
        "success_csv": str(success_csv),
        "error_csv": str(error_csv),
        "summary_txt": str(summary_txt),
        "summary_json": str(summary_json),
    }


def main():
    try:
        script_path = Path(__file__).resolve()
        project_root = find_project_root(script_path.parent)
        process_all(project_root)
    except Exception as exc:
        print("\n[ERRO FATAL]", str(exc))
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
