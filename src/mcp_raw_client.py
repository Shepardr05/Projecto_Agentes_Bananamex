"""
mcp_raw_client.py -- Cliente MCP minimo SIN LLM (evolucion de 12_mcp_raw_client.py).

Demuestra el ciclo MCP contra el servidor de SQL: inicializar -> descubrir (tools/list)
-> ejecutar (tools/call) -> cerrar. Python decide que tool llamar; no hay modelo.
Sirve en la demo para probar que la BD se consume via MCP aunque falle el LLM.

    python src/mcp_raw_client.py
    python src/mcp_raw_client.py "select cve_producto, count(*) from cfg.fact_sdos_captacoloca_m group by 1"
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
SERVER = ROOT / "src" / "mcp_postgres_server.py"
DEFAULT_SQL = (
    "select cve_producto, count(*) cuentas, round(sum(saldo_mes),2) saldo_total "
    "from cfg.fact_sdos_captacoloca_m where fec_informacion = 20260630 "
    "group by 1 order by 1"
)


async def main() -> None:
    sql = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SQL
    transport = StdioTransport(command=sys.executable, args=[str(SERVER)], env=dict(os.environ))
    async with Client(transport) as client:
        print("--- TOOLS DESCUBIERTAS (tools/list) ---")
        for t in await client.list_tools():
            print(f"- {t.name}")
        print("\n--- tools/call list_tables ---")
        print((await client.call_tool("list_tables", {})).content[0].text)
        print(f"\n--- tools/call run_sql_query ---\n{sql}\n")
        print((await client.call_tool("run_sql_query", {"sql": sql})).content[0].text)
        print("\n--- tools/call run_governance_checks ---")
        print((await client.call_tool("run_governance_checks", {})).content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
