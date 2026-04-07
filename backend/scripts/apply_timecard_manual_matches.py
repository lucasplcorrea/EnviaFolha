"""
Apply manual timecard matches from a CSV file.

Default input:
    tests/timecard/aplicar registros.csv

Usage:
    cd backend
    python -m scripts.apply_timecard_manual_matches            # dry-run (default)
    python -m scripts.apply_timecard_manual_matches --apply    # apply updates
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from app.models.employee import Employee
from app.models.timecard import TimecardData, TimecardPeriod
from app.services.runtime_compat import SessionLocal


@dataclass
class MatchRow:
    company_inferred: str
    employee_number_file: str
    employee_name_file: str
    candidate_employee_id: int
    candidate_name: str
    candidate_unique_id: str
    candidate_company_code: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_input_csv() -> Path:
    return _project_root() / "tests" / "timecard" / "aplicar registros.csv"


def _load_rows(input_csv: Path) -> List[MatchRow]:
    with input_csv.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows: List[MatchRow] = []
        for item in reader:
            rows.append(
                MatchRow(
                    company_inferred=str(item.get("company_inferred", "")).strip(),
                    employee_number_file=str(item.get("employee_number_file", "")).strip(),
                    employee_name_file=str(item.get("employee_name_file", "")).strip(),
                    candidate_employee_id=int(str(item.get("candidate_employee_id", "0") or "0")),
                    candidate_name=str(item.get("candidate_name", "")).strip(),
                    candidate_unique_id=str(item.get("candidate_unique_id", "")).strip(),
                    candidate_company_code=str(item.get("candidate_company_code", "")).strip(),
                )
            )
        return rows


def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply manual timecard matches")
    parser.add_argument("--input-csv", type=Path, default=_default_input_csv())
    parser.add_argument("--output-dir", type=Path, default=_default_input_csv().parent)
    parser.add_argument("--apply", action="store_true", help="Apply updates (default is dry-run)")
    args = parser.parse_args()

    input_csv: Path = args.input_csv
    output_dir: Path = args.output_dir
    apply_mode: bool = bool(args.apply)

    if not input_csv.exists():
        print(f"ERROR: input CSV not found: {input_csv}")
        return 1

    requested = _load_rows(input_csv)
    if not requested:
        print("ERROR: input CSV has no rows")
        return 1

    db = SessionLocal()
    started = datetime.now()

    results: List[Dict] = []
    total_rows_found = 0
    total_rows_would_update = 0
    total_rows_updated = 0
    total_overtime_hours = 0.0
    total_night_hours = 0.0

    try:
        for req in requested:
            candidate = db.query(Employee).filter(Employee.id == req.candidate_employee_id).first()
            if not candidate:
                results.append(
                    {
                        "employee_number_file": req.employee_number_file,
                        "employee_name_file": req.employee_name_file,
                        "candidate_employee_id": req.candidate_employee_id,
                        "candidate_name": req.candidate_name,
                        "status": "candidate_not_found",
                        "timecard_rows_found": 0,
                        "rows_to_update": 0,
                        "rows_updated": 0,
                        "overtime_hours_sum": "0.00",
                        "night_hours_sum": "0.00",
                        "periods": "",
                        "notes": "Employee id inexistente no banco",
                    }
                )
                continue

            query = db.query(TimecardData, TimecardPeriod).outerjoin(
                TimecardPeriod, TimecardPeriod.id == TimecardData.period_id
            ).filter(
                TimecardData.employee_number == req.employee_number_file,
                TimecardData.company == req.company_inferred,
            )

            rows = query.order_by(TimecardPeriod.year.desc(), TimecardPeriod.month.desc(), TimecardData.id.desc()).all()
            total_rows_found += len(rows)

            overtime_sum = 0.0
            night_sum = 0.0
            periods: List[str] = []
            rows_to_update = 0
            rows_updated = 0

            for timecard, period in rows:
                overtime = float((timecard.overtime_50 or 0) + (timecard.overtime_100 or 0))
                night = float((timecard.night_overtime_50 or 0) + (timecard.night_overtime_100 or 0) + (timecard.night_hours or 0))
                overtime_sum += overtime
                night_sum += night

                if period and period.year and period.month:
                    periods.append(f"{period.month:02d}/{period.year}")
                else:
                    periods.append(f"period_id:{timecard.period_id}")

                if timecard.employee_id != candidate.id:
                    rows_to_update += 1
                    if apply_mode:
                        timecard.employee_id = candidate.id
                        rows_updated += 1

            total_rows_would_update += rows_to_update
            total_rows_updated += rows_updated
            total_overtime_hours += overtime_sum
            total_night_hours += night_sum

            if not rows:
                status = "timecard_not_found"
                notes = "Nenhuma linha de cartão ponto encontrada para matrícula+empresa"
            elif rows_to_update == 0:
                status = "already_linked"
                notes = "Todas as linhas já estavam vinculadas ao cadastro alvo"
            else:
                status = "updated" if apply_mode else "ready_to_update"
                notes = "Vinculo aplicado" if apply_mode else "Pronto para aplicar"

            results.append(
                {
                    "employee_number_file": req.employee_number_file,
                    "employee_name_file": req.employee_name_file,
                    "candidate_employee_id": candidate.id,
                    "candidate_name": candidate.name,
                    "candidate_unique_id": candidate.unique_id,
                    "candidate_company_code": candidate.company_code,
                    "status": status,
                    "timecard_rows_found": len(rows),
                    "rows_to_update": rows_to_update,
                    "rows_updated": rows_updated,
                    "has_overtime": "yes" if overtime_sum > 0 else "no",
                    "overtime_hours_sum": f"{overtime_sum:.2f}",
                    "night_hours_sum": f"{night_sum:.2f}",
                    "periods": " | ".join(sorted(set(periods))),
                    "notes": notes,
                }
            )

        if apply_mode:
            db.commit()
        else:
            db.rollback()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_label = "apply" if apply_mode else "dry_run"
    result_csv = output_dir / f"timecard_manual_match_{mode_label}_{timestamp}.csv"
    result_json = output_dir / f"timecard_manual_match_{mode_label}_{timestamp}.json"

    fieldnames = [
        "employee_number_file",
        "employee_name_file",
        "candidate_employee_id",
        "candidate_name",
        "candidate_unique_id",
        "candidate_company_code",
        "status",
        "timecard_rows_found",
        "rows_to_update",
        "rows_updated",
        "has_overtime",
        "overtime_hours_sum",
        "night_hours_sum",
        "periods",
        "notes",
    ]
    _write_csv(result_csv, results, fieldnames)

    summary = {
        "generated_at": datetime.now().isoformat(),
        "mode": mode_label,
        "input_csv": str(input_csv),
        "requested_matches": len(requested),
        "timecard_rows_found": total_rows_found,
        "timecard_rows_would_update": total_rows_would_update,
        "timecard_rows_updated": total_rows_updated,
        "overtime_hours_total": round(total_overtime_hours, 2),
        "night_hours_total": round(total_night_hours, 2),
        "duration_seconds": round((datetime.now() - started).total_seconds(), 3),
        "result_csv": str(result_csv),
        "rows": results,
    }

    result_json.parent.mkdir(parents=True, exist_ok=True)
    with result_json.open("w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, ensure_ascii=False, indent=2)

    print(f"Mode: {mode_label}")
    print(f"Requested matches: {len(requested)}")
    print(f"Timecard rows found: {total_rows_found}")
    print(f"Rows to update: {total_rows_would_update}")
    print(f"Rows updated: {total_rows_updated}")
    print(f"Overtime total (hours): {total_overtime_hours:.2f}")
    print(f"Night total (hours): {total_night_hours:.2f}")
    print(f"Result CSV: {result_csv}")
    print(f"Result JSON: {result_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
