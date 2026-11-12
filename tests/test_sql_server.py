"""
Pruebas deterministas (SIN LLM) del servidor MCP de SQL, usando un cliente MCP real.
Requieren la BD cargada y variables PG* en .env.   Ejecutar:  pytest -q
"""
import asyncio
import os
import re
import sys
import tempfile
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))
import auth  # noqa: E402
import db_config  # noqa: E402

os.environ["STEWARD_AUDIT_FILE"] = str(Path(tempfile.mkdtemp()) / "audit.jsonl")  # no ensucia logs/
db_config.ensure_db()  # PostgreSQL embebido arriba antes de lanzar el servidor MCP
SERVER = str(ROOT / "src" / "mcp_postgres_server.py")


def call(tool: str, _role: str | None = "admin", **args) -> str:
    """Llama una tool del servidor MCP con el rol indicado (None = sin rol definido)."""
    env = {**os.environ, "STEWARD_USER": f"pytest-{_role}"}
    env.pop("STEWARD_ROLE", None)
    if _role:
        env["STEWARD_ROLE"] = _role

    async def _go():
        async with Client(StdioTransport(command=sys.executable, args=[SERVER], env=env)) as c:
            return (await c.call_tool(tool, args)).content[0].text

    return asyncio.run(_go())


@pytest.fixture(scope="module", autouse=True)
def _db_available():
    out = call("list_tables")
    if out.startswith("Error"):
        pytest.skip(f"BD no disponible: {out}")


def test_tools_discovered():
    async def _go():
        t = StdioTransport(command=sys.executable, args=[SERVER], env={**os.environ, "STEWARD_ROLE": "admin"})
        async with Client(t) as c:
            return {x.name for x in await c.list_tools()}

    assert {"run_sql_query", "list_tables", "describe_table", "data_quality_profile",
            "run_governance_checks", "get_data_model_guide", "get_audit_log"} <= asyncio.run(_go())


def test_row_counts():
    out = call("list_tables")
    for table, n in [("dim_cliente", "5000"), ("fact_sdos_captacoloca_m", "120000"),
                     ("fact_txn_captacoloca_d", "225000")]:
        assert table in out and n in out


def test_select_works():
    out = call("run_sql_query", sql="select count(*) as n from dim.dim_cliente where tipo_persona='PF'")
    assert "4800" in out


@pytest.mark.parametrize("sql", [
    "drop table dim.dim_cliente",
    "delete from dim.dim_cliente",
    "update dim.dim_cliente set tipo_persona='PM'",
    "select 1; drop table dim.dim_cliente",
    "with x as (select 1) delete from dim.dim_cliente",
    "insert into dim.dim_producto(cve_producto) values ('X')",
])
def test_writes_rejected(sql):
    assert "RECHAZADA" in call("run_sql_query", sql=sql)
    assert "5000" in call("run_sql_query", sql="select count(*) from dim.dim_cliente")


def test_governance_findings():
    out = call("run_governance_checks")
    for rule in ("DQ-07", "DQ-08", "DQ-10"):
        line = next(l for l in out.splitlines() if rule in l)
        assert "FALLA" in line
    for rule in ("DQ-01", "DQ-02", "DQ-05", "DQ-11"):
        line = next(l for l in out.splitlines() if rule in l)
        assert "PASA" in line


def test_profile_finds_empty_columns():
    out = call("data_quality_profile", table="dim.dim_cliente")
    for col in ("giro_empresa", "cve_territorio", "cve_sucursal", "cve_promotor"):
        assert next(l for l in out.splitlines() if l.startswith(f"| {col} ")).count("100.0%") == 1


def test_invalid_table_rejected():
    assert "invalida" in call("describe_table", table="pg_catalog.pg_user").lower()


def test_guide_has_exact_columns_and_examples():
    guide = call("get_data_model_guide")
    assert "COLUMNAS EXACTAS" in guide
    assert "saldo_mes (numeric)" in guide
    assert "EJEMPLOS DE SQL CORRECTO" in guide


def test_guide_examples_actually_run():
    """Cada ejemplo de la guia debe ejecutarse sin error (si no, ensenariamos SQL roto)."""
    guide = call("get_data_model_guide")
    block = guide.split("EJEMPLOS DE SQL CORRECTO")[1].split("BUENAS PRACTICAS")[0]
    sqls = [l for l in block.splitlines() if l.strip().upper().startswith("SELECT")]
    assert len(sqls) >= 6
    for sql in sqls:
        out = call("run_sql_query", sql=sql)
        assert not out.startswith(("ERROR", "CONSULTA RECHAZADA")), f"{sql}\n{out}"


def test_bad_column_returns_hint_with_real_columns():
    out = call("run_sql_query", sql="SELECT SUM(saldo_mensual) FROM cfg.fact_sdos_captacoloca_m WHERE fecha = '2026-06-01'")
    assert "UndefinedColumn" in out and "PISTA" in out
    assert "saldo_mes (numeric)" in out and "fec_informacion (integer)" in out


def test_multiple_selects_in_one_call():
    out = call("run_sql_query", sql="SELECT tipo_persona, COUNT(*) AS n FROM dim.dim_cliente GROUP BY 1 ORDER BY 1; "
                                    "SELECT cve_producto FROM dim.dim_producto ORDER BY 1 LIMIT 2;")
    assert "Resultado 1" in out and "Resultado 2" in out and "4800" in out and "AHORRO" in out


def test_select_then_write_still_rejected():
    assert "RECHAZADA" in call("run_sql_query", sql="select 1; update dim.dim_cliente set tipo_persona='PM'")
    assert "RECHAZADA" in call("run_sql_query", sql="select 1; select 2; select 3; select 4")


def test_semicolon_inside_string_is_not_a_split():
    out = call("run_sql_query", sql="select 'a;b' as txt")
    assert "a;b" in out and "RECHAZADA" not in out


def test_failing_rules_include_next_step_instruction():
    out = call("run_governance_checks")
    assert "SIGUIENTE PASO OBLIGATORIO" in out and "DQ-07" in out


# ---------------------------------------------------------------------------------------
# ROLES: usuario vs admin
# ---------------------------------------------------------------------------------------

ADMIN_TOOL_CALLS = [("describe_table", {"table": "dim.dim_cliente"}), ("data_quality_profile", {"table": "dim.dim_cliente"}),
                    ("run_governance_checks", {}), ("get_audit_log", {})]


def test_login_and_password_hashing(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "USERS_FILE", tmp_path / "users.json")
    auth.add_user("ana", "usuario", "clave-ana")
    auth.add_user("beto", "admin", "clave-beto")
    assert auth.login("ana", "clave-ana") == auth.User("ana", "usuario")
    assert auth.login("beto", "clave-beto") == auth.User("beto", "admin")
    assert auth.login("ana", "clave-beto") is None and auth.login("nadie", "x") is None
    assert "clave-ana" not in (tmp_path / "users.json").read_text()
    with pytest.raises(SystemExit):
        auth.add_user("x", "superadmin", "x")


def test_permission_matrix():
    for tool in ("postgres_run_governance_checks", "postgres_describe_table", "postgres_get_audit_log"):
        assert auth.can("admin", tool) and not auth.can("usuario", tool)
    for tool in ("postgres_run_sql_query", "postgres_list_tables", "governance_search_governance_knowledge", "web_search"):
        assert auth.can("admin", tool) and auth.can("usuario", tool)


@pytest.mark.parametrize("tool,args", ADMIN_TOOL_CALLS)
@pytest.mark.parametrize("role", ["usuario", None, "root"])  # None / rol invalido -> minimo privilegio
def test_admin_tools_denied_without_admin_role(tool, args, role):
    assert "ACCESO DENEGADO" in call(tool, _role=role, **args)


@pytest.mark.parametrize("tool,args", ADMIN_TOOL_CALLS[:3])
def test_admin_tools_work_for_admin(tool, args):
    assert "ACCESO DENEGADO" not in call(tool, **args)


def test_usuario_can_query_non_personal_data():
    assert "4800" in call("run_sql_query", _role="usuario", sql="select count(*) from dim.dim_cliente where tipo_persona='PF'")
    assert "dim_cliente" in call("list_tables", _role="usuario")
    assert "saldo_mes" in call("get_data_model_guide", _role="usuario")


@pytest.mark.parametrize("sql", [
    "select fec_nac from dim.dim_cliente limit 1",
    "select * from dim.dim_cliente limit 1",
    "select count(*) from dim.dim_cliente where genero_cte = 'MUJER'",   # inferencia por filtro
    "select genero_cte, count(*) from dim.dim_cliente group by 1",       # ni siquiera agregados
])
def test_usuario_cannot_touch_personal_columns(sql):
    out = call("run_sql_query", _role="usuario", sql=sql)
    assert "ACCESO DENEGADO" in out
    assert not re.search(r"\b(19|20)\d{2}-\d{2}-\d{2}\b", out)
    assert "tipo_persona (" in out and "fec_nac (" not in out and "genero_cte (" not in out  # lista de columnas permitidas


def test_admin_can_aggregate_personal_columns():
    out = call("run_sql_query", sql="select genero_cte, count(*) as n from dim.dim_cliente group by 1 order by 1")
    assert "ACCESO DENEGADO" not in out and "MUJER" in out


def test_db_roles_enforced_without_the_mcp_layer():
    with psycopg.connect(**db_config.readonly_conninfo("usuario"), autocommit=True) as c:
        assert c.execute("select count(*) from dim.dim_cliente").fetchone()[0] == 5000
        for bad in ("select fec_nac from dim.dim_cliente", "select * from dim.dim_cliente", "create table dim.x(a int)"):
            with pytest.raises(psycopg.Error):
                c.execute(bad)


def test_describe_table_and_profile_mask_personal_data():
    real = [r[0] for r in db_config_rows("select fec_nac::text from dim.dim_cliente limit 3")]
    described = call("describe_table", table="dim.dim_cliente")
    assert "***" in described and not any(v in described for v in real)
    profile = call("data_quality_profile", table="dim.dim_cliente")
    assert next(l for l in profile.splitlines() if l.startswith("| fec_nac ")).count("***") == 2


def db_config_rows(sql):
    with psycopg.connect(**db_config.readonly_conninfo("admin"), autocommit=True) as c:
        return c.execute(sql).fetchall()


def test_audit_log_records_allowed_and_denied_calls():
    call("run_governance_checks", _role="usuario")                       # denegada
    call("run_sql_query", _role="usuario", sql="select 1 as marca_auditoria")  # permitida
    log = call("get_audit_log", limit=50)
    denied = next(l for l in log.splitlines() if "pytest-usuario" in l and "run_governance_checks" in l)
    allowed = next(l for l in log.splitlines() if "marca_auditoria" in l)
    assert "| NO |" in denied and "| si |" in allowed
