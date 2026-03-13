from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_ROOT = SCRIPT_DIR.parent
BACKEND_ROOT = SCRIPTS_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent


def ensure_backend_on_path() -> None:
    backend_path = str(BACKEND_ROOT)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_repo_env() -> None:
    _load_env_file(PROJECT_ROOT / ".env")
    _load_env_file(BACKEND_ROOT / ".env")


def get_database_url() -> str:
    load_repo_env()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD", "")
    db_port = os.getenv("DB_PORT", "5432")

    if db_host and db_name and db_user:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    raise RuntimeError(
        "DATABASE_URL não configurada. Defina DATABASE_URL ou DB_HOST/DB_NAME/DB_USER/DB_PASSWORD."
    )


def get_api_base_url() -> str:
    load_repo_env()
    return os.getenv("SCRIPT_API_URL", "http://localhost:8002").rstrip("/")


def get_api_credentials() -> Tuple[str, str]:
    load_repo_env()

    username = os.getenv("SCRIPT_API_USERNAME", "admin")
    password = os.getenv("SCRIPT_API_PASSWORD")
    if not password:
        raise RuntimeError("Defina SCRIPT_API_PASSWORD para executar scripts que autenticam na API.")

    return username, password


def get_analytics_dir(subdir: str = "Empreendimentos") -> Path:
    load_repo_env()

    custom_dir = os.getenv("SCRIPT_ANALYTICS_DIR")
    if custom_dir:
        return Path(custom_dir)

    return PROJECT_ROOT / "Analiticos" / subdir