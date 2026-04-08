"""Servicos para relatorios exportaveis (XLSX)."""

from __future__ import annotations

import calendar
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


def _get_first_number(payload: Optional[Dict[str, Any]], keys: Iterable[str]) -> float:
    if not isinstance(payload, dict):
        return 0.0
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return _as_float(payload[key])
    return 0.0


def _sum_numeric_payload(payload: Any) -> float:
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


def _active_employees_for_month(session: Session, company: str, year: int, month: int) -> List[Employee]:
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    return (
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
        .order_by(Employee.name.asc())
        .all()
    )


def _latest_payroll_by_employee(session: Session, company: str, year: int, month: int) -> Dict[int, PayrollData]:
    rows = (
        session.query(PayrollData)
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
    return _latest_by_employee(rows)


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

        payroll_additional = payroll.additional_data if payroll and isinstance(payroll.additional_data, dict) else {}
        payroll_earnings = payroll.earnings_data if payroll and isinstance(payroll.earnings_data, dict) else {}

        salario_base = _get_first_number(
            payroll_additional,
            ["Salario Mensal", "Salario Mensal", "Valor Salario", "Valor Salario"],
        )
        if not salario_base and payroll is not None:
            salario_base = _as_float(payroll.gross_salary)

        proventos = _get_first_number(
            payroll_additional,
            ["Total de Proventos", "TOTAL_PROVENTOS", "Total Proventos"],
        )
        if not proventos and payroll is not None:
            proventos = _as_float(payroll.gross_salary)
        if not proventos:
            proventos = _sum_numeric_payload(payroll_earnings)

        liquido = _get_first_number(
            payroll_additional,
            ["Liquido de Calculo", "LIQ_A_RECEBER", "Liquido"],
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
        "O": 16,
        "P": 16,
        "Q": 14,
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
) -> Tuple[bytes, int, str]:
    """Gera o xlsx de relatorio estrategico de infraestrutura e retorna bytes, total de linhas e nome sugerido."""
    employees = _active_employees_for_month(session, company=company, year=year, month=month)
    payroll = _latest_payroll_by_employee(session, company=company, year=year, month=month)
    benefits = _latest_benefits_by_employee(session, company=company, year=year, month=month)

    rows = _build_export_rows(employees, payroll, benefits, company=company)
    xlsx_bytes = _write_xlsx(rows, company=company, year=year, month=month)
    filename = f"relatorio_estrategico_{company}_{year}-{month:02d}.xlsx"
    return xlsx_bytes, len(rows), filename
