"""
Pruebas deterministas (SIN LLM) del servidor MCP de SQL, usando un cliente MCP real.
Requieren la BD cargada y variables PG* en .env.   Ejecutar:  pytest -q
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))
import db_config  # noqa: E402

db_config.ensure_db()  # PostgreSQL embebido arriba antes de lanzar el servidor MCP
SERVER = str(ROOT / "src" / "mcp_postgres_server.py")


def call(tool: str, **args) -> str:
    async def _go():
        t = StdioTransport(command=sys.executable, args=[SERVER], env=dict(os.environ))
        async with Client(t) as c:
            return (await c.call_tool(tool, args)).content[0].text

    return asyncio.run(_go())


@pytest.fixture(scope="module", autouse=True)
def _db_available():
    out = call("list_tables")
    if out.startswith("Error"):
        pytest.skip(f"BD no disponible: {out}")


def test_tools_discovered():
    async def _go():
        t = StdioTransport(command=sys.executable, args=[SERVER], env=dict(os.environ))
        async with Client(t) as c:
            return {x.name for x in await c.list_tools()}

    assert {"run_sql_query", "list_tables", "describe_table", "data_quality_profile",
            "run_governance_checks", "get_data_model_guide"} <= asyncio.run(_go())


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