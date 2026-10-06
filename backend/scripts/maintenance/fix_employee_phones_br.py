import argparse
import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from common import ensure_backend_on_path

ensure_backend_on_path()

from app.models.base import SessionLocal
from app.models.employee import Employee


VALID_BRAZIL_DDDS = {
    "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "21", "22", "24", "27", "28",
    "31", "32", "33", "34", "35", "37", "38",
    "41", "42", "43", "44", "45", "46",
    "47", "48", "49",
    "51", "53", "54", "55",
    "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "71", "73", "74", "75", "77", "79",
    "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "91", "92", "93", "94", "95", "96", "97", "98", "99",
}


@dataclass
class FixResult:
    normalized: str
    changed: bool
    reason: str


def _digits_only(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_br_phone(phone: Optional[str]) -> FixResult:
    raw = _digits_only(phone)
    if not raw:
        return FixResult(normalized="", changed=False, reason="empty")

    had_country_code = raw.startswith("55")
    core = raw[2:] if had_country_code else raw

    # Core must start with a valid Brazilian DDD.
    if len(core) < 10:
        return FixResult(normalized=raw, changed=False, reason="too_short")

    ddd = core[:2]
    if ddd not in VALID_BRAZIL_DDDS:
        return FixResult(normalized=raw, changed=False, reason="invalid_ddd")

    removed_zero_after_ddd = False
    if len(core) >= 3 and core[2] == "0":
        core = core[:2] + core[3:]
        removed_zero_after_ddd = True

    # Accept only common BR local lengths after cleanup: DDD+8 or DDD+9.
    if len(core) not in (10, 11):
        return FixResult(normalized=raw, changed=False, reason="unsupported_length")

    normalized = f"55{core}"
    changed = normalized != raw

    if not changed:
        return FixResult(normalized=normalized, changed=False, reason="already_ok")

    if removed_zero_after_ddd and not had_country_code:
        reason = "added_55_and_removed_zero_after_ddd"
    elif removed_zero_after_ddd and had_country_code:
        reason = "removed_zero_after_ddd"
    elif not had_country_code:
        reason = "added_55"
    else:
        reason = "normalized"

    return FixResult(normalized=normalized, changed=True, reason=reason)


def run(apply_changes: bool, limit: Optional[int], export_csv: bool) -> None:
    db = SessionLocal()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(__file__).parent / f"phone_fix_report_{now}.csv"

    scanned = 0
    changed = 0
    unchanged = 0
    invalid = 0

    rows_to_export = []

    try:
        query = db.query(Employee).filter(Employee.phone.isnot(None)).order_by(Employee.id.asc())
        if limit:
            query = query.limit(limit)

        employees = query.all()

        for emp in employees:
            scanned += 1
            original_phone = emp.phone or ""
            result = normalize_br_phone(original_phone)

            if result.reason in ("too_short", "invalid_ddd", "unsupported_length"):
                invalid += 1

            if result.changed:
                changed += 1
                rows_to_export.append(
                    {
                        "employee_id": emp.id,
                        "unique_id": emp.unique_id,
                        "name": emp.name,
                        "old_phone": original_phone,
                        "new_phone": result.normalized,
                        "reason": result.reason,
                    }
                )
                if apply_changes:
                    emp.phone = result.normalized
            else:
                unchanged += 1

        if apply_changes:
            db.commit()

        if export_csv and rows_to_export:
            with report_path.open("w", newline="", encoding="utf-8-sig") as fp:
                writer = csv.DictWriter(
                    fp,
                    fieldnames=["employee_id", "unique_id", "name", "old_phone", "new_phone", "reason"],
                )
                writer.writeheader()
                writer.writerows(rows_to_export)

        mode = "APPLY" if apply_changes else "DRY-RUN"
        print(f"Modo: {mode}")
        print(f"Registros analisados: {scanned}")
        print(f"Registros alterados: {changed}")
        print(f"Registros sem alteração: {unchanged}")
        print(f"Registros com formato não suportado: {invalid}")

        if rows_to_export:
            print("Amostra das primeiras 10 alterações:")
            for row in rows_to_export[:10]:
                print(
                    f"  ID {row['employee_id']} | {row['old_phone']} -> {row['new_phone']} "
                    f"({row['reason']})"
                )

        if export_csv and rows_to_export:
            print(f"Relatório CSV: {report_path}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corrige telefones BR no formato DDD0NUMERO para 55DDDNUMERO, removendo o 0 após DDD."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica alterações no banco (por padrão apenas simula).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita a quantidade de registros analisados (útil para teste).",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Não gerar CSV com alterações.",
    )

    args = parser.parse_args()
    run(apply_changes=args.apply, limit=args.limit, export_csv=not args.no_csv)


if __name__ == "__main__":
    main()
