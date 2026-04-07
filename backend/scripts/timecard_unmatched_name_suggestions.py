"""
Generate name-based match suggestions for unmatched timecard rows.

Input default:
    tests/timecard/timecard_unmatched_dry_run_unique.csv

Outputs default (same folder):
    - timecard_unmatched_name_match_suggestions.csv
    - timecard_unmatched_name_match_best.csv
    - timecard_unmatched_name_match_report.json

Usage:
    cd backend
    python -m scripts.timecard_unmatched_name_suggestions
"""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List

from app.models.employee import Employee
from app.services.runtime_compat import SessionLocal


@dataclass
class EmployeeIndexRow:
    employee_id: int
    unique_id: str
    registration_number: str
    company_code: str
    name: str
    normalized_name: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalize_name(value: str) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = "".join(ch if ch.isalnum() else " " for ch in text)
    return " ".join(text.split())


def _token_sort(text: str) -> str:
    return " ".join(sorted(text.split()))


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0

    ratio_raw = SequenceMatcher(None, a, b).ratio()
    ratio_sorted = SequenceMatcher(None, _token_sort(a), _token_sort(b)).ratio()

    a_tokens = set(a.split())
    b_tokens = set(b.split())
    overlap = len(a_tokens & b_tokens)
    token_score = overlap / max(1, len(a_tokens))

    score = (ratio_raw * 0.45) + (ratio_sorted * 0.45) + (token_score * 0.10)
    return round(score * 100, 2)


def _default_input_csv() -> Path:
    return _project_root() / "tests" / "timecard" / "timecard_unmatched_dry_run_unique.csv"


def _load_employees() -> List[EmployeeIndexRow]:
    db = SessionLocal()
    try:
        rows = db.query(Employee).all()
        result: List[EmployeeIndexRow] = []
        for emp in rows:
            name = str(emp.name or "").strip()
            normalized = _normalize_name(name)
            if not normalized:
                continue
            result.append(
                EmployeeIndexRow(
                    employee_id=int(emp.id),
                    unique_id=str(emp.unique_id or ""),
                    registration_number=str(emp.registration_number or ""),
                    company_code=str(emp.company_code or ""),
                    name=name,
                    normalized_name=normalized,
                )
            )
        return result
    finally:
        db.close()


def _read_unmatched_unique(input_csv: Path) -> List[Dict[str, str]]:
    with input_csv.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


def _build_suggestions(
    unmatched_rows: List[Dict[str, str]],
    employees: List[EmployeeIndexRow],
    top_n: int,
    min_score: float,
) -> List[Dict[str, str]]:
    suggestions: List[Dict[str, str]] = []

    for row in unmatched_rows:
        company_inferred = str(row.get("company_inferred", "")).strip()
        unmatched_name = str(row.get("employee_name_file", "")).strip()
        normalized_unmatched = _normalize_name(unmatched_name)

        scored = []
        for emp in employees:
            score = _similarity(normalized_unmatched, emp.normalized_name)
            if score < min_score:
                continue

            company_match = "yes" if company_inferred and (company_inferred == emp.company_code) else "no"
            matricula_match = "yes" if str(row.get("employee_number_digits", "")).strip() and (
                str(row.get("employee_number_digits", "")).strip() == str(emp.registration_number).lstrip("0")
                or str(row.get("employee_number_digits", "")).strip() == str(emp.registration_number)
                or str(row.get("employee_number_digits", "")).strip() == str(emp.unique_id).lstrip("0")
                or str(row.get("employee_number_digits", "")).strip() == str(emp.unique_id)
            ) else "no"

            boosted_score = score
            if company_match == "yes":
                boosted_score += 3.0
            if matricula_match == "yes":
                boosted_score += 25.0
            boosted_score = round(min(boosted_score, 100.0), 2)

            scored.append((boosted_score, score, company_match, matricula_match, emp))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        for rank, (boosted, base_score, company_match, matricula_match, emp) in enumerate(scored[: max(1, top_n)], start=1):
            suggestions.append(
                {
                    "company_inferred": company_inferred,
                    "employee_number_file": str(row.get("employee_number_file", "")).strip(),
                    "employee_number_digits": str(row.get("employee_number_digits", "")).strip(),
                    "employee_name_file": unmatched_name,
                    "occurrences": str(row.get("occurrences", "")),
                    "candidate_rank": str(rank),
                    "candidate_employee_id": str(emp.employee_id),
                    "candidate_unique_id": emp.unique_id,
                    "candidate_registration_number": emp.registration_number,
                    "candidate_company_code": emp.company_code,
                    "candidate_name": emp.name,
                    "score_base": f"{base_score:.2f}",
                    "score_final": f"{boosted:.2f}",
                    "company_match": company_match,
                    "matricula_match": matricula_match,
                }
            )

    return suggestions


def _write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate match suggestions for unmatched timecard names")
    parser.add_argument("--input-csv", type=Path, default=_default_input_csv())
    parser.add_argument("--output-dir", type=Path, default=_default_input_csv().parent)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=62.0)
    args = parser.parse_args()

    input_csv: Path = args.input_csv
    output_dir: Path = args.output_dir
    top_n: int = max(1, min(int(args.top_n), 20))
    min_score: float = max(0.0, min(float(args.min_score), 100.0))

    if not input_csv.exists():
        print(f"ERROR: input CSV not found: {input_csv}")
        return 1

    unmatched_rows = _read_unmatched_unique(input_csv)
    employees = _load_employees()

    suggestions = _build_suggestions(unmatched_rows, employees, top_n=top_n, min_score=min_score)

    suggestion_csv = output_dir / "timecard_unmatched_name_match_suggestions.csv"
    best_csv = output_dir / "timecard_unmatched_name_match_best.csv"
    report_json = output_dir / "timecard_unmatched_name_match_report.json"

    if suggestions:
        fieldnames = list(suggestions[0].keys())
        _write_csv(suggestion_csv, suggestions, fieldnames)
    else:
        _write_csv(suggestion_csv, [], [
            "company_inferred", "employee_number_file", "employee_number_digits", "employee_name_file",
            "occurrences", "candidate_rank", "candidate_employee_id", "candidate_unique_id",
            "candidate_registration_number", "candidate_company_code", "candidate_name",
            "score_base", "score_final", "company_match", "matricula_match"
        ])

    best_map: Dict[str, Dict[str, str]] = {}
    for row in suggestions:
        key = f"{row['company_inferred']}|{row['employee_number_digits']}|{_normalize_name(row['employee_name_file'])}"
        if key not in best_map:
            best_map[key] = row
    best_rows = list(best_map.values())

    if best_rows:
        _write_csv(best_csv, best_rows, list(best_rows[0].keys()))
    else:
        _write_csv(best_csv, [], [
            "company_inferred", "employee_number_file", "employee_number_digits", "employee_name_file",
            "occurrences", "candidate_rank", "candidate_employee_id", "candidate_unique_id",
            "candidate_registration_number", "candidate_company_code", "candidate_name",
            "score_base", "score_final", "company_match", "matricula_match"
        ])

    payload = {
        "generated_at": datetime.now().isoformat(),
        "input_csv": str(input_csv),
        "employees_indexed": len(employees),
        "unmatched_unique_rows": len(unmatched_rows),
        "suggestions_total": len(suggestions),
        "best_rows": len(best_rows),
        "top_n": top_n,
        "min_score": min_score,
        "outputs": {
            "suggestions_csv": str(suggestion_csv),
            "best_csv": str(best_csv),
            "report_json": str(report_json),
        },
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    with report_json.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)

    print("Name match suggestion files generated.")
    print(f"Suggestions CSV: {suggestion_csv}")
    print(f"Best CSV:        {best_csv}")
    print(f"Report JSON:     {report_json}")
    print(f"Suggestions: {len(suggestions)}")
    print(f"Best rows:   {len(best_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
