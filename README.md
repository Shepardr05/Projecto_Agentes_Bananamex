# Data Steward · Beta Sprint 2

Agente de Data Steward para un banco (datos sintéticos) que:

1. **Consulta una base PostgreSQL** (scripts SQL del socio formador) mediante un **servidor MCP** de solo lectura.
2. **Fundamenta recomendaciones en gobernanza** con un **RAG** (Pinecone) expuesto por un **segundo servidor MCP**.
3. **Busca en internet (Tavily)** como último recurso.

Cada respuesta imprime la traza de tools (SQL ejecutado y resultado), como evidencia de que consulta la base.

Arquitectura: [`docs/arquitectura.png`](docs/arquitectura.png) · [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)

## Ejecutar (Windows)

**Requisitos:** [Python 3.11+](https://www.python.org/downloads/) (con *Add to PATH*) y [Ollama](https://ollama.com/download) abierto. No se necesita Docker ni instalar PostgreSQL.

**1. Crear `.env`** en la raíz del proyecto (cambiar solo las dos claves):

```
PINECONE_API_KEY=pega_tu_clave_de_pinecone
TAVILY_API_KEY=pega_tu_clave_de_tavily
INDEX_NAME=rag-governance
MIN_SCORE=0.5
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:latest
EMBEDDING_MODEL=bge-m3
USE_EMBEDDED_DB=1
POSTGRES_DB=banco_sintetico
```

**2. Instalar todo** (crear el entorno, instalar dependencias, cargar la base, descargar modelos, crear el índice de Pinecone y lo llena):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

**3. Crear usuarios** (roles `usuario` y `admin`, ver [`docs/ROLES.md`](docs/ROLES.md)):

```powershell
python src\auth.py add lalo admin
python src\auth.py add analista usuario
```

El agente pide usuario y contraseña al iniciar (o usa `--user NOMBRE`; la contraseña también puede ir en `STEWARD_PASSWORD`). Si ya tenías la base cargada antes de los roles, corre una vez `.\run.ps1 load-db` (no borra datos) para crear el rol de BD `steward_usuario`; `setup.ps1` también lo hace.

**4. Usar el proyecto:**

```powershell
.\run.ps1 demo                      # demo con 6 preguntas
.\run.ps1 ask "¿Cuál es el saldo total de TDC en junio de 2026?"
.\run.ps1 chat --user lalo          # chat interactivo
.\run.ps1 tests                     # 14 casos (T1-T10 y R1-R4 de roles) -> docs\RESULTADOS_PRUEBAS.md
.\run.ps1 preguntas                 # las 15 preguntas + revisión -> docs\RESULTADOS_15_PREGUNTAS.md
.\run.ps1 pytest                    # 45 pruebas del servidor MCP de SQL y de roles
.\run.ps1 check                     # diagnóstico del entorno
.\run.ps1 raw --user lalo           # MCP sin LLM
.\run.ps1 load-db                   # crea/actualiza roles de la BD y datos si faltan (idempotente)
.\run.ps1 stop-db                   # detiene PostgreSQL embebido
```

`demo`, `ask`, `chat`, `tests`, `preguntas`, `respuestas`, `langsmith` y `raw` piden login; para las 15 preguntas usa un usuario `admin` (algunas usan `describe_table` y las reglas DQ).

Mac/Linux: `bash setup.sh` y `./run.sh demo`.

Problemas comunes: si falla `Ollama no responde`, abre la app de Ollama; si el RAG no devuelve fuentes, bajar `MIN_SCORE` a 0.3.

## Estructura

```
├── setup.ps1 / run.ps1       instalación y atajos
├── sql/                      000 esquema cfg (equipo) · 001-003 scripts del socio (sin modificar)
├── rag_documents/            PDFs GOV.UK / ONS + política y catálogo sintéticos + síntesis de fuentes
│                             públicas (Banamex, LIC, LFPDPPP, CNBV, BCBS 239); ver su README
├── src/                      agent · auth (roles) · mcp_postgres_server · mcp_governance_server
│                             ingest_governance · run_test_cases · mcp_raw_client · db_config · common
├── scripts/                  setup_all · load_db · check_setup · stop_db
├── tests/                    45 pruebas pytest del MCP de SQL y de roles
└── docs/                     arquitectura · roles · pruebas · análisis de fallos · herramientas · guía de demo
```

## Herramientas

| Origen | Tool | Rol | Función |
|---|---|---|---|
| MCP postgres | `get_data_model_guide` | usuario, admin | Guía del modelo: joins, signos, trampas |
| MCP postgres | `list_tables` | usuario, admin | Tablas y número de filas |
| MCP postgres | `describe_table` | admin | Esquema y muestra (datos personales enmascarados) |
| MCP postgres | `run_sql_query` | usuario, admin | Hasta 3 SELECT validados, con timeout y tope de filas |
| MCP postgres | `data_quality_profile` | admin | % nulos, distintos, min/max |
| MCP postgres | `run_governance_checks` | admin | Reglas DQ-01 a DQ-11 |
| MCP postgres | `get_audit_log` | admin | Últimas llamadas a tools: quién, qué y si se permitió |
| MCP governance | `search_governance_knowledge` | usuario, admin | RAG con fuente, página y score |
| Local | `web_search` | usuario, admin | Tavily (no es MCP) |

## Seguridad

- Rol `steward_ro` (solo `SELECT`), sesión de solo lectura, `statement_timeout` y validación de cada sentencia.
- **Roles de la app** (`usuario` y `admin`): login, tools filtradas por rol, validación en cada servidor MCP y auditoría en `logs/audit.jsonl`. El rol `usuario` se conecta con el rol de BD `steward_usuario`, sin `fec_nac` ni `genero_cte` (la base rechaza incluso `SELECT *` y los filtros sobre esas columnas). Detalle y límites: [`docs/ROLES.md`](docs/ROLES.md).
- `.env` está en `.gitignore`; solo se versiona `.env.example`. No hay credenciales en el código.

## Pruebas

- `pytest`: 45/45 pasan (incluye 26 pruebas de roles, sin LLM).
- Casos con el agente (`llama3.1`): **7/10 pasan** (fallan T1, T6 y T8). En los fallos el modelo no usa bien el resultado de las tools; los resultados varían entre corridas. Los casos nuevos **R1-R4** (roles) dependen de que el LLM obedezca y están pendientes de correr con Ollama.
- Detalle: [`docs/RESULTADOS_PRUEBAS.md`](docs/RESULTADOS_PRUEBAS.md) · Causas: [`docs/ANALISIS_FALLOS.md`](docs/ANALISIS_FALLOS.md)

## Limitaciones

- `langchain.mcp` está en beta. Un LLM local de 8B puede fallar al redactar la respuesta; se puede cambiar con `LLM_PROVIDER=google|anthropic`.
- `politica_calidad_datos_sintetica.md` y `catalogo_datos_sintetico.csv` son ejemplos escritos por el equipo, no documentos oficiales de Banamex.
- Los roles son control de acceso a nivel de aplicación: quien tenga shell en la máquina puede cambiar `STEWARD_ROLE`, y el `admin` puede leer datos personales fila por fila con SQL libre (lo frenan el prompt y la auditoría). Ver `docs/ROLES.md`.

## Fuentes de gobernanza

UK Government Data Quality Framework y su guía (GOV.UK) · ONS Data Quality Management Policy · política y catálogo sintéticos del equipo · síntesis de fuentes públicas sobre Banamex y el marco regulatorio mexicano (LIC, Código de Comercio, LFPDPPP 2025, CNBV, CUB Anexo 52, BCBS 239) y un glosario. Banamex no publica su política interna de gobierno de datos; ver [`rag_documents/README.md`](rag_documents/README.md).
