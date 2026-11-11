"""
evaluar_langsmith.py -- Evalua el agente con LangSmith usando las 15 preguntas de la entrega.

Que hace:
  1. Crea (una sola vez) el dataset "data-steward-15" en tu cuenta de LangSmith con las 15 preguntas
     y su respuesta esperada.
  2. Corre el agente sobre cada pregunta (una a la vez) y registra una trazas por pregunta.
  3. Aplica 3 evaluadores a cada respuesta (las mismas revisiones de run_preguntas.py):
        correcto           1 si la respuesta contiene lo esperado (palabras/cifras reales de la BD)
        uso_tool_esperada  1 si llamo a la tool que correspondia (SQL o gobernanza)
        sin_error          1 si no hubo excepcion, interrupcion, respuesta vacia ni disculpa
  4. Crea un "experimento" en LangSmith (Datasets & Experiments) para comparar corridas/modelos.

Requisitos en .env:  LANGSMITH_API_KEY  (y opcional LANGSMITH_PROJECT, LANGSMITH_DATASET)

Uso:  python src/evaluar_langsmith.py              # las 15
      python src/evaluar_langsmith.py 6 12         # solo algunas
      python src/evaluar_langsmith.py --no-web
Para comparar modelos: cambia LLM_MODEL / LLM_PROVIDER en .env y vuelve a correrlo (el experimento
se nombra con el modelo).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import StewardSession  # noqa: E402  (tambien carga .env)
from run_preguntas import Q_, extra_checks  # noqa: E402

DATASET = os.getenv("LANGSMITH_DATASET", "data-steward-15")
QS = {q.n: q for q in Q_}


# ------------------------------ dataset ------------------------------
def asegurar_dataset(client) -> None:
    if not client.has_dataset(dataset_name=DATASET):
        client.create_dataset(DATASET, description="15 preguntas de la entrega del Data Steward (Sprint 2)")
    existentes = {e.inputs.get("n") for e in client.list_examples(dataset_name=DATASET)}
    nuevos = [
        {"inputs": {"n": q.n, "question": q.question},
         "outputs": {"expected": q.expected},
         "metadata": {"group": q.group}}
        for q in Q_ if q.n not in existentes
    ]
    if nuevos:
        client.create_examples(dataset_name=DATASET, examples=nuevos)
        print(f"Dataset '{DATASET}': {len(nuevos)} preguntas nuevas subidas.")
    else:
        print(f"Dataset '{DATASET}': ya tenia las {len(existentes)} preguntas.")


# ------------------------------ evaluadores ------------------------------
def _calls(outputs: dict) -> list[dict]:
    return outputs.get("calls", [])


def ev_correcto(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    q = QS[inputs["n"]]
    if outputs.get("error"):
        return {"key": "correcto", "score": 0, "comment": f"error: {outputs['error']}"}
    probs = q.check(outputs.get("answer", "")) + extra_checks(q.n, {"calls": _calls(outputs)})
    return {"key": "correcto", "score": int(not probs), "comment": "; ".join(probs) or "coincide con lo esperado"}


def ev_tool(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    q = QS[inputs["n"]]
    used = [c["name"] for c in _calls(outputs)]
    ok = all(any(t in u for u in used) for t in q.tools)
    return {"key": "uso_tool_esperada", "score": int(ok),
            "comment": f"uso: {', '.join(used) or 'ninguna'} | esperada: {', '.join(q.tools)}"}


def ev_sin_error(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    ans = (outputs.get("answer") or "").strip()
    if outputs.get("error"):
        why = f"excepcion: {outputs['error']}"
    elif outputs.get("aborted"):
        why = "agente interrumpido"
    elif not ans:
        why = "respuesta vacia"
    elif ans.lower().startswith(("lo siento", "lo lamento", "perdón", "sorry")):
        why = "el agente se disculpo en vez de responder"
    else:
        why = ""
    return {"key": "sin_error", "score": int(not why), "comment": why or "ok"}


# ------------------------------ ejecucion ------------------------------
async def evaluar(session, data, client=None, upload_results: bool = True):
    from langsmith import aevaluate

    async def target(inputs: dict) -> dict:
        try:
            out = await session.ask(inputs["question"])
        except Exception as exc:  # noqa: BLE001  (la pregunta falla, la evaluacion sigue)
            return {"answer": "", "calls": [], "aborted": False, "error": f"{type(exc).__name__}: {exc}"}
        return {
            "answer": out["answer"],
            "aborted": bool(out.get("aborted")),
            "calls": [{"name": c["name"], "args": {"sql": str(c["args"].get("sql", ""))}} for c in out["calls"]],
        }

    modelo = f"{os.getenv('LLM_PROVIDER', 'ollama')}-{os.getenv('LLM_MODEL', 'llama3.1:latest')}"
    return await aevaluate(
        target,
        data=data,
        evaluators=[ev_correcto, ev_tool, ev_sin_error],
        experiment_prefix=f"steward-{modelo}",
        metadata={"model": os.getenv("LLM_MODEL", "llama3.1:latest"), "provider": os.getenv("LLM_PROVIDER", "ollama"),
                  "min_score": os.getenv("MIN_SCORE", "")},
        max_concurrency=1,          # una pregunta a la vez (el agente usa procesos MCP compartidos)
        client=client,
        upload_results=upload_results,
    )


async def resumen(results) -> None:
    filas = []
    async for r in results:
        n = r["example"].inputs["n"]
        ev = {e.key: e for e in r["evaluation_results"]["results"]}
        filas.append((n, ev))
    filas.sort(key=lambda x: x[0])
    print("\n" + "=" * 78 + "\nRESUMEN (correcto / tool esperada / sin error)")
    ok = 0
    for n, ev in filas:
        c, t, s = (int(ev[k].score) for k in ("correcto", "uso_tool_esperada", "sin_error"))
        ok += c
        motivo = "" if c else "  <- " + str(ev["correcto"].comment)
        print(f"  P{n:<2} {c} / {t} / {s}{motivo}")
    print(f"\n{ok}/{len(filas)} correctas segun la revision automatica.")


async def main(sel: list[int], use_web: bool) -> None:
    if not os.getenv("LANGSMITH_API_KEY"):
        sys.exit("Falta LANGSMITH_API_KEY en el .env (ver README: seccion LangSmith).")
    from langsmith import Client
    client = Client()
    asegurar_dataset(client)
    data = [e for e in client.list_examples(dataset_name=DATASET) if not sel or e.inputs["n"] in sel]
    async with StewardSession(use_web=use_web) as session:
        results = await evaluar(session, data, client=client)
        await resumen(results)
    print("\nAbre LangSmith -> Datasets & Experiments -> '" + DATASET + "' para ver el experimento y las trazas.")


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(main([int(x) for x in a if x.isdigit()], "--no-web" not in a))