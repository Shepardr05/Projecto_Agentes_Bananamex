# Data Steward · Beta Sprint 2

Agente de Data Steward para un banco (datos sintéticos) que:

1. **Consulta una base PostgreSQL** (scripts SQL del socio formador) mediante un **servidor MCP** de solo lectura.
2. **Fundamenta recomendaciones en gobernanza** con un **RAG** (Pinecone) expuesto por un **segundo servidor MCP**.
3. **Busca en internet (Tavily)** como último recurso.

Cada respuesta imprime la traza de tools (SQL ejecutado y resultado), como evidencia de que consulta la base.

Arquitectura: [`docs/arquitectura.png`](docs/arquitectura.png) · [`docs/ARQUITECTURA.txt`](docs/ARQUITECTURA.txt)

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

**3. Usar el proyecto:**

```powershell
.\run.ps1 demo                      # demo con 6 preguntas
.\run.ps1 ask "¿Cuál es el saldo total de TDC en junio de 2026?"
.\run.ps1 chat                      # chat interactivo
.\run.ps1 tests                     # 10 casos -> docs\RESULTADOS_PRUEBAS.md
.\run.ps1 pytest                    # 19 pruebas del servidor MCP de SQL
.\run.ps1 check                     # diagnóstico del entorno
.\run.ps1 raw                       # MCP sin LLM
.\run.ps1 stop-db                   # detiene PostgreSQL embebido
```

Mac/Linux: `bash setup.sh` y `./run.sh demo`.

Problemas comunes: si falla `Ollama no responde`, abre la app de Ollama; si el RAG no devuelve fuentes, bajar `MIN_SCORE` a 0.3.

## Estructura

```
├── setup.ps1 / run.ps1       instalación y atajos
├── sql/                      000 esquema cfg (equipo) · 001-003 scripts del socio (sin modificar)
├── rag_documents/            PDFs GOV.UK / ONS + política y catálogo sintéticos
├── src/                      agent · mcp_postgres_server · mcp_governance_server · ingest_governance
│                             run_test_cases · mcp_raw_client · db_config · common
├── scripts/                  setup_all · load_db · check_setup · stop_db
├── tests/                    19 pruebas pytest del MCP de SQL
└── docs/                     arquitectura · pruebas · análisis de fallos · herramientas · guía de demo
```

## Herramientas

| Origen | Tool | Función |
|---|---|---|
| MCP postgres | `get_data_model_guide` | Guía del modelo: joins, signos, trampas |
| MCP postgres | `list_tables`, `describe_table` | Esquema y muestra |
| MCP postgres | `run_sql_query` | Hasta 3 SELECT validados, con timeout y tope de filas |
| MCP postgres | `data_quality_profile` | % nulos, distintos, min/max |
| MCP postgres | `run_governance_checks` | Reglas DQ-01 a DQ-11 |
| MCP governance | `search_governance_knowledge` | RAG con fuente, página y score |
| Local | `web_search` | Tavily (no es MCP) |

## Seguridad

- Rol `steward_ro` (solo `SELECT`), sesión de solo lectura, `statement_timeout` y validación de cada sentencia.
- `.env` está en `.gitignore`; solo se versiona `.env.example`. No hay credenciales en el código.

## Pruebas

- `pytest`: 19/19 pasan.
- Casos con el agente (`llama3.1`): **7/10 pasan** (fallan T1, T6 y T8). En los fallos el modelo no usa bien el resultado de las tools; los resultados varían entre corridas.
- Detalle: [`docs/RESULTADOS_PRUEBAS.md`](docs/RESULTADOS_PRUEBAS.md) · Causas: [`docs/ANALISIS_FALLOS.md`](docs/ANALISIS_FALLOS.md)

## Limitaciones

- `langchain.mcp` está en beta. Un LLM local de 8B puede fallar al redactar la respuesta; se puede cambiar con `LLM_PROVIDER=google|anthropic`.
- `politica_calidad_datos_sintetica.md` y `catalogo_datos_sintetico.csv` son ejemplos escritos por el equipo, no documentos oficiales de Banamex.

## Fuentes de gobernanza

UK Government Data Quality Framework y su guía (GOV.UK) · ONS Data Quality Management Policy · política y catálogo sintéticos del equipo.
