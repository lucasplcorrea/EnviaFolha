"""Servicos para relatorios exportaveis (XLSX)."""

from __future__ import annotations

import calendar
import ast
import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.payroll import BenefitsData, BenefitsPeriod, PayrollData, PayrollPeriod
from app.utils.parsers import normalize_cpf, parse_br_number


CURRENCY_COLUMNS = {
    "Salario Base",
    "Proventos",
    "Descontos",
    "Liquido",
    "Mobilidade",
    "Vale Alimentacao",
    "Vale Refeicao",
    "Saldo Livre",
}


def _as_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return float(parse_br_number(value))


def _parse_json_like(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except Exception:
                try:
                    return ast.literal_eval(text)
                except Exception:
                    return value
    return value


def _as_dict_payload(payload: Any) -> Dict[str, Any]:
    parsed = _parse_json_like(payload)
    return parsed if isinstance(parsed, dict) else {}


def _get_first_number(payload: Optional[Dict[str, Any]], keys: Iterable[str]) -> float:
    payload_dict = _as_dict_payload(payload)
    if not payload_dict:
        return 0.0
    for key in keys:
        if key in payload_dict and payload_dict[key] not in (None, ""):
            return _as_float(payload_dict[key])
    return 0.0


def _normalize_key(value: Any) -> str:
    import unicodedata

    text = str(value or "")
    if "\\u" in text:
        try:
            text = bytes(text, "utf-8").decode("unicode_escape")
        except Exception:
            pass

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def _get_first_number_fuzzy(payload: Optional[Dict[str, Any]], aliases: Iterable[str]) -> float:
    payload_dict = _as_dict_payload(payload)
    if not payload_dict:
        return 0.0

    normalized_aliases = {_normalize_key(alias) for alias in aliases}
    for key, value in payload_dict.items():
        if _normalize_key(key) in normalized_aliases and value not in (None, ""):
            return _as_float(value)
    return 0.0


def _sum_numeric_payload(payload: Any) -> float:
    payload = _parse_json_like(payload)
    if payload is None:
        return 0.0
    if isinstance(payload, dict):
        return sum(_sum_numeric_payload(value) for value in payload.values())
    if isinstance(payload, (list, tuple, set)):
        return sum(_sum_numeric_payload(value) for value in payload)
    return _as_float(payload)


def _latest_by_employee(rows: List[Any]) -> Dict[int, Any]:
    latest: Dict[int, Any] = {}
    for row in rows:
        if row.employee_id not in latest:
            latest[row.employee_id] = row
    return latest


def _active_employees_for_month(
    session: Session,
    company: str,
    year: int,
    month: int,
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
) -> List[Employee]:
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    query = (
        session.query(Employee)
        .filter(
            or_(
                Employee.company_code == company,
                Employee.unique_id.like(f"{company}%"),
                Employee.absolute_id.like(f"{company}%"),
            )
        )
        .filter(or_(Employee.admission_date.is_(None), Employee.admission_date <= month_end))
        .filter(or_(Employee.termination_date.is_(None), Employee.termination_date >= month_start))
    )

    if department:
        query = query.filter(Employee.department == department)

    if employee_id is not None:
        query = query.filter(Employee.id == employee_id)

    return query.order_by(Employee.name.asc()).all()

def _classify_payroll_period_type(period_name: Optional[str]) -> str:
    name = _normalize_key(period_name)
    if "13" in name and "adiant" in name:
        return "13_adiantamento"
    if "13" in name:
        return "13_integral"
    if "complement" in name:
        return "complementar"
    if "adiant" in name:
        return "adiantamento_salario"
    return "mensal"


def _latest_payroll_by_employee(
    session: Session,
    company: str,
    year: int,
    month: int,
    payroll_type: str = "mensal",
) -> Dict[int, PayrollData]:
    rows = (
        session.query(PayrollData, PayrollPeriod)
        .join(PayrollPeriod, PayrollPeriod.id == PayrollData.period_id)
        .filter(
            PayrollPeriod.company == company,
            PayrollPeriod.year == year,
            PayrollPeriod.month == month,
        )
        .order_by(
            PayrollData.employee_id.asc(),
            PayrollData.updated_at.desc().nullslast(),
            PayrollData.id.desc(),
        )
        .all()
    )

    filtered_rows: List[PayrollData] = []
    for payroll_data, period in rows:
        detected_type = _classify_payroll_period_type(period.period_name)
        if payroll_type != "all" and detected_type != payroll_type:
            continue
        filtered_rows.append(payroll_data)

    return _latest_by_employee(filtered_rows)


def _latest_benefits_by_employee(session: Session, company: str, year: int, month: int) -> Dict[int, BenefitsData]:
    rows = (
        session.query(BenefitsData)
        .join(BenefitsPeriod, BenefitsPeriod.id == BenefitsData.period_id)
        .filter(
            BenefitsPeriod.company == company,
            BenefitsPeriod.year == year,
            BenefitsPeriod.month == month,
        )
        .order_by(
            BenefitsData.employee_id.asc(),
            BenefitsData.updated_at.desc().nullslast(),
            BenefitsData.id.desc(),
        )
        .all()
    )
    return _latest_by_employee(rows)


def _build_export_rows(
    employees: List[Employee],
    payroll_by_employee: Dict[int, PayrollData],
    benefits_by_employee: Dict[int, BenefitsData],
    company: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for employee in employees:
        payroll = payroll_by_employee.get(employee.id)
        benefits = benefits_by_employee.get(employee.id)

        payroll_additional = _as_dict_payload(payroll.additional_data) if payroll else {}
        payroll_earnings = _as_dict_payload(payroll.earnings_data) if payroll else {}
        payroll_deductions = _as_dict_payload(payroll.deductions_data) if payroll else {}

        salario_base = _get_first_number_fuzzy(
            payroll_additional,
            ["Salário Mensal", "Salario Mensal", "Valor Salário", "Valor Salario", "Salário Base", "Salario Base"],
        )
        if not salario_base:
            salario_base = _get_first_number_fuzzy(
                payroll_earnings,
                ["SALARIO_BASE", "Salário Base", "Salario Base", "SALARIO MENSAL", "Salário Mensal"],
            )
        if not salario_base and payroll is not None:
            salario_base = _as_float(payroll.gross_salary)

        proventos = _get_first_number_fuzzy(
            payroll_additional,
            [
                "Total de Proventos",
                "TOTAL_PROVENTOS",
                "Total Proventos",
                "Total Provento",
                "Proventos",
                "Total Vencimentos",
            ],
        )
        if not proventos and payroll is not None:
            proventos = _as_float(payroll.gross_salary)
        if not proventos:
            proventos = _sum_numeric_payload(payroll_earnings)

        descontos = _get_first_number_fuzzy(
            payroll_additional,
            [
                "Total de Descontos",
                "TOTAL_DESCONTOS",
                "Total Descontos",
                "Descontos",
                "Total de Deducoes",
            ],
        )
        if not descontos:
            descontos = _sum_numeric_payload(payroll_deductions)

        liquido = _get_first_number_fuzzy(
            payroll_additional,
            ["Liquido de Calculo", "Líquido de Cálculo", "LIQ_A_RECEBER", "Liquido", "Liquido a Receber"],
        )
        if not liquido and payroll is not None:
            liquido = _as_float(payroll.net_salary)

        rows.append(
            {
                "Nome": employee.name,
                "Cargo": employee.position or "",
                "Setor": employee.department or "",
                "CPF": normalize_cpf(employee.cpf) if employee.cpf else "",
                "Matricula": employee.unique_id or employee.registration_number or "",
                "Absolute ID": employee.absolute_id or "",
                "Empresa": employee.company_code or company,
                "Situacao": employee.employment_status or "",
                "Admissao": employee.admission_date,
                "Demissao": employee.termination_date,
                "Salario Base": salario_base,
                "Proventos": proventos,
                "Descontos": descontos,
                "Liquido": liquido,
                "Mobilidade": _as_float(benefits.mobilidade) if benefits else 0.0,
                "Vale Alimentacao": _as_float(benefits.alimentacao) if benefits else 0.0,
                "Vale Refeicao": _as_float(benefits.refeicao) if benefits else 0.0,
                "Saldo Livre": _as_float(benefits.livre) if benefits else 0.0,
            }
        )

    return rows


def _write_xlsx(rows: List[Dict[str, Any]], company: str, year: int, month: int) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = f"{company} {year}-{month:02d}"

    title_fill = PatternFill("solid", fgColor="1F4E79")
    header_fill = PatternFill("solid", fgColor="2E75B6")
    zebra_fill = PatternFill("solid", fgColor="F5FAFF")
    thin = Side(border_style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_font = Font(color="FFFFFF", bold=True)
    title_font = Font(color="FFFFFF", bold=True, size=12)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    columns = [
        "Nome",
        "Cargo",
        "Setor",
        "CPF",
        "Matricula",
        "Absolute ID",
        "Empresa",
        "Situacao",
        "Admissao",
        "Demissao",
        "Salario Base",
        "Proventos",
        "Descontos",
        "Liquido",
        "Mobilidade",
        "Vale Alimentacao",
        "Vale Refeicao",
        "Saldo Livre",
    ]

    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
    title_cell = sheet.cell(row=1, column=1, value=f"Relatorio Estrategico - Infraestrutura {company} - {month:02d}/{year}")
    title_cell.fill = title_fill
    title_cell.font = title_font
    title_cell.alignment = center

    header_row = 3
    for col_idx, name in enumerate(columns, start=1):
        cell = sheet.cell(row=header_row, column=col_idx, value=name)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = center

    for row_idx, row_data in enumerate(rows, start=header_row + 1):
        row_fill = zebra_fill if row_idx % 2 == 0 else None
        for col_idx, name in enumerate(columns, start=1):
            cell = sheet.cell(row=row_idx, column=col_idx, value=row_data.get(name))
            cell.border = border
            if row_fill:
                cell.fill = row_fill

            if name in CURRENCY_COLUMNS:
                cell.number_format = 'R$ #,##0.00'
            elif name in {"Admissao", "Demissao"} and cell.value:
                cell.number_format = 'DD/MM/YYYY'

    sheet.freeze_panes = f"A{header_row + 1}"
    sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(len(columns))}{header_row + max(1, len(rows))}"

    widths = {
        "A": 28,
        "B": 22,
        "C": 18,
        "D": 16,
        "E": 15,
        "F": 24,
        "G": 10,
        "H": 14,
        "I": 14,
        "J": 14,
        "K": 14,
        "L": 14,
        "M": 14,
        "N": 14,
        "O": 14,
        "P": 16,
        "Q": 16,
        "R": 14,
    }
    for letter, width in widths.items():
        sheet.column_dimensions[letter].width = width

    summary = workbook.create_sheet("Resumo")
    summary["A1"] = "Resumo da exportacao"
    summary["A1"].font = Font(bold=True, size=12, color="1F4E79")
    summary["A3"] = "Empresa"
    summary["B3"] = company
    summary["A4"] = "Competencia"
    summary["B4"] = f"{year}-{month:02d}"
    summary["A5"] = "Colaboradores"
    summary["B5"] = len(rows)
    summary["A6"] = "Gerado pelo"
    summary["B6"] = "Relatorios Exportaveis"
    summary.column_dimensions["A"].width = 22
    summary.column_dimensions["B"].width = 26

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream.getvalue()


def build_infra_analytics_xlsx(
    session: Session,
    year: int,
    month: int,
    company: str = "0059",
    payroll_type: str = "mensal",
    department: Optional[str] = None,
    employee_id: Optional[int] = None,
) -> Tuple[bytes, int, str]:
    """Gera o xlsx de relatorio estrategico de infraestrutura e retorna bytes, total de linhas e nome sugerido."""
    employees = _active_employees_for_month(
        session,
        company=company,
        year=year,
        month=month,
        department=department,
        employee_id=employee_id,
    )
    payroll = _latest_payroll_by_employee(
        session,
        company=company,
        year=year,
        month=month,
        payroll_type=payroll_type,
    )
    benefits = _latest_benefits_by_employee(session, company=company, year=year, month=month)

    rows = _build_export_rows(employees, payroll, benefits, company=company)
    xlsx_bytes = _write_xlsx(rows, company=company, year=year, month=month)
    suffix = "" if payroll_type == "mensal" else f"_{payroll_type}"
    filename = f"relatorio_estrategico_{company}_{year}-{month:02d}{suffix}.xlsx"
    return xlsx_bytes, len(rows), filename
