"""
check_setup.py -- Diagnostico del entorno ANTES de la demo. No usa LLM.
Revisa: .env, PostgreSQL (y que el usuario sea de solo lectura), descubrimiento de tools
por MCP, indice/consulta de Pinecone, Ollama (modelos) y Tavily (busqueda web real).

    python scripts/check_setup.py
"""
import asyncio
import json
import os
import sys
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
import common  # noqa: E402,F401  (configura la consola)
import db_config  # noqa: E402

OK, BAD, WARN = "[ OK ]", "[FALLA]", "[AVISO]"


def check_env():
    need = ["PINECONE_API_KEY", "INDEX_NAME"]
    missing = [k for k in need if not os.getenv(k) or "PEGA" in os.getenv(k, "")]
    print(OK if not missing else BAD, "Variables .env obligatorias", f"(faltan: {missing})" if missing else "")
    has_tavily = os.getenv("TAVILY_API_KEY") and "PEGA" not in os.getenv("TAVILY_API_KEY", "")
    print(OK if has_tavily else WARN, "TAVILY_API_KEY", "" if has_tavily else "(sin ella no hay busqueda web)")


def check_db():
    import psycopg

    try:
        with psycopg.connect(**db_config.readonly_conninfo(), connect_timeout=8) as c:
            n = c.execute("select count(*) from cfg.fact_sdos_captacoloca_m").fetchone()[0]
            print(OK if n == 120000 else WARN, f"PostgreSQL: saldos = {n:,} filas (esperado 120,000)")
            try:
                c.execute("create table cfg.__probe(x int)")
                c.rollback()
                print(BAD, "El usuario PUEDE crear tablas: debe ser el rol de solo lectura")
            except Exception:
                c.rollback()
                print(OK, "El usuario de conexion es de solo lectura")
    except Exception as e:
        print(BAD, f"PostgreSQL: {type(e).__name__}: {str(e).splitlines()[0]}")
        print("       -> corre:  python scripts/load_db.py")


def check_ollama():
    emb = os.getenv("EMBEDDING_MODEL", "bge-m3")
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            models = [m["name"] for m in json.load(r)["models"]]
    except Exception:
        print(BAD, "Ollama no responde en localhost:11434 (abre la app de Ollama; se necesita para los embeddings)")
        return
    print(OK if any(emb in m for m in models) else BAD, f"Ollama embeddings '{emb}'", "" if any(emb in m for m in models) else f"-> ollama pull {emb}")
    if os.getenv("LLM_PROVIDER", "ollama") == "ollama":
        llm = os.getenv("LLM_MODEL", "llama3.1:latest").split(":")[0]
        print(OK if any(llm in m for m in models) else BAD, f"Ollama LLM '{llm}'", "" if any(llm in m for m in models) else f"-> ollama pull {llm}")


def check_tavily():
    if not os.getenv("TAVILY_API_KEY"):
        return
    try:
        from langchain_tavily import TavilySearch

        res = TavilySearch(max_results=1).invoke({"query": "capital of Australia"})
        items = res.get("results", []) if isinstance(res, dict) else res
        print(OK if items else WARN, "Tavily: busqueda web de prueba", "" if items else "(sin resultados)")
    except Exception as e:
        print(BAD, f"Tavily: {type(e).__name__}: {str(e)[:120]}")


async def check_mcp():
    from agent import mcp_config
    from langchain.mcp import MCPAdapter

    try:
        async with MCPAdapter(mcp_config()) as a:
            tools = await a.list_tools()
            names = [t.name for t in tools]
            print(OK, f"MCP: {len(names)} tools descubiertas -> {', '.join(names)}")
            t = next(x for x in tools if x.name.endswith("run_sql_query"))
            r = await t.ainvoke({"sql": "select count(*) as clientes from dim.dim_cliente"})
            print(OK, "MCP->PostgreSQL:", str(r[0]["text"]).replace("\n", " ") if isinstance(r, list) else r)
            g = next(x for x in tools if x.name.endswith("search_governance_knowledge"))
            r = await g.ainvoke({"query": "data quality dimensions"})
            txt = r[0]["text"] if isinstance(r, list) else str(r)
            bad = txt.startswith("Error") or txt.startswith("NOT_IN")
            print(BAD if bad else OK, "MCP->Pinecone (RAG):", txt[:160].replace("\n", " "))
    except Exception as e:
        print(BAD, f"MCP: {type(e).__name__}: {e}")


if __name__ == "__main__":
    check_env()
    check_db()
    check_ollama()
    check_tavily()
    asyncio.run(check_mcp())
