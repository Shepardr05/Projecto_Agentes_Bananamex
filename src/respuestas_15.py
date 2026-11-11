"""
respuestas_15.py -- Hace las 15 preguntas al agente y muestra cada pregunta con su respuesta.

Sin comparar contra nada: solo pregunta -> respuesta (y las tools usadas). Si algo sale mal
(error de conexion, agente interrumpido, respuesta vacia o una disculpa) muestra un [AVISO].

Uso:  python src/respuestas_15.py            # las 15
      python src/respuestas_15.py 6 12       # solo algunas
      python src/respuestas_15.py --no-web   # sin Tavily
Salida: terminal + docs/RESPUESTAS_15.md
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import StewardSession  # noqa: E402
from common import ROOT  # noqa: E402

PREGUNTAS = [
    "¿Quién es el dueño del dato del saldo de cierre de mes de las cuentas y quién es el steward responsable?",
    "¿Qué campos de la información de clientes son datos personales y cómo están clasificados?",
    "¿De dónde viene el dominio del producto y cuál de las dos fuentes debo considerar la oficial?",
    "¿Quién es responsable de que la sucursal y el promotor del cliente estén informados?",
    "¿Qué clasificación tienen los importes de las transacciones y quién puede acceder a ellos?",
    "¿Cuál es el saldo total de cada producto al cierre de junio de 2026?",
    "¿Cuánto creció en promedio el saldo de las tarjetas de crédito de enero a febrero?",
    "Para un cliente en particular, ¿cómo se compone el saldo de su tarjeta de crédito en marzo: saldo inicial, compras, disposiciones, pagos y saldo final?",
    "¿Qué segmento de clientes concentra el mayor saldo en cheques al cierre de junio?",
    "¿Cuánto dinero se movió en retiros y depósitos en mayo, producto por producto?",
    "¿Cuánto tiempo debemos conservar los saldos y las transacciones, según la política?",
    "¿En cuánto tiempo debo escalar un hallazgo de calidad de severidad alta y a quién?",
    "¿Qué dice la política sobre cómo corregir que el dominio de los saldos no coincida con el catálogo de productos?",
    "¿Cuáles son las seis dimensiones de calidad de datos del marco de gobierno del Reino Unido y a cuál pertenece que un saldo no pueda ser negativo?",
    "¿Cuántos días después del cierre de mes deben estar disponibles los saldos mensuales?",
]
TIPOS = ["Gobernanza"] * 5 + ["Analítica"] * 5 + ["Documentos"] * 5


def aviso(exc: Exception | None, out: dict | None) -> str:
    if exc is not None:
        m = str(exc)
        extra = ""
        if "connect" in m.lower():
            extra = " -> No hay conexion: abre la app de Ollama (y revisa internet para Pinecone/Tavily) y corre .\\run.ps1 check"
        return f"error: {type(exc).__name__}: {m}{extra}"
    if out.get("aborted"):
        return "el agente fue interrumpido (bucle o sin respuesta final)"
    ans = out["answer"].strip()
    if not ans:
        return "respuesta vacia"
    if ans.lower().startswith(("lo siento", "lo lamento", "perdón", "sorry")):
        return "el agente se disculpo en vez de responder"
    return ""


async def run(sel: list[int], use_web: bool) -> None:
    idx = [i for i in range(1, 16) if not sel or i in sel]
    bar = "=" * 78
    md = ["# Respuestas del agente a las 15 preguntas\n", f"Fecha: {datetime.now():%Y-%m-%d %H:%M}\n"]
    avisos = 0
    async with StewardSession(use_web=use_web) as s:
        for i in idx:
            q = PREGUNTAS[i - 1]
            print(f"\n{bar}\nP{i} ({TIPOS[i - 1]}): {q}\n{bar}", flush=True)
            exc, out = None, None
            try:
                out = await s.ask(q)
            except Exception as e:  # noqa: BLE001
                exc = e
            msg = aviso(exc, out)
            tools = ", ".join(c["name"] for c in out["calls"]) if out else "-"
            ans = out["answer"].strip() if out else ""
            print(f"TOOLS: {tools or '(ninguna)'}\n\nRESPUESTA:\n{ans or '(sin respuesta)'}")
            if msg:
                avisos += 1
                print(f"\n[AVISO] {msg}")
            md += [f"## P{i} · {TIPOS[i - 1]}\n", f"**Pregunta:** {q}\n", f"**Tools:** {tools or '(ninguna)'}\n",
                   "**Respuesta:**\n", "> " + (ans or "(sin respuesta)").replace("\n", "\n> ") + "\n"]
            if msg:
                md.append(f"**AVISO:** {msg}\n")
    path = ROOT / "docs" / "RESPUESTAS_15.md"
    path.write_text("\n".join(md), encoding="utf-8")
    print(f"\n{bar}\n{len(idx)} preguntas hechas, {avisos} con aviso. Guardado en: {path}")


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(run([int(x) for x in a if x.isdigit()], "--no-web" not in a))