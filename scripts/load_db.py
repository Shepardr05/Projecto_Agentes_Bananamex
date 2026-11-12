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
import auth  # noqa: E402
import db_config  # noqa: E402

EXPECTED = {"cfg.fact_sdos_captacoloca_m": 120000, "cfg.fact_txn_captacoloca_d": 225000, "dim.dim_cliente": 5000}


def counts(conn) -> dict | None:
    try:
        return {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in EXPECTED}
    except psycopg.errors.UndefinedTable:
        return None


def ensure_role(conn, role: str, password_env: str, columns: list[tuple[str, str]] | None = None) -> None:
    """Crea (o actualiza) un rol de SOLO LECTURA. Con `columns` [(esquema.tabla, columna)] solo
    recibe SELECT sobre esas columnas; sin `columns` recibe SELECT sobre todas las tablas."""
    ident, sql = psycopg.sql.Identifier(role), psycopg.sql
    conn.execute(sql.SQL("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {r}) "
                         "THEN CREATE ROLE {i} LOGIN; END IF; END $$").format(r=sql.Literal(role), i=ident))
    if not db_config.use_embedded():  # en modo externo el rol lleva contrasena
        import os
        conn.execute(sql.SQL("ALTER ROLE {i} PASSWORD {p}").format(i=ident, p=sql.Literal(os.environ[password_env])))
    conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(db_config.db_name()), ident))
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA dim, cfg TO {}").format(ident))
    conn.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA dim, cfg FROM {}").format(ident))  # idempotente
    if columns is None:
        conn.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA dim, cfg TO {}").format(ident))
    else:
        by_table: dict[str, list[str]] = {}
        for table, col in columns:
            by_table.setdefault(table, []).append(col)
        for table, cols in by_table.items():
            schema, name = table.split(".")
            conn.execute(sql.SQL("GRANT SELECT ({}) ON {}.{} TO {}").format(
                sql.SQL(", ").join(map(sql.Identifier, cols)), sql.Identifier(schema), sql.Identifier(name), ident))
    conn.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(ident))
    conn.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '15s'").format(ident))


def ensure_roles(conn) -> None:
    """admin -> steward_ro (todo) | usuario -> steward_usuario (todo MENOS columnas personales)."""
    ensure_role(conn, db_config.RO_USER, "PGPASSWORD")
    allowed = conn.execute(
        "SELECT table_schema || '.' || table_name, column_name FROM information_schema.columns "
        "WHERE table_schema IN ('dim', 'cfg') AND column_name <> ALL(%s) ORDER BY 1, ordinal_position",
        (list(auth.PII_COLUMNS),)).fetchall()
    ensure_role(conn, db_config.USER_RO, "PGPASSWORD_USUARIO", columns=allowed)


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
        conn.execute("ANALYZE")  # estadisticas para el planificador: sin esto, la 1a consulta con JOIN tarda >15 s
        ensure_roles(conn)
        print("Conteos:", counts(conn))
        print("Roles de solo lectura:", db_config.RO_USER, "(admin),", db_config.USER_RO, "(usuario, sin datos personales)")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
