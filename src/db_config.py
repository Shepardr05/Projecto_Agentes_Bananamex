"""
db_config.py -- Conexion a PostgreSQL.

MODO POR DEFECTO (USE_EMBEDDED_DB=1): PostgreSQL EMBEBIDO. Se instala con `pip`
(paquete pixeltable-pgserver), arranca solo y guarda sus datos en una carpeta FUERA del
proyecto (en Windows: %LOCALAPPDATA%\\data-steward\\pgdata; asi OneDrive no lo sincroniza).
No necesitas Docker ni instalar PostgreSQL.

MODO EXTERNO (USE_EMBEDDED_DB=0): usa un PostgreSQL que ya tengas, con estas variables:
  PGHOST, PGPORT, POSTGRES_USER, POSTGRES_PASSWORD (admin, solo para cargar la BD)
  POSTGRES_DB, PGUSER, PGPASSWORD (rol de solo lectura que usa el agente)
"""
from __future__ import annotations

import os
from pathlib import Path

from psycopg.conninfo import conninfo_to_dict

RO_USER = "steward_ro"
_server = None


def use_embedded() -> bool:
    return os.getenv("USE_EMBEDDED_DB", "1").lower() not in ("0", "false", "no")


def db_name() -> str:
    return os.getenv("POSTGRES_DB", "banco_sintetico")


def data_dir() -> Path:
    if os.getenv("PGDATA_DIR"):
        return Path(os.environ["PGDATA_DIR"])
    root = Path(os.environ["LOCALAPPDATA"]) if os.name == "nt" and os.getenv("LOCALAPPDATA") else Path.home()
    return root / ("data-steward" if os.name == "nt" else ".data-steward") / "pgdata"


def _embedded_server():
    """Arranca (o reutiliza) el PostgreSQL embebido. cleanup_mode=None: sigue vivo al
    terminar el script, asi los servidores MCP y el agente comparten la misma instancia."""
    global _server
    if _server is None:
        import pixeltable_pgserver as pgserver

        d = data_dir()
        d.parent.mkdir(parents=True, exist_ok=True)
        _server = pgserver.get_server(d, cleanup_mode=None)
    return _server


def ensure_db() -> None:
    """Garantiza que el PostgreSQL embebido este corriendo (no hace nada en modo externo)."""
    if use_embedded():
        _embedded_server()


def stop_db() -> None:
    """Detiene el PostgreSQL embebido (pg_ctl stop). NO borra los datos."""
    if use_embedded():
        _embedded_server()._stop()


def admin_conninfo(dbname: str | None = None) -> dict:
    """Credenciales de administrador (solo para crear/cargar la BD)."""
    if use_embedded():
        info = conninfo_to_dict(_embedded_server().get_uri())
        info.pop("password", None)
        info["dbname"] = dbname or "postgres"
        return info
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "dbname": dbname or "postgres",
    }


def readonly_conninfo() -> dict:
    """Credenciales del rol de SOLO LECTURA (lo unico que usa el agente)."""
    if use_embedded():
        info = conninfo_to_dict(_embedded_server().get_uri())
        info.pop("password", None)
        info["user"] = RO_USER
        info["dbname"] = db_name()
        return info
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", "5432"),
        "user": os.getenv("PGUSER", RO_USER),
        "password": os.getenv("PGPASSWORD", ""),
        "dbname": os.getenv("PGDATABASE", db_name()),
    }
