"""
mcp_postgres_server.py

Servidor MCP que expone la BASE DE DATOS SINTETICA (PostgreSQL) como tools.
Es independiente de cualquier agente/LLM: cualquier cliente MCP puede usarlo.

Tools:
  - get_data_model_guide()       guia semantica del modelo (joins, signos, trampas)
  - list_tables()                tablas de los esquemas dim y cfg + numero de filas
  - describe_table(table)        columnas, tipos, nulabilidad y 3 filas de muestra
  - run_sql_query(sql, max_rows) SELECT de solo lectura (validado y con timeout)
  - data_quality_profile(table)  % de nulos, distintos, min/max por columna
  - run_governance_checks()      reglas de calidad de datos (pasa/falla) con conteos

Seguridad (defensa en capas):
  1. Conexion con rol de solo lectura (steward_ro) si esta configurado en .env
  2. La sesion se abre con default_transaction_read_only=on y statement_timeout
  3. Solo se aceptan sentencias SELECT / WITH, una sola sentencia
  4. Limite de filas devueltas (MAX_ROWS)

IMPORTANTE: transporte stdio -> NO usar print() en stdout (rompe el protocolo MCP).
Para depurar: print(..., file=sys.stderr).

Conexion: ver db_config.py (PostgreSQL embebido por defecto; externo con USE_EMBEDDED_DB=0).
"""

from __future__ import annotations

import os
import re
import sys
from decimal import Decimal
from datetime import date, datetime

import psycopg
from dotenv import load_dotenv
os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")
from fastmcp import FastMCP  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db_config  # noqa: E402

load_dotenv()

mcp = FastMCP("Synthetic Banking DB (PostgreSQL)")

MAX_ROWS = int(os.getenv("SQL_MAX_ROWS", "200"))
ALLOWED_SCHEMAS = ("dim", "cfg")

# ---------------------------------------------------------------------------
# Conexion
# ---------------------------------------------------------------------------


def _connect() -> psycopg.Connection:
    """Abre una conexion nueva con el rol de SOLO LECTURA, en modo read-only y con timeout."""
    return psycopg.connect(
        **db_config.readonly_conninfo(),
        autocommit=True,
        options="-c default_transaction_read_only=on -c statement_timeout=15000",
        connect_timeout=8,
    )


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _rows_to_markdown(columns: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "(0 filas)"
    head = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(_jsonable(v)) for v in r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def _query(sql: str, params=None, max_rows: int = MAX_ROWS) -> tuple[list[str], list[tuple], bool]:
    """Ejecuta y devuelve (columnas, filas, truncado)."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description is None:
            return [], [], False
        cols = [d.name for d in cur.description]
        rows = cur.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        return cols, rows[:max_rows], truncated


# ---------------------------------------------------------------------------
# Validacion de SQL
# ---------------------------------------------------------------------------

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do|"
    r"vacuum|analyze|reindex|cluster|refresh|lock|set|reset|listen|notify|execute|"
    r"prepare|comment|security|pg_read_file|pg_sleep|dblink|lo_import|lo_export)\b",
    re.IGNORECASE,
)


def _validate_select(sql: str) -> str | None:
    """Devuelve un mensaje de error si el SQL no es un SELECT seguro; None si esta bien."""
    cleaned = re.sub(r"--[^\n]*", " ", sql)               # comentarios de linea
    cleaned = re.sub(r"/\*.*?\*/", " ", cleaned, flags=re.S)  # comentarios de bloque
    cleaned = cleaned.strip().rstrip(";").strip()
    if not cleaned:
        return "La consulta esta vacia."
    # Ignora literales de texto ('a;b', 'DO NOT SET') al revisar ';' y palabras prohibidas
    without_strings = re.sub(r"'(?:[^']|'')*'", "''", cleaned)
    if ";" in without_strings:
        return "Solo se permite UNA sentencia (se detecto ';' en medio)."
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        return "Solo se permiten consultas SELECT (o WITH ... SELECT)."
    bad = _FORBIDDEN.search(without_strings)
    if bad:
        return f"Palabra no permitida en una consulta de solo lectura: {bad.group(0).upper()}."
    return None


def _check_table(table: str) -> tuple[str, str] | str:
    """Valida 'esquema.tabla' contra la lista blanca. Devuelve (schema, table) o un error."""
    parts = table.strip().split(".")
    if len(parts) != 2 or parts[0] not in ALLOWED_SCHEMAS or not re.fullmatch(r"[a-z_0-9]+", parts[1]):
        return f"Tabla invalida '{table}'. Usa 'esquema.tabla' con esquema en {ALLOWED_SCHEMAS}. Llama list_tables()."
    return parts[0], parts[1]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

DATA_MODEL_GUIDE = """
MODELO DE DATOS (banco sintetico, 5,000 clientes, 4 productos, ene-jun 2026)

TABLAS
- dim.dim_cliente (5,000): PK num_cte. tipo_persona PF/PM, genero_cte, segmento_cte
  (PREMIUM/PREFERENTE/MASIVO), fec_nac, fec_alta.
  OJO: giro_empresa, cve_territorio, cve_dir, cve_subdir, cve_sucursal, cve_promotor
  existen pero estan 100% NULL en los datos sinteticos.
- dim.dim_producto (4): CHEQUES, AHORRO (grupo CAPTACION); C_PERSONAL, TDC (grupo COLOCACION).
- dim.dim_txn (9 filas, SIN PK): catalogo de transacciones. cve_txn se REPITE entre productos
  (100/200 en CHEQUES y AHORRO; 300/450 en C_PERSONAL y TDC). Para unir usar SIEMPRE
  cve_producto Y cve_txn, o se multiplican las filas.
- cfg.fact_sdos_captacoloca_m (120,000): foto MENSUAL de saldos, una fila por cuenta y mes.
  * fec_informacion = fecha de cierre de mes en formato entero YYYYMMDD
    (20260131, 20260228, 20260331, 20260430, 20260531, 20260630). USAR ESTA COLUMNA para
    filtrar por mes.
  * saldo_mes = saldo de cierre del mes; saldo_apertura = saldo al inicio del mes
    (enero: saldo inicial; feb-jun: cierre del mes anterior).
  * cve_mes_alta = 202601 en TODAS las filas: es el mes de apertura de la cuenta, NO el mes
    de la foto. No sirve para filtrar meses.
  * num_cta: CHEQUES 100000-104999, AHORRO 200000-204999, TDC 300000-304999,
    C_PERSONAL 400000-404999. Cada cliente tiene exactamente 1 cuenta por producto.
- cfg.fact_txn_captacoloca_d (225,000): transacciones. SOLO feb-jun 2026 (no hay de enero).
  * saldo_txn es SIEMPRE positivo; el signo economico lo da producto + cve_txn.
  * fec_txn cae el dia 15 de cada mes; cve_mes_txn = YYYYMM; fec_informacion = fin de mes.

SIGNOS ECONOMICOS (efecto sobre saldo_mes)
- CHEQUES/AHORRO: cve_txn 100 DEPOSITO suma; 200 RETIRO resta.
- C_PERSONAL: 450 DISPOSICIONES suma deuda; 300 PAGOS resta.
- TDC: 400 COMPRAS y 450 DISPOSICIONES suman deuda; 300 PAGOS resta.
- Captacion = dinero del cliente en el banco (pasivo). Colocacion = deuda del cliente (activo/cartera).
  No sumar captacion con colocacion sin aclararlo.

CRECIMIENTO DISENADO DEL SALDO vs. cierre anterior
- Feb: captacion +2.0%, colocacion +3.0%. Mar-Jun: captacion +1.0%, colocacion +2.2%.

INCONSISTENCIAS CONOCIDAS (hallazgos de gobernanza)
- cfg.fact_sdos_captacoloca_m.dominio: enero usa CAPTACION/COLOCACION, pero feb-jun usa
  DEPOSITS/LENDING/TDC (igual que dim_producto.cve_dominio). No filtrar por 'dominio' en
  saldos sin unificar; mejor unir con dim.dim_producto por cve_producto.
- Columnas de dim_cliente 100% NULL (ver arriba).

MESES -> fec_informacion (entero YYYYMMDD, fin de mes)
  enero 20260131 | febrero 20260228 | marzo 20260331 | abril 20260430 | mayo 20260531 | junio 20260630
  Para transacciones usa cve_mes_txn (YYYYMM): 202602 ... 202606.
  El saldo SIEMPRE se llama saldo_mes (cierre) o saldo_apertura. NO existen columnas
  "saldo", "saldo_mensual" ni "fecha". Las fechas son fec_informacion / fec_alta / fec_txn.

EJEMPLOS DE SQL CORRECTO (copia el patron)
-- Saldo total de TDC al cierre de junio de 2026
SELECT ROUND(SUM(saldo_mes),2) AS saldo_total FROM cfg.fact_sdos_captacoloca_m WHERE cve_producto = 'TDC' AND fec_informacion = 20260630;
-- Saldo total por producto en un mes
SELECT cve_producto, ROUND(SUM(saldo_mes),2) AS saldo_total FROM cfg.fact_sdos_captacoloca_m WHERE fec_informacion = 20260630 GROUP BY cve_producto ORDER BY cve_producto;
-- Clientes por tipo de persona
SELECT tipo_persona, COUNT(*) AS clientes FROM dim.dim_cliente GROUP BY tipo_persona ORDER BY tipo_persona;
-- Crecimiento promedio del saldo de un producto, febrero contra enero
SELECT ROUND(AVG(100.0 * (f.saldo_mes - e.saldo_mes) / e.saldo_mes), 2) AS crecimiento_pct FROM cfg.fact_sdos_captacoloca_m f JOIN cfg.fact_sdos_captacoloca_m e ON e.num_cta = f.num_cta AND e.fec_informacion = 20260131 WHERE f.cve_producto = 'TDC' AND f.fec_informacion = 20260228;
-- Importe de transacciones de TDC por tipo en marzo
SELECT t.desc_txn, ROUND(SUM(t.saldo_txn),2) AS importe FROM cfg.fact_txn_captacoloca_d t WHERE t.cve_producto = 'TDC' AND t.cve_mes_txn = 202603 GROUP BY t.desc_txn ORDER BY t.desc_txn;
-- Saldo de CHEQUES por segmento de cliente en junio
SELECT c.segmento_cte, ROUND(SUM(s.saldo_mes),2) AS saldo_total FROM cfg.fact_sdos_captacoloca_m s JOIN dim.dim_cliente c ON c.num_cte = s.num_cte WHERE s.cve_producto = 'CHEQUES' AND s.fec_informacion = 20260630 GROUP BY c.segmento_cte ORDER BY c.segmento_cte;

BUENAS PRACTICAS PARA ESCRIBIR SQL
- Prefija esquemas (cfg., dim.). Usa LIMIT. Redondea con ROUND(x, 2).
- Saldos totales de un mes: WHERE fec_informacion = 20260630 (ejemplo junio).
""".strip()


def _columns_listing(only: list[tuple[str, str]] | None = None) -> str:
    """Lista EXACTA de columnas (esquema.tabla: col tipo, ...) tomada del catalogo vivo."""
    _, rows, _ = _query(
        "SELECT table_schema, table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = ANY(%s) ORDER BY table_schema, table_name, ordinal_position",
        (list(ALLOWED_SCHEMAS),),
        max_rows=2000,
    )
    tables: dict[tuple[str, str], list[str]] = {}
    for schema, table, col, typ in rows:
        tables.setdefault((schema, table), []).append(f"{col} ({typ})")
    lines = [f"{sch}.{tab}: " + ", ".join(cols) for (sch, tab), cols in tables.items() if only is None or (sch, tab) in only]
    return "\n".join(lines)


@mcp.tool()
def get_data_model_guide() -> str:
    """Return the semantic guide of the database (tables, EXACT column names, join rules,
    month codes, economic sign of transactions, working SQL examples and KNOWN data
    inconsistencies). Call this FIRST before writing any SQL."""
    try:
        cols = _columns_listing()
    except Exception as exc:  # la guia estatica sigue siendo util sin BD
        cols = f"(no se pudo leer el catalogo: {type(exc).__name__})"
    return DATA_MODEL_GUIDE + "\n\nCOLUMNAS EXACTAS (usa SOLO estos nombres)\n" + cols


@mcp.tool()
def list_tables() -> str:
    """List the tables of the schemas dim and cfg with their row count."""
    try:
        _, tables, _ = _query(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' AND table_schema = ANY(%s) ORDER BY 1, 2",
            (list(ALLOWED_SCHEMAS),),
        )
        rows = []
        for schema, name in tables:  # nombres tomados del catalogo, no del usuario
            _, res, _ = _query(f'SELECT count(*) FROM "{schema}"."{name}"')
            rows.append((schema, name, res[0][0]))
        return _rows_to_markdown(["esquema", "tabla", "filas"], rows)
    except Exception as exc:
        return f"Error: {type(exc).__name__}: {exc}"


@mcp.tool()
def describe_table(table: str) -> str:
    """Describe a table: columns, data types, nullability and 3 sample rows.

    Args:
        table: 'schema.table', e.g. 'cfg.fact_sdos_captacoloca_m' or 'dim.dim_cliente'.
    """
    checked = _check_table(table)
    if isinstance(checked, str):
        return checked
    schema, name = checked
    try:
        cols, rows, _ = _query(
            """
            SELECT column_name AS columna, data_type AS tipo, is_nullable AS nulable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, name),
        )
        if not rows:
            return f"La tabla {table} no existe. Llama list_tables()."
        out = [f"### {table}\n", _rows_to_markdown(cols, rows)]
        scols, srows, _ = _query(f"SELECT * FROM {schema}.{name} LIMIT 3")  # nombre validado arriba
        out += ["\nMuestra (3 filas):\n", _rows_to_markdown(scols, srows)]
        return "\n".join(out)
    except Exception as exc:
        return f"Error: {type(exc).__name__}: {exc}"


def _split_statements(sql: str) -> list[str]:
    """Divide por ';' respetando comillas simples; descarta fragmentos vacios o solo comentarios."""
    out, buf, in_quote = [], [], False
    for ch in sql:
        if ch == "'":
            in_quote = not in_quote
        if ch == ";" and not in_quote:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [x.strip() for x in out if re.sub(r"--[^\n]*|/\*.*?\*/|\s", "", x, flags=re.S)]


def _sql_error_message(exc: Exception, sql: str) -> str:
    """Mensaje legible para que el LLM pueda corregir su SQL (con pista de columnas reales)."""
    msg = f"ERROR SQL: {type(exc).__name__}: {str(exc).splitlines()[0]}"
    if type(exc).__name__ in ("UndefinedColumn", "UndefinedTable", "AmbiguousColumn"):
        try:
            refs = [(m.group(1), m.group(2)) for m in re.finditer(r"\b(dim|cfg)\.([a-z_0-9]+)", sql)]
            msg += (
                "\n\nPISTA: esa columna/tabla NO existe. Columnas reales"
                + (" de las tablas que usaste" if refs else " de todas las tablas")
                + " (usa SOLO estos nombres; el saldo es saldo_mes y los meses se filtran con fec_informacion):\n"
                + _columns_listing(refs or None)
            )
        except Exception:
            pass
    return msg


@mcp.tool()
def run_sql_query(sql: str, max_rows: int = 50) -> str:
    """Run one read-only SQL SELECT (PostgreSQL) -- or up to 3 SELECTs separated by ';' --
    against the synthetic banking database and return each result as a markdown table.
    Writes are rejected. Always prefix schemas (cfg., dim.) and use LIMIT / aggregates.
    Use the exact column names of the data model guide.

    Args:
        sql: a SELECT or WITH ... SELECT statement (max 3 statements separated by ';').
        max_rows: maximum rows to return per statement (hard cap applies).
    """
    statements = _split_statements(sql)
    if not statements:
        return "CONSULTA RECHAZADA: La consulta esta vacia."
    if len(statements) > 3:
        return "CONSULTA RECHAZADA: maximo 3 sentencias SELECT por llamada."
    for st in statements:
        error = _validate_select(st)
        if error:
            return f"CONSULTA RECHAZADA: {error}"
    limit = max(1, min(int(max_rows), MAX_ROWS))
    blocks = []
    for i, st in enumerate(statements, 1):
        try:
            cols, rows, truncated = _query(st, max_rows=limit)
        except Exception as exc:
            return _sql_error_message(exc, st) + (f"\n(fallo la sentencia {i} de {len(statements)})" if len(statements) > 1 else "")
        text = _rows_to_markdown(cols, rows)
        if truncated:
            text += f"\n\n(Resultado truncado a {limit} filas. Agrega agregaciones o LIMIT.)"
        blocks.append(f"**Resultado {i}**\n{text}" if len(statements) > 1 else text)
    return "\n\n".join(blocks)


@mcp.tool()
def data_quality_profile(table: str) -> str:
    """Profile a table for data-quality: row count and, per column, % NULL,
    number of distinct values and min/max. Use it to find incomplete columns.

    Args:
        table: 'schema.table', e.g. 'dim.dim_cliente'.
    """
    checked = _check_table(table)
    if isinstance(checked, str):
        return checked
    schema, name = checked
    try:
        _, cols, _ = _query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
            (schema, name),
        )
        if not cols:
            return f"La tabla {table} no existe."
        names = [c[0] for c in cols]
        selects = ["count(*) AS total"]
        for c in names:
            selects.append(f'count(*) FILTER (WHERE "{c}" IS NULL) AS "{c}__nulls"')
            selects.append(f'count(DISTINCT "{c}") AS "{c}__distinct"')
            selects.append(f'min("{c}")::text AS "{c}__min"')
            selects.append(f'max("{c}")::text AS "{c}__max"')
        _, res, _ = _query(f"SELECT {', '.join(selects)} FROM {schema}.{name}")
        r = res[0]
        total = r[0]
        lines = []
        for i, c in enumerate(names):
            nulls, distinct, vmin, vmax = r[1 + 4 * i : 5 + 4 * i]
            pct = 100.0 * nulls / total if total else 0
            lines.append((c, f"{pct:.1f}%", nulls, distinct, vmin, vmax))
        header = f"### Perfil de {table} ({total:,} filas)\n"
        return header + _rows_to_markdown(
            ["columna", "pct_nulos", "nulos", "distintos", "min", "max"], lines
        )
    except Exception as exc:
        return f"Error: {type(exc).__name__}: {exc}"


# Reglas de calidad ejecutables. Cada una devuelve el numero de filas que VIOLAN la regla.
GOVERNANCE_CHECKS: list[tuple[str, str, str]] = [
    ("DQ-01 Unicidad de cuenta por mes",
     "num_cta + fec_informacion no debe repetirse en saldos",
     "SELECT count(*) FROM (SELECT num_cta, fec_informacion FROM cfg.fact_sdos_captacoloca_m "
     "GROUP BY 1,2 HAVING count(*) > 1) t"),
    ("DQ-02 Completitud de saldos",
     "saldo_apertura y saldo_mes no deben ser NULL",
     "SELECT count(*) FROM cfg.fact_sdos_captacoloca_m WHERE saldo_apertura IS NULL OR saldo_mes IS NULL"),
    ("DQ-03 Validez: saldo no negativo",
     "saldo_mes >= 0",
     "SELECT count(*) FROM cfg.fact_sdos_captacoloca_m WHERE saldo_mes < 0"),
    ("DQ-04 Validez: importe de transaccion positivo",
     "saldo_txn > 0",
     "SELECT count(*) FROM cfg.fact_txn_captacoloca_d WHERE saldo_txn IS NULL OR saldo_txn <= 0"),
    ("DQ-05 Integridad referencial cuenta->cliente",
     "todo num_cte de saldos debe existir en dim_cliente",
     "SELECT count(*) FROM cfg.fact_sdos_captacoloca_m s "
     "LEFT JOIN dim.dim_cliente c ON c.num_cte = s.num_cte WHERE c.num_cte IS NULL"),
    ("DQ-06 Integridad referencial txn->catalogo",
     "(cve_producto, cve_txn) de transacciones debe existir en dim_txn",
     "SELECT count(*) FROM cfg.fact_txn_captacoloca_d t LEFT JOIN dim.dim_txn d "
     "ON d.cve_producto = t.cve_producto AND d.cve_txn = t.cve_txn WHERE d.cve_txn IS NULL"),
    ("DQ-07 Consistencia: dominio unico por producto",
     "cada cve_producto debe tener UN solo valor de dominio en saldos",
     "SELECT count(*) FROM (SELECT cve_producto FROM cfg.fact_sdos_captacoloca_m "
     "GROUP BY 1 HAVING count(DISTINCT dominio) > 1) t"),
    ("DQ-08 Consistencia: dominio de saldos = catalogo",
     "dominio de saldos debe coincidir con dim_producto.cve_dominio (filas que no coinciden)",
     "SELECT count(*) FROM cfg.fact_sdos_captacoloca_m s JOIN dim.dim_producto p "
     "ON p.cve_producto = s.cve_producto WHERE s.dominio <> p.cve_dominio"),
    ("DQ-09 Mayoria de edad (PF)",
     "clientes PF deben tener 18+ anos",
     "SELECT count(*) FROM dim.dim_cliente WHERE tipo_persona = 'PF' "
     "AND age(date '2026-06-30', fec_nac) < interval '18 years'"),
    ("DQ-10 Completitud: atributos organizacionales de cliente",
     "cve_territorio, cve_sucursal y cve_promotor deben estar informados (clientes que NO los tienen)",
     "SELECT count(*) FROM dim.dim_cliente WHERE cve_territorio IS NULL "
     "OR cve_sucursal IS NULL OR cve_promotor IS NULL"),
    ("DQ-11 Conciliacion saldo vs movimientos (feb-jun)",
     "saldo_mes - (saldo_apertura +/- movimientos) debe ser 0 (cuentas-mes con diferencia > 0.01)",
     """WITH mov AS (
          SELECT num_cta, cve_mes_txn,
                 SUM(CASE WHEN (cve_producto IN ('CHEQUES','AHORRO') AND cve_txn = 100)
                            OR (cve_producto = 'C_PERSONAL' AND cve_txn = 450)
                            OR (cve_producto = 'TDC' AND cve_txn IN (400,450)) THEN saldo_txn
                          ELSE -saldo_txn END) AS neto
          FROM cfg.fact_txn_captacoloca_d GROUP BY 1,2)
        SELECT count(*) FROM cfg.fact_sdos_captacoloca_m s
        JOIN mov m ON m.num_cta = s.num_cta
                  AND m.cve_mes_txn = (s.fec_informacion / 100)
        WHERE abs(s.saldo_mes - (s.saldo_apertura + m.neto)) > 0.01"""),
]


@mcp.tool()
def run_governance_checks() -> str:
    """Run the predefined data-quality / governance rules (DQ-01..DQ-11) against the
    database and report, for each rule, how many rows VIOLATE it (0 = passes).
    Use it to answer 'is the data compliant?' and then ground recommendations with
    search_governance_knowledge."""
    rows = []
    for name, desc, sql in GOVERNANCE_CHECKS:
        try:
            _, res, _ = _query(sql)
            n = res[0][0]
            rows.append((name, "PASA" if n == 0 else "FALLA", n, desc))
        except Exception as exc:
            rows.append((name, "ERROR", None, f"{type(exc).__name__}: {str(exc).splitlines()[0]}"))
    text = _rows_to_markdown(["regla", "estado", "filas_que_violan", "descripcion"], rows)
    failing = [r[0].split(" ")[0] for r in rows if r[1] == "FALLA"]
    if failing:
        text += (
            f"\n\nREGLAS QUE FALLAN: {', '.join(failing)}.\n"
            "SIGUIENTE PASO OBLIGATORIO: para recomendar que hacer, llama ahora a "
            f"governance_search_governance_knowledge con una consulta como "
            f"'remediacion {' '.join(failing)} politica de calidad de datos' y cita el archivo fuente. "
            "No inventes remediaciones: usa solo lo que devuelva esa busqueda."
        )
    return text


if __name__ == "__main__":
    mcp.run(show_banner=False)  # stdio