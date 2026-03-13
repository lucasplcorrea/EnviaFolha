import argparse
import os
from typing import Any, Dict, List, Tuple
from datetime import datetime
import re

from common import load_repo_env

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


load_repo_env()


def build_url(host: str, port: str, db_name: str, user: str, password: str) -> str:
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_common_columns(prod_engine: Engine, test_engine: Engine) -> List[str]:
    q = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'employees'
        ORDER BY ordinal_position
        """
    )
    with prod_engine.connect() as conn:
        prod_cols = [r[0] for r in conn.execute(q)]
    with test_engine.connect() as conn:
        test_cols = [r[0] for r in conn.execute(q)]

    common = [c for c in prod_cols if c in test_cols]
    if "id" not in common or "unique_id" not in common or "cpf" not in common:
        raise RuntimeError("Tabela employees sem colunas obrigatorias (id, unique_id, cpf).")
    return common


def fetch_rows(engine: Engine, columns: List[str]) -> List[Dict[str, Any]]:
    cols = ", ".join(columns)
    q = text(f"SELECT {cols} FROM public.employees ORDER BY id")
    with engine.connect() as conn:
        rows = conn.execute(q).mappings().all()
    return [dict(r) for r in rows]


def normalize(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def normalize_uid_for_match(v: Any) -> str:
    uid = normalize(v)
    if not uid:
        return ""
    stripped = uid.lstrip("0")
    return stripped if stripped else "0"


def normalize_cpf_for_match(v: Any) -> str:
    cpf = normalize(v)
    if not cpf:
        return ""
    return re.sub(r"\D", "", cpf)


def sync_employees(prod_rows: List[Dict[str, Any]], test_rows: List[Dict[str, Any]], apply: bool, test_engine: Engine) -> Dict[str, int]:
    stats = {
        "prod_total": len(prod_rows),
        "test_before": len(test_rows),
        "updated_by_unique_id": 0,
        "updated_by_cpf": 0,
        "updated_by_unique_id_normalized": 0,
        "updated_by_cpf_normalized": 0,
        "inserted": 0,
        "deactivated_missing": 0,
        "skipped_invalid": 0,
        "test_after": 0,
    }
    pending_inserts: List[Tuple[str, str]] = []

    test_by_unique_id: Dict[str, Dict[str, Any]] = {}
    test_by_cpf: Dict[str, Dict[str, Any]] = {}
    test_by_unique_id_norm: Dict[str, Dict[str, Any]] = {}
    test_by_cpf_norm: Dict[str, Dict[str, Any]] = {}
    for row in test_rows:
        uid = normalize(row.get("unique_id"))
        cpf = normalize(row.get("cpf"))
        if uid:
            test_by_unique_id[uid] = row
        if cpf:
            test_by_cpf[cpf] = row
        uid_norm = normalize_uid_for_match(uid)
        cpf_norm = normalize_cpf_for_match(cpf)
        if uid_norm and uid_norm not in test_by_unique_id_norm:
            test_by_unique_id_norm[uid_norm] = row
        if cpf_norm and cpf_norm not in test_by_cpf_norm:
            test_by_cpf_norm[cpf_norm] = row

    touched_test_ids = set()

    cols = list(prod_rows[0].keys()) if prod_rows else []
    cols_without_id = [c for c in cols if c != "id"]

    if apply:
        session = Session(test_engine)
    else:
        session = None

    try:
        for prod in prod_rows:
            uid = normalize(prod.get("unique_id"))
            cpf = normalize(prod.get("cpf"))
            uid_norm = normalize_uid_for_match(uid)
            cpf_norm = normalize_cpf_for_match(cpf)

            if not uid or not cpf:
                stats["skipped_invalid"] += 1
                continue

            target = test_by_unique_id.get(uid)
            match_type = "unique_id"
            if not target:
                target = test_by_cpf.get(cpf)
                match_type = "cpf"
            if not target and uid_norm:
                target = test_by_unique_id_norm.get(uid_norm)
                match_type = "unique_id_normalized"
            if not target and cpf_norm:
                target = test_by_cpf_norm.get(cpf_norm)
                match_type = "cpf_normalized"

            if target:
                test_id = target["id"]
                touched_test_ids.add(test_id)
                if apply:
                    set_clause = ", ".join([f"{c} = :{c}" for c in cols_without_id])
                    update_sql = text(f"UPDATE public.employees SET {set_clause} WHERE id = :target_id")
                    params = {c: prod.get(c) for c in cols_without_id}
                    params["target_id"] = test_id
                    session.execute(update_sql, params)

                if match_type == "unique_id":
                    stats["updated_by_unique_id"] += 1
                elif match_type == "cpf":
                    stats["updated_by_cpf"] += 1
                elif match_type == "unique_id_normalized":
                    stats["updated_by_unique_id_normalized"] += 1
                elif match_type == "cpf_normalized":
                    stats["updated_by_cpf_normalized"] += 1
            else:
                if apply:
                    ins_cols = ", ".join(cols_without_id)
                    ins_vals = ", ".join([f":{c}" for c in cols_without_id])
                    insert_sql = text(f"INSERT INTO public.employees ({ins_cols}) VALUES ({ins_vals})")
                    params = {c: prod.get(c) for c in cols_without_id}
                    session.execute(insert_sql, params)
                stats["inserted"] += 1
                pending_inserts.append((uid, cpf))

        missing_test_ids = {
            r["id"]
            for r in test_rows
            if r["id"] not in touched_test_ids
        }

        if missing_test_ids:
            if apply:
                deactivate_sql = text(
                    """
                    UPDATE public.employees
                    SET is_active = FALSE
                    WHERE id = ANY(:missing_ids)
                    """
                )
                session.execute(deactivate_sql, {"missing_ids": list(missing_test_ids)})
            stats["deactivated_missing"] = len(missing_test_ids)

        if apply:
            session.commit()

        with test_engine.connect() as conn:
            stats["test_after"] = conn.execute(text("SELECT COUNT(*) FROM public.employees")).scalar_one()

        stats["pending_inserts_sample"] = pending_inserts[:10]
        return stats
    except Exception:
        if apply and session is not None:
            session.rollback()
        raise
    finally:
        if session is not None:
            session.close()


def set_sequence_to_max_id(test_engine: Engine, apply: bool) -> int:
    q = text(
        """
        SELECT setval(
            pg_get_serial_sequence('public.employees', 'id'),
            COALESCE((SELECT MAX(id) FROM public.employees), 1),
            true
        )
        """
    )
    if apply:
        with test_engine.begin() as conn:
            return int(conn.execute(q).scalar_one())
    with test_engine.connect() as conn:
        return int(conn.execute(text("SELECT COALESCE(MAX(id), 1) FROM public.employees")).scalar_one())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sincroniza employees de producao para teste.")
    parser.add_argument("--test-host", default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--test-port", default=os.getenv("DB_PORT", "5432"))
    parser.add_argument("--test-db", default=os.getenv("DB_NAME", "enviafolha_db"))
    parser.add_argument("--test-user", default=os.getenv("DB_USER", "enviafolha_user"))
    parser.add_argument("--test-password", default=os.getenv("DB_PASSWORD", ""))

    parser.add_argument("--prod-host", default=os.getenv("PROD_DB_HOST", ""))
    parser.add_argument("--prod-port", default=os.getenv("DB_PORT", "5432"))
    parser.add_argument("--prod-db", default=os.getenv("DB_NAME", "enviafolha_db"))
    parser.add_argument("--prod-user", default=os.getenv("DB_USER", "enviafolha_user"))
    parser.add_argument("--prod-password", default=os.getenv("PROD_DB_PASSWORD", ""))

    parser.add_argument("--apply", action="store_true", help="Aplica alteracoes no banco de teste")
    return parser.parse_args()


def backup_test_employees(test_engine: Engine) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_table = f"employees_backup_{stamp}"
    with test_engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS public.{backup_table}"))
        conn.execute(text(f"CREATE TABLE public.{backup_table} AS TABLE public.employees"))
    return backup_table


def main() -> None:
    args = parse_args()

    if not args.prod_host:
        raise ValueError("Informe --prod-host ou defina PROD_DB_HOST.")

    if not args.prod_password:
        raise ValueError("Informe --prod-password ou defina PROD_DB_PASSWORD.")

    test_url = build_url(args.test_host, args.test_port, args.test_db, args.test_user, args.test_password)
    prod_url = build_url(args.prod_host, args.prod_port, args.prod_db, args.prod_user, args.prod_password)

    prod_engine = create_engine(prod_url, pool_pre_ping=True)
    test_engine = create_engine(test_url, pool_pre_ping=True)

    common_columns = get_common_columns(prod_engine, test_engine)
    prod_rows = fetch_rows(prod_engine, common_columns)
    test_rows = fetch_rows(test_engine, common_columns)

    backup_table = None
    if args.apply:
        backup_table = backup_test_employees(test_engine)

    stats = sync_employees(prod_rows, test_rows, args.apply, test_engine)
    seq_value = set_sequence_to_max_id(test_engine, args.apply)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Modo: {mode}")
    print(f"Colunas comuns usadas: {len(common_columns)}")
    print(f"Produção (employees): {stats['prod_total']}")
    print(f"Teste antes (employees): {stats['test_before']}")
    print(f"Atualizados por unique_id: {stats['updated_by_unique_id']}")
    print(f"Atualizados por cpf: {stats['updated_by_cpf']}")
    print(f"Atualizados por unique_id normalizado: {stats['updated_by_unique_id_normalized']}")
    print(f"Atualizados por cpf normalizado: {stats['updated_by_cpf_normalized']}")
    print(f"Inseridos: {stats['inserted']}")
    print(f"Desativados (existem so no teste): {stats['deactivated_missing']}")
    print(f"Ignorados por dados invalidos: {stats['skipped_invalid']}")
    print(f"Teste depois (employees): {stats['test_after']}")
    print(f"Sequencia employees.id ajustada para: {seq_value}")
    pending_sample = stats.get("pending_inserts_sample") or []
    if pending_sample:
        print("Amostra de possiveis insercoes pendentes (unique_id, cpf):")
        for uid, cpf in pending_sample:
            print(f"  - {uid} | {cpf}")
    if backup_table:
        print(f"Backup criado em: public.{backup_table}")


if __name__ == "__main__":
    main()
