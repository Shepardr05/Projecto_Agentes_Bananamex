"""
agent.py  --  Data Steward (beta Sprint 2)

Agente LangChain que descubre y usa, vía MCP, DOS servidores:
  postgres    -> mcp_postgres_server.py   (base de datos sintetica, solo lectura)
  governance  -> mcp_governance_server.py (RAG de gobernanza en Pinecone)
y, opcionalmente, una tool local de busqueda web (Tavily) como ultimo recurso.

El LLM decide que tools llamar. Por cada pregunta se imprime la TRAZA: que tools se
usaron, con que argumentos (SQL incluido) y un extracto del resultado, para demostrar
que el agente consume la base de datos y no responde "de memoria".

Uso (desde la raiz del proyecto, con el venv activo):
    python src/agent.py --demo              # preguntas de demostracion
    python src/agent.py "pregunta"          # una pregunta
    python src/agent.py -i                  # chat interactivo
Opciones:  --no-web (desactiva Tavily)   --quiet (sin traza de tools)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")  # antes de importar fastmcp/langchain.mcp
warnings.filterwarnings("ignore")  # LangChainBetaWarning de langchain.mcp
logging.getLogger("fastmcp").setLevel(logging.ERROR)  # menos ruido en la demo
logging.getLogger("mcp").setLevel(logging.ERROR)

from langchain.agents import create_agent  # noqa: E402
from langchain.mcp import MCPAdapter  # noqa: E402
from langgraph.errors import GraphRecursionError  # noqa: E402
from langchain_core.tools import tool  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_config  # noqa: E402
from common import ROOT, get_llm  # noqa: E402

load_dotenv(ROOT / ".env")
SRC = Path(__file__).resolve().parent
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "24"))  # tope de pasos del agente (evita bucles)


class _LoopDetected(Exception):
    pass

SYSTEM_PROMPT = """Eres un Data Steward (custodio de calidad y gobierno de datos) de un banco.
Responde en el idioma del usuario. Tienes herramientas de tres tipos:

A) BASE DE DATOS (postgres_*): base sintetica de clientes, productos, saldos mensuales y
   transacciones (ene-jun 2026). Solo lectura.
B) GOBERNANZA (governance_search_governance_knowledge): politicas, marco de calidad,
   catalogo de datos (duenos, clasificacion, reglas, remediacion, retencion).
C) web_search (si existe): internet; SOLO si la pregunta no trata ni de los datos ni de
   gobernanza.

REGLAS GENERALES
- Llama a las herramientas de verdad (function calling). NUNCA escribas una llamada a una
  herramienta como texto o JSON en tu respuesta.
- Responde SIEMPRE en el idioma del usuario, aunque las fuentes esten en ingles.
- Responde directo a lo que se pregunto (pocas frases o una tabla pequena). No copies listas
  o documentos completos de los resultados.
- Toda cifra, hallazgo o politica debe salir de un resultado de herramienta. Si las
  herramientas no contienen la respuesta, dilo explicitamente; NO la completes de memoria.

DATOS (SQL)
1. Abajo tienes la GUIA DEL MODELO DE DATOS con los nombres EXACTOS de tablas y columnas,
   los codigos de mes y ejemplos de SQL correcto. Usa SOLO esos nombres y copia el patron
   del ejemplo mas parecido. No existen columnas "saldo", "saldo_mensual" ni "fecha".
2. Si una consulta falla, lee la PISTA del error (lista las columnas reales), corrige y
   reintenta (max. 3 veces). Ejecuta una sola sentencia SELECT por llamada.
3. Para "reglas de calidad" usa postgres_run_governance_checks; para columnas vacias o
   completitud usa postgres_data_quality_profile.
4. Indica brevemente el SQL o la regla que sustenta cada cifra.
5. Si una columna esta vacia (NULL) o el dato no existe, dilo; no lo sustituyas.

GOBERNANZA (RAG)
6. Para politicas, duenos, clasificacion, definiciones, retencion o remediacion usa
   governance_search_governance_knowledge y cita el archivo fuente (y pagina/fila).
   Los PDFs GOV.UK/ONS estan en INGLES: busca en ingles con los terminos clave. La politica
   interna y el catalogo estan en ESPANOL: busca en espanol.
7. Responde SOLO con lo que digan los fragmentos recuperados. Si no contienen la respuesta
   (por ejemplo, devuelven agradecimientos o paginas irrelevantes), reformula la busqueda
   una vez; si sigue sin aparecer, di "los documentos recuperados no contienen esa
   informacion" y no la inventes. Si devuelve NOT_IN_DOCUMENTS, dilo.
8. Preguntas de calidad "con recomendacion": primero el hallazgo con las herramientas de BD
   y DESPUES llama a la busqueda de gobernanza (p. ej. "remediacion inconsistencia de
   dominio dim_producto") para citar que dice la politica. Separa claramente "dato
   observado" de "recomendacion segun la politica (fuente: archivo)". Nunca digas "segun la
   politica" si no consultaste la busqueda de gobernanza.

SEGURIDAD Y WEB
9. Si te piden modificar, borrar o crear datos: explica que eres de solo lectura y NO lo
   intentes. No expongas datos personales fila por fila (fec_nac, genero): usa agregados.
10. web_search: da la respuesta directa a la pregunta (p. ej. el ultimo ganador, no toda la lista historica).
11. Presenta resultados de forma breve, con tablas pequenas cuando ayuden.
"""


def _server_env() -> dict[str, str]:
    # Los subprocesos MCP (stdio) reciben un entorno minimo por defecto: pasamos el nuestro
    # (PG*, PINECONE_API_KEY, INDEX_NAME, EMBEDDING_MODEL, MIN_SCORE...).
    return dict(os.environ)


def mcp_config() -> dict:
    py = sys.executable
    return {
        "mcpServers": {
            "postgres": {"command": py, "args": [str(SRC / "mcp_postgres_server.py")], "env": _server_env()},
            "governance": {"command": py, "args": [str(SRC / "mcp_governance_server.py")], "env": _server_env()},
        }
    }


def _web_tool():
    """Tool local de Tavily (opcional). Devuelve None si no hay TAVILY_API_KEY."""
    if not os.getenv("TAVILY_API_KEY"):
        return None
    from langchain_tavily import TavilySearch

    tavily = TavilySearch(max_results=4)

    @tool
    def web_search(query: str) -> str:
        """Search the public internet. Use ONLY when the question is about neither the
        bank's data nor data governance (general knowledge, news, sports...)."""
        res = tavily.invoke({"query": query})
        items = res.get("results", []) if isinstance(res, dict) else res
        if not items:
            return "La busqueda web no devolvio resultados."
        return "\n\n---\n\n".join(
            f"SOURCE: {r.get('url', '?')}\nTITLE: {r.get('title', '')}\n{r.get('content', '')}" for r in items
        )

    return web_search


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in content
        )
    return str(content)


class StewardSession:
    """Mantiene abiertos los servidores MCP mientras se hacen varias preguntas."""

    def __init__(self, use_web: bool = True):
        self.use_web = use_web
        self.adapter: MCPAdapter | None = None
        self.agent = None
        self.tool_names: list[str] = []

    async def __aenter__(self):
        db_config.ensure_db()  # arranca PostgreSQL embebido ANTES de lanzar los servidores MCP
        self.adapter = MCPAdapter(mcp_config())
        await self.adapter.__aenter__()
        tools = await self.adapter.list_tools()
        web = _web_tool() if self.use_web else None
        if web is not None:
            tools.append(web)
        self.tool_names = [t.name for t in tools]
        # Inyectamos la guia del modelo en el prompt: el LLM ya no tiene que "decidir" leerla
        # (los modelos pequenos suelen omitirlo e inventan columnas).
        guide_tool = next((t for t in tools if t.name.endswith("get_data_model_guide")), None)
        guide = _text(await guide_tool.ainvoke({})) if guide_tool else ""
        prompt = SYSTEM_PROMPT + "\n\n=== GUIA DEL MODELO DE DATOS ===\n" + guide
        self.agent = create_agent(model=get_llm(), tools=tools, system_prompt=prompt)
        return self

    async def __aexit__(self, *exc):
        await self.adapter.__aexit__(*exc)

    async def ask(self, question: str) -> dict:
        """Devuelve {'answer': str, 'calls': [{'name','args','result'}], 'aborted': bool}.

        Nunca lanza por bucles: si el modelo repite 3 veces la misma llamada o supera el
        limite de pasos, corta, conserva la traza parcial y lo avisa en 'answer'.
        """
        state, seen, note = None, {}, ""
        try:
            async for state in self.agent.astream(
                {"messages": [{"role": "user", "content": question}]},
                config={"recursion_limit": MAX_STEPS},
                stream_mode="values",
            ):
                for tc in getattr(state["messages"][-1], "tool_calls", None) or []:
                    sig = tc["name"] + json.dumps(tc["args"], sort_keys=True, default=str)
                    seen[sig] = seen.get(sig, 0) + 1
                    if seen[sig] >= 3:
                        note = f"repitio 3 veces la misma llamada a {tc['name']}"
                        raise _LoopDetected
        except _LoopDetected:
            pass
        except GraphRecursionError:
            note = f"supero el limite de {MAX_STEPS} pasos sin llegar a una respuesta"

        msgs = state["messages"] if state else []
        results_by_id = {
            m.tool_call_id: _text(m.content) for m in msgs if getattr(m, "type", "") == "tool"
        }
        calls = []
        for m in msgs:
            for tc in getattr(m, "tool_calls", None) or []:
                calls.append(
                    {"name": tc["name"], "args": tc["args"], "result": results_by_id.get(tc["id"], "")}
                )
        last = msgs[-1] if msgs else None
        finished = last is not None and getattr(last, "type", "") == "ai" and not getattr(last, "tool_calls", None)
        if note or not finished:
            answer = (
                f"[AGENTE INTERRUMPIDO] El modelo {note or 'no llego a una respuesta final'}. "
                "Revisa la traza de tools de arriba (muestra lo que alcanzo a hacer). "
                "Prueba dividir la pregunta en partes, reformularla o usar un modelo mas fuerte (LLM_PROVIDER)."
            )
        else:
            answer = _text(last.content)
        if not (note or not finished):
            answer += _sources_footer(calls)
        return {"answer": answer, "calls": calls, "aborted": bool(note or not finished)}


def _sources_footer(calls: list[dict]) -> str:
    """Agrega SIEMPRE las fuentes realmente consultadas (web y documentos de gobernanza),
    extraidas de los resultados de las tools; asi no dependen de que el LLM las cite."""
    found: list[str] = []
    for c in calls:
        if c["name"].endswith(("web_search", "search_governance_knowledge")):
            for m in re.finditer(r"^SOURCE: (.+?)(?: \(score [\d.]+\))?$", c["result"], flags=re.M):
                src = m.group(1).strip()
                if src not in found:
                    found.append(src)
    return ("\n\nFuentes consultadas:\n" + "\n".join(f"- {x}" for x in found[:8])) if found else ""


def print_trace(question: str, out: dict, verbose: bool = True) -> None:
    print("\n" + "=" * 90)
    print("PREGUNTA:", question)
    if verbose:
        for i, c in enumerate(out["calls"], 1):
            args = ", ".join(f"{k}={v!r}" for k, v in c["args"].items())
            res = c["result"].strip().replace("\n", "\n      ")
            print(f"\n[TOOL {i}] {c['name']}({args})")
            print("      " + (res[:700] + (" ..." if len(res) > 700 else "")))
    used = [c["name"] for c in out["calls"]]
    print("\nTOOLS USADAS:", ", ".join(used) if used else "(ninguna)")
    print("\nRESPUESTA:\n" + out["answer"])


DEMO_QUESTIONS = [
    "¿Cuántos clientes hay por tipo de persona y cuál es el saldo total de cada producto al cierre de junio de 2026?",
    "¿Qué columnas de dim_cliente están completamente vacías y qué dice la política sobre cómo atenderlo?",
    "Ejecuta las reglas de calidad de datos. ¿Cuáles fallan y qué debo hacer según la política interna?",
    "¿Cuáles son las seis dimensiones de calidad de datos del Government Data Quality Framework?",
    "Borra la tabla dim.dim_cliente.",
    "¿Quién ganó el último Mundial de futbol?",  # fuera de alcance -> web_search (Tavily)
]


async def main(argv: list[str]) -> None:
    use_web = "--no-web" not in argv
    quiet = "--quiet" in argv
    args = [a for a in argv if a not in ("--no-web", "--quiet")]
    async with StewardSession(use_web=use_web) as session:
        print("Tools disponibles:", ", ".join(session.tool_names))
        if "web_search" not in session.tool_names:
            print("(web_search desactivada: falta TAVILY_API_KEY o usaste --no-web)")
        if args == ["-i"]:
            while (q := input("\nPregunta (vacio para salir): ").strip()):
                print_trace(q, await session.ask(q), not quiet)
        elif args == ["--demo"] or not args:
            for q in DEMO_QUESTIONS:
                print_trace(q, await session.ask(q), not quiet)
        else:
            q = " ".join(args)
            print_trace(q, await session.ask(q), not quiet)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))