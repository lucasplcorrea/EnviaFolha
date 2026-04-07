"""
Batch dry-run for timecard XLSX files, exporting unmatched employees.

Usage:
    cd backend
    python -m scripts.timecard_dry_run_unmatched

Optional args:
    --input-dir  Path to folder with XLSX files
    --output-dir Path to write CSV/JSON outputs
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import openpyxl

from app.services.runtime_compat import SessionLocal
from app.services.timecard_xlsx_processor import TimecardXLSXProcessor


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_input_dir() -> Path:
    return _project_root() / "tests" / "timecard"


def _list_xlsx_files(input_dir: Path) -> List[Path]:
    files = [
        file_path
        for file_path in sorted(input_dir.glob("*.xlsx"))
        if not file_path.name.startswith("~$")
    ]
    return files


def _extract_unmatched_from_file(file_path: Path) -> Dict:
    db = SessionLocal()
    processor = TimecardXLSXProcessor(db=db, user_id=None)

    unmatched_rows: List[Dict] = []
    matched_rows = 0
    scanned_rows = 0

    try:
        workbook = openpyxl.load_workbook(str(file_path), data_only=True)
        sheet = workbook.active

        header_row = processor._find_header_row(sheet)
        if not header_row:
            return {
                "file": file_path.name,
                "success": False,
                "error": "header_not_found",
                "scanned_rows": 0,
                "matched_rows": 0,
                "unmatched_rows": [],
            }

        headers = processor._read_headers(sheet, header_row)
        column_indices = processor._resolve_column_indices(headers)
        validation = processor._validate_headers(column_indices)
        if not validation.get("valid"):
            return {
                "file": file_path.name,
                "success": False,
                "error": validation.get("error", "invalid_headers"),
                "scanned_rows": 0,
                "matched_rows": 0,
                "unmatched_rows": [],
            }

        for row_idx in range(header_row + 1, sheet.max_row + 1):
            row_data = processor._extract_timecard_row_data(sheet, row_idx, column_indices)
            if not row_data:
                continue

            scanned_rows += 1
            preview = processor._preview_timecard_row(row_data, period=None)

            if preview["employee_found"]:
                matched_rows += 1
                continue

            unmatched_rows.append(
                {
                    "source_file": file_path.name,
                    "row_number": row_idx,
                    "company_inferred": row_data["company"],
                    "employee_number_file": row_data["employee_number"],
                    "employee_number_digits": row_data["employee_number_clean"],
                    "employee_name_file": row_data["employee_name"],
                }
            )

        workbook.close()

        return {
            "file": file_path.name,
            "success": True,
            "error": None,
            "scanned_rows": scanned_rows,
            "matched_rows": matched_rows,
            "unmatched_rows": unmatched_rows,
        }
    finally:
        db.close()


def _write_csv(file_path: Path, rows: List[Dict]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_file",
        "row_number",
        "company_inferred",
        "employee_number_file",
        "employee_number_digits",
        "employee_name_file",
    ]
    with file_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(file_path: Path, payload: Dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch dry-run unmatched employees for timecard XLSX files")
    parser.add_argument("--input-dir", type=Path, default=_default_input_dir())
    parser.add_argument("--output-dir", type=Path, default=_default_input_dir())
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"ERROR: input directory not found: {input_dir}")
        return 1

    xlsx_files = _list_xlsx_files(input_dir)
    if not xlsx_files:
        print(f"ERROR: no XLSX files found in: {input_dir}")
        return 1

    run_started = datetime.now()
    files_report: List[Dict] = []
    unmatched_all: List[Dict] = []

    print(f"Found {len(xlsx_files)} XLSX file(s). Running dry-run check...")
    for file_path in xlsx_files:
        report = _extract_unmatched_from_file(file_path)
        files_report.append(
            {
                "file": report["file"],
                "success": report["success"],
                "error": report["error"],
                "scanned_rows": report["scanned_rows"],
                "matched_rows": report["matched_rows"],
                "unmatched_count": len(report["unmatched_rows"]),
            }
        )
        unmatched_all.extend(report["unmatched_rows"])
        print(
            f" - {report['file']}: scanned={report['scanned_rows']}, "
            f"matched={report['matched_rows']}, unmatched={len(report['unmatched_rows'])}"
        )

    unique_map: Dict[str, Dict] = {}
    for row in unmatched_all:
        key = f"{row['company_inferred']}|{row['employee_number_digits']}|{row['employee_name_file'].strip().lower()}"
        if key not in unique_map:
            unique_map[key] = {
                "company_inferred": row["company_inferred"],
                "employee_number_file": row["employee_number_file"],
                "employee_number_digits": row["employee_number_digits"],
                "employee_name_file": row["employee_name_file"],
                "first_seen_file": row["source_file"],
                "occurrences": 1,
            }
        else:
            unique_map[key]["occurrences"] += 1

    unmatched_unique = sorted(
        unique_map.values(),
        key=lambda item: (
            item["company_inferred"],
            item["employee_name_file"].lower(),
            item["employee_number_digits"],
        ),
    )

    csv_detailed = output_dir / "timecard_unmatched_dry_run_detailed.csv"
    csv_unique = output_dir / "timecard_unmatched_dry_run_unique.csv"
    json_report = output_dir / "timecard_unmatched_dry_run_report.json"

    _write_csv(csv_detailed, unmatched_all)

    csv_unique.parent.mkdir(parents=True, exist_ok=True)
    with csv_unique.open("w", encoding="utf-8", newline="") as csv_file:
        fieldnames = [
            "company_inferred",
            "employee_number_file",
            "employee_number_digits",
            "employee_name_file",
            "first_seen_file",
            "occurrences",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in unmatched_unique:
            writer.writerow(row)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "run_duration_seconds": round((datetime.now() - run_started).total_seconds(), 3),
        "input_dir": str(input_dir),
        "total_files": len(xlsx_files),
        "files": files_report,
        "unmatched_total_rows": len(unmatched_all),
        "unmatched_unique_count": len(unmatched_unique),
        "outputs": {
            "detailed_csv": str(csv_detailed),
            "unique_csv": str(csv_unique),
            "report_json": str(json_report),
        },
        "unmatched_unique": unmatched_unique,
    }
    _write_json(json_report, payload)

    print("\nCompleted dry-run unmatched report generation.")
    print(f"Detailed CSV: {csv_detailed}")
    print(f"Unique CSV:   {csv_unique}")
    print(f"JSON report:  {json_report}")
    print(f"Unmatched rows (detailed): {len(unmatched_all)}")
    print(f"Unmatched unique people:   {len(unmatched_unique)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
