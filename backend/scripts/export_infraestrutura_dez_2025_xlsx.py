"""Script de conveniencia para gerar XLSX estrategico de infraestrutura (0059, dez/2025)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.services.exportable_reports import build_infra_analytics_xlsx


TARGET_COMPANY = "0059"
TARGET_YEAR = 2025
TARGET_MONTH = 12


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_output_path() -> Path:
    return _project_root() / "exports" / f"infraestrutura_{TARGET_COMPANY}_{TARGET_YEAR}-{TARGET_MONTH:02d}.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera XLSX com colaboradores ativos da infraestrutura em dez/2025")
    parser.add_argument("--output", type=Path, default=_default_output_path(), help="Caminho do arquivo XLSX de saída")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        xlsx_bytes, total_rows, _ = build_infra_analytics_xlsx(
            session,
            year=TARGET_YEAR,
            month=TARGET_MONTH,
            company=TARGET_COMPANY,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(xlsx_bytes)

        print(f"OK: {total_rows} colaborador(es) exportado(s) para {args.output}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())