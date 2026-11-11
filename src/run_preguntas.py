"""
run_preguntas.py -- Las 15 preguntas de la entrega: respuesta esperada vs. respuesta del agente.

  Gobernanza (1-5) y ancladas en documentos (11-15): se comparan con palabras clave tomadas de
  rag_documents/ (politica y catalogo sinteticos del equipo; si el socio da documentos oficiales,
  actualiza las claves de abajo).
  Analiticas (6-10): las cifras se calculan EN VIVO en TU base (los saldos son aleatorios).

Uso:  python src/run_preguntas.py              # las 15
      python src/run_preguntas.py 6 12         # solo algunas
      python src/run_preguntas.py --no-web
      python src/run_preguntas.py --corto    # solo veredictos en la terminal
Salida: docs/RESULTADOS_15_PREGUNTAS.md
"""
from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import StewardSession  # noqa: E402
import db_config  # noqa: E402
from common import ROOT  # noqa: E402


def rows(sql: str):
    with psycopg.connect(**db_config.readonly_conninfo(), autocommit=True) as c:
        c.execute("set statement_timeout=0")
        return c.execute(sql).fetchall()


def norm(t: str) -> str:
    return re.sub(r"[,\s$]", "", t.lower())


def has_num(ans: str, v: float) -> bool:
    t = norm(ans)
    return f"{float(v):.2f}" in t or str(int(v)) in t


def words(ans: str, ws: list[str]) -> list[str]:
    t = ans.lower()
    return [f"falta '{w}'" for w in ws if w.lower() not in t]


def any_of(ans: str, ws: list[str], what: str) -> list[str]:
    t = ans.lower()
    return [] if any(w.lower() in t for w in ws) else [f"falta {what}"]


# ---------- verificaciones de las analiticas (cifras calculadas en la BD) ----------
def c6(ans):
    p = []
    for prod, v in rows("select cve_producto, sum(saldo_mes) from cfg.fact_sdos_captacoloca_m "
                        "where fec_informacion=20260630 group by 1 order by 1"):
        if not has_num(ans, v):
            p.append(f"saldo {prod} esperado {float(v):,.2f}")
    return p


def c7(ans):
    return [] if re.search(r"\b3(\.0+)?\s*%", ans) else ["esperado crecimiento promedio de 3%"]


def c8(ans):
    p = []
    t = ans.lower()
    # exige los cinco componentes con cifras reales
    for opts in (("apertura", "inicial"), ("compra",), ("disposici",), ("pago",)):
        if not any(w in t for w in opts):
            p.append(f"falta componente '{opts[0]}'")
    if not re.search(r"saldo (final|de cierre|cierre)|saldo_mes", t):
        p.append("falta saldo final")
    # las cifras deben coincidir con alguna cuenta TDC de marzo: se valida el saldo final citado
    cand = set(re.findall(r"\d[\d,]*\.\d{2}", ans))
    ok = False
    for c in cand:
        v = float(c.replace(",", ""))
        if rows(f"select 1 from cfg.fact_sdos_captacoloca_m where cve_producto='TDC' and "
                f"fec_informacion=20260331 and (saldo_mes={v} or saldo_apertura={v}) limit 1"):
            ok = True
            break
    if not ok:
        p.append("ninguna cifra de la respuesta corresponde a un saldo real de TDC en marzo")
    return p


def c9(ans):
    top = rows("""select c.segmento_cte from cfg.fact_sdos_captacoloca_m s join dim.dim_cliente c using(num_cte)
                  where s.cve_producto='CHEQUES' and s.fec_informacion=20260630
                  group by 1 order by sum(s.saldo_mes) desc limit 1""")[0][0]
    return [] if top.lower() in ans.lower() else [f"esperado segmento {top}"]


def c10(ans):
    p = []
    for prod, desc, v in rows("""select cve_producto, desc_txn, sum(saldo_txn) from cfg.fact_txn_captacoloca_d
                                 where fec_informacion=20260531 and cve_txn in (100,200)
                                 group by 1,2 order by 1,2"""):
        if not has_num(ans, v):
            p.append(f"{prod} {desc} esperado {float(v):,.2f}")
    return p


@dataclass
class Q:
    n: int
    group: str
    question: str
    expected: str          # texto legible de la respuesta esperada
    check: callable
    tools: list[str]


Q_ = [
    Q(1, "Gobernanza", "¿Quién es el dueño del dato del saldo de cierre de mes de las cuentas y quién es el steward responsable?",
      "Data Owner: Dirección de Finanzas. Data Steward: Steward de Saldos (campo saldo_mes, catálogo).",
      lambda a: words(a, ["Finanzas", "Steward de Saldos"]), ["governance"]),
    Q(2, "Gobernanza", "¿Qué campos de la información de clientes son datos personales y cómo están clasificados?",
      "fec_nac (fecha de nacimiento) y genero_cte (género): clasificación Restringida.",
      lambda a: words(a, ["fec_nac", "genero", "Restringida"]), ["governance"]),
    Q(3, "Gobernanza", "¿De dónde viene el dominio del producto y cuál de las dos fuentes debo considerar la oficial?",
      "Hay dos fuentes: dim_producto.cve_dominio (DEPOSITS/LENDING/TDC) y la columna dominio de la tabla de saldos "
      "(inconsistente). La oficial es dim_producto.cve_dominio.",
      lambda a: words(a, ["dim_producto", "cve_dominio"]) + any_of(a, ["oficial"], "'oficial'"), ["governance"]),
    Q(4, "Gobernanza", "¿Quién es responsable de que la sucursal y el promotor del cliente estén informados?",
      "Data Owner: Dirección de Red Comercial; Steward de Estructura Comercial (regla DQ-10).",
      lambda a: words(a, ["Red Comercial"]) + any_of(a, ["Estructura Comercial"], "'Estructura Comercial'"), ["governance"]),
    Q(5, "Gobernanza", "¿Qué clasificación tienen los importes de las transacciones y quién puede acceder a ellos?",
      "saldo_txn: Confidencial; acceso por perfil (política). Owner: Dirección de Finanzas.",
      lambda a: words(a, ["Confidencial"]) + any_of(a, ["perfil"], "'acceso por perfil'"), ["governance"]),
    Q(6, "Analítica", "¿Cuál es el saldo total de cada producto al cierre de junio de 2026?",
      "Suma de saldo_mes con fec_informacion=20260630 por producto (cifras en tu base: ver sección 'Verdad en tu base').",
      c6, ["run_sql_query"]),
    Q(7, "Analítica", "¿Cuánto creció en promedio el saldo de las tarjetas de crédito de enero a febrero?",
      "≈ 3% (promedio del crecimiento por cuenta TDC, saldo_mes de 20260131 a 20260228).", c7, ["run_sql_query"]),
    Q(8, "Analítica", "Para un cliente en particular, ¿cómo se compone el saldo de su tarjeta de crédito en marzo: saldo inicial, compras, disposiciones, pagos y saldo final?",
      "Saldo final = saldo inicial + compras (400) + disposiciones (450) − pagos (300). El agente debe elegir/pedir un cliente "
      "y mostrar los cinco componentes con cifras reales.", c8, ["run_sql_query"]),
    Q(9, "Analítica", "¿Qué segmento de clientes concentra el mayor saldo en cheques al cierre de junio?",
      "El segmento con mayor suma de saldo_mes de CHEQUES (join con dim_cliente) a 20260630.", c9, ["run_sql_query"]),
    Q(10, "Analítica", "¿Cuánto dinero se movió en retiros y depósitos en mayo, producto por producto?",
      "Solo CHEQUES y AHORRO tienen depósitos (100) y retiros (200); suma de saldo_txn en 20260531. "
      "TDC y C_PERSONAL no tienen retiros/depósitos (tienen pagos, compras y disposiciones).", c10, ["run_sql_query"]),
    Q(11, "Documentos", "¿Cuánto tiempo debemos conservar los saldos y las transacciones, según la política?",
      "10 años (política, sección 6).", lambda a: any_of(a, ["10 años", "10 anos", "diez años", "10 years"], "'10 años'"), ["governance"]),
    Q(12, "Documentos", "¿En cuánto tiempo debo escalar un hallazgo de calidad de severidad alta y a quién?",
      "Máximo 2 días hábiles, al Data Owner (política, sección 1).",
      lambda a: any_of(a, ["2 días", "2 dias", "dos días", "dos dias"], "'2 días hábiles'") + words(a, ["Data Owner"]), ["governance"]),
    Q(13, "Documentos", "¿Qué dice la política sobre cómo corregir que el dominio de los saldos no coincida con el catálogo de productos?",
      "Homologar al catálogo oficial dim_producto.cve_dominio (DEPOSITS, LENDING, TDC); registrar el cambio, no sobrescribir "
      "sin respaldo, notificar a los consumidores; mientras tanto unir con dim_producto (política, sección 5).",
      lambda a: any_of(a, ["homolog"], "'homologar'") + words(a, ["dim_producto"]), ["governance"]),
    Q(14, "Documentos", "¿Cuáles son las seis dimensiones de calidad de datos del marco de gobierno del Reino Unido y a cuál pertenece que un saldo no pueda ser negativo?",
      "Completeness, Uniqueness, Consistency, Timeliness, Validity, Accuracy. Saldo no negativo = Validez (DQ-03, política).",
      lambda a: [f"falta dimensión '{e}'" for e, s in [("completeness", "completitud"), ("uniqueness", "unicidad"),
                 ("consistency", "consistencia"), ("timeliness", "oportunidad"), ("validity", "validez"),
                 ("accuracy", "exactitud")] if e not in a.lower() and s not in a.lower()]
                + words(a, ["negativ"]) + any_of(a, ["validity", "validez"], "'Validez' como dimensión del saldo no negativo"),
      ["governance"]),
    Q(15, "Documentos", "¿Cuántos días después del cierre de mes deben estar disponibles los saldos mensuales?",
      "5 días hábiles después del cierre (política, sección 7).",
      lambda a: any_of(a, ["5 días", "5 dias", "cinco días", "cinco dias"], "'5 días hábiles'"), ["governance"]),
]


def extra_checks(n: int, out: dict) -> list[str]:
    """Revisiones que miran las llamadas a tools, no solo el texto."""
    sqls = " ".join(str(c["args"].get("sql", "")) for c in out.get("calls", []) if c["name"].endswith("run_sql_query"))
    if n == 7 and "'TDC'" not in sqls.upper():
        return ["consulto un producto distinto de TDC (el SQL no filtra por 'TDC')"]
    return []


def hint(exc: Exception) -> str:
    m = str(exc)
    if "connection attempts failed" in m.lower() or "connect" in m.lower():
        return " -> No hay conexion: abre la app de Ollama (y revisa internet para Pinecone/Tavily) y corre .\\run.ps1 check"
    return ""


def truth_section() -> list[str]:
    out = ["## Verdad en tu base (calculada en vivo)\n"]
    out.append("**P6 · saldo por producto al 30-jun-2026**\n")
    for prod, v in rows("select cve_producto, round(sum(saldo_mes),2) from cfg.fact_sdos_captacoloca_m "
                        "where fec_informacion=20260630 group by 1 order by 1"):
        out.append(f"- {prod}: {float(v):,.2f}")
    top = rows("""select c.segmento_cte, round(sum(s.saldo_mes),2) from cfg.fact_sdos_captacoloca_m s
                  join dim.dim_cliente c using(num_cte) where s.cve_producto='CHEQUES' and s.fec_informacion=20260630
                  group by 1 order by 2 desc""")
    out.append("\n**P9 · saldo de CHEQUES por segmento (junio)**\n")
    out += [f"- {s}: {float(v):,.2f}" for s, v in top]
    out.append("\n**P10 · movimientos de mayo**\n")
    out += [f"- {p} {d}: {float(v):,.2f}" for p, d, v in rows(
        """select cve_producto, desc_txn, round(sum(saldo_txn),2) from cfg.fact_txn_captacoloca_d
           where fec_informacion=20260531 and cve_txn in (100,200) group by 1,2 order by 1,2""")]
    r = rows("""select s.num_cte, s.num_cta, s.saldo_apertura,
        coalesce(sum(t.saldo_txn) filter (where t.cve_txn=400),0), coalesce(sum(t.saldo_txn) filter (where t.cve_txn=450),0),
        coalesce(sum(t.saldo_txn) filter (where t.cve_txn=300),0), s.saldo_mes
        from cfg.fact_sdos_captacoloca_m s left join cfg.fact_txn_captacoloca_d t
          on t.num_cta=s.num_cta and t.fec_informacion=s.fec_informacion and t.cve_producto='TDC'
        where s.cve_producto='TDC' and s.fec_informacion=20260331
          and s.num_cta=(select min(num_cta) from cfg.fact_sdos_captacoloca_m where cve_producto='TDC' and fec_informacion=20260331)
        group by 1,2,3,7""")[0]
    out.append("\n**P8 · ejemplo: primera cuenta TDC en marzo**\n")
    out.append(f"- cliente {r[0]}, cuenta {r[1]}: apertura {float(r[2]):,.2f} + compras {float(r[3]):,.2f} + "
               f"disposiciones {float(r[4]):,.2f} − pagos {float(r[5]):,.2f} = saldo final {float(r[6]):,.2f}")
    return out


async def run(sel: list[int], use_web: bool, short: bool = False) -> None:
    qs = [q for q in Q_ if not sel or q.n in sel]
    res = []
    bar = "=" * 78
    async with StewardSession(use_web=use_web) as s:
        for q in qs:
            print(f"\n{bar}\n[P{q.n}] ({q.group}) {q.question}\n{bar}", flush=True)
            try:
                out = await s.ask(q.question)
                used = [x["name"] for x in out["calls"]]
                probs = []
                if out.get("aborted"):
                    probs.append("agente interrumpido: entro en bucle o no llego a respuesta final")
                for t in q.tools:
                    if not any(t in u for u in used):
                        probs.append(f"no uso la tool '{t}'")
                probs += q.check(out["answer"]) + extra_checks(q.n, out)
            except Exception as e:
                out, used = {"answer": f"EXCEPCION: {type(e).__name__}: {e}", "calls": []}, []
                probs = [f"excepcion: {e}{hint(e)}"]
            res.append((q, out, used, probs))
            if not short:
                print("TOOLS:    ", ", ".join(used) or "(ninguna)")
                print("RESPUESTA:")
                print("   " + out["answer"].strip().replace("\n", "\n   "))
                print("ESPERADO: ", q.expected)
            print("RESULTADO:", "[OK] coincide con lo esperado" if not probs else "[REVISAR] " + "; ".join(probs), flush=True)
    ok = sum(1 for r in res if not r[3])
    md = ["# Las 15 preguntas: esperado vs. respuesta del agente (generado automáticamente)\n",
          f"Fecha: {datetime.now():%Y-%m-%d %H:%M} · **{ok}/{len(res)} coinciden con lo esperado**\n",
          "Heurística automática: revisa a mano las respuestas marcadas ❌. Las preguntas de gobernanza y de documentos se "
          "comparan contra la política y el catálogo **sintéticos** del equipo.\n",
          "| # | Tipo | Pregunta | Resultado | Motivo |", "|---|---|---|---|---|"]
    for q, o, u, p in res:
        md.append(f"| {q.n} | {q.group} | {q.question} | {'✅' if not p else '❌'} | {'; '.join(p) or '-'} |")
    md.append("")
    md += truth_section()
    md.append("\n## Detalle\n")
    for q, o, u, p in res:
        md.append(f"### P{q.n} · {q.group}\n\n**Pregunta:** {q.question}\n\n**Esperado:** {q.expected}\n")
        for c in o["calls"]:
            md.append(f"- `{c['name']}({', '.join(f'{k}={v!r}' for k, v in c['args'].items())})`")
        md.append("\n**Respuesta del agente:**\n\n> " + o["answer"].strip().replace("\n", "\n> ") + "\n")
        md.append(f"**Veredicto:** {'✅' if not p else '❌ ' + '; '.join(p)}\n")
    path = ROOT / "docs" / "RESULTADOS_15_PREGUNTAS.md"
    path.write_text("\n".join(md), encoding="utf-8")
    print("\n" + "=" * 78 + "\nRESUMEN")
    for q, o, u, p in res:
        print(f"  P{q.n:<2} {'[OK]     ' if not p else '[REVISAR]'} {q.question[:60]}")
    print(f"\n{ok}/{len(res)} coinciden con lo esperado (revision automatica: lee tambien las respuestas).")
    print(f"Reporte completo: {path}")


if __name__ == "__main__":
    a = sys.argv[1:]
    asyncio.run(run([int(x) for x in a if x.isdigit()], "--no-web" not in a, "--corto" in a))