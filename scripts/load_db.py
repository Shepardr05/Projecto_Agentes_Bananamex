"""
load_db.py -- Crea la base sintetica y carga los scripts del socio (sql/000..003).
Es IDEMPOTENTE: si la BD ya esta cargada correctamente, no hace nada (solo asegura el rol
de solo lectura). Usa PostgreSQL embebido por defecto (ver src/db_config.py).

    python scripts/load_db.py            # carga si hace falta
    python scripts/load_db.py --force    # borra dim/cfg y regenera TODO (cifras nuevas)
"""
import sys
from pathlib import Path

import psycopg
import psycopg.sql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")
import db_config  # noqa: E402

EXPECTED = {"cfg.fact_sdos_captacoloca_m": 120000, "cfg.fact_txn_captacoloca_d": 225000, "dim.dim_cliente": 5000}


def counts(conn) -> dict | None:
    try:
        return {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in EXPECTED}
    except psycopg.errors.UndefinedTable:
        return None


def ensure_role(conn) -> None:
    ro = db_config.RO_USER
    conn.execute(
        psycopg.sql.SQL("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {r}) "
                        "THEN CREATE ROLE {i} LOGIN; END IF; END $$").format(
            r=psycopg.sql.Literal(ro), i=psycopg.sql.Identifier(ro)))
    if not db_config.use_embedded():  # en modo externo el rol lleva contrasena
        import os
        conn.execute(psycopg.sql.SQL("ALTER ROLE {i} PASSWORD {p}").format(
            i=psycopg.sql.Identifier(ro), p=psycopg.sql.Literal(os.environ["PGPASSWORD"])))
    db = db_config.db_name()
    conn.execute(psycopg.sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
        psycopg.sql.Identifier(db), psycopg.sql.Identifier(ro)))
    conn.execute(psycopg.sql.SQL("GRANT USAGE ON SCHEMA dim, cfg TO {}").format(psycopg.sql.Identifier(ro)))
    conn.execute(psycopg.sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA dim, cfg TO {}").format(psycopg.sql.Identifier(ro)))
    conn.execute(psycopg.sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(psycopg.sql.Identifier(ro)))
    conn.execute(psycopg.sql.SQL("ALTER ROLE {} SET statement_timeout = '15s'").format(psycopg.sql.Identifier(ro)))


def main(force: bool = False) -> None:
    db = db_config.db_name()
    mode = "embebido (sin Docker)" if db_config.use_embedded() else "externo"
    print(f"PostgreSQL {mode}. Base: {db}", flush=True)

    with psycopg.connect(**db_config.admin_conninfo("postgres"), autocommit=True) as c:
        if not c.execute("select 1 from pg_database where datname=%s", (db,)).fetchone():
            c.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(db)))
            print(f"Base {db} creada")

    with psycopg.connect(**db_config.admin_conninfo(db), autocommit=True) as conn:
        current = counts(conn)
        if current == EXPECTED and not force:
            print("La base ya esta cargada y completa; no se vuelve a generar.")
        else:
            if current is not None and not force:
                raise SystemExit(f"La base existe pero esta incompleta/distinta {current}. Usa --force para regenerarla.")
            if current is not None or force:
                conn.execute("DROP SCHEMA IF EXISTS cfg CASCADE; DROP SCHEMA IF EXISTS dim CASCADE;")
            for f in sorted((ROOT / "sql").glob("00[0-3]_*.sql")):
                print(f"Ejecutando {f.name} ...", flush=True)
                conn.execute(f.read_text(encoding="utf-8"))
        ensure_role(conn)
        print("Conteos:", counts(conn))
        print("Rol de solo lectura:", db_config.RO_USER)


if __name__ == "__main__":
    main(force="--force" in sys.argv)
