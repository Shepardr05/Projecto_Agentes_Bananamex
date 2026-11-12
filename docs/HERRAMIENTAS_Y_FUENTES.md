# Herramientas y fuentes de gobernanza

## Herramientas MCP

Cada tool indica qué roles la pueden usar (ver [`ROLES.md`](ROLES.md)); las de admin devuelven `ACCESO DENEGADO` al rol `usuario`.

### Servidor `postgres` (`src/mcp_postgres_server.py`)
| Tool | Entrada | Salida / comportamiento |
|---|---|---|
| `get_data_model_guide` | – | Texto con tablas, reglas de join, significado de columnas, signo económico de transacciones e inconsistencias conocidas |
| `list_tables` | – | Tablas de `dim` y `cfg` con número de filas |
| `describe_table` (admin) | `table` = `esquema.tabla` | Columnas, tipos, nulabilidad y 3 filas de muestra con datos personales enmascarados (lista blanca de esquemas) |
| `run_sql_query` | `sql`, `max_rows` | Un SELECT/WITH de solo lectura → tabla markdown. Rechaza escrituras, `;` encadenados y palabras peligrosas; timeout 15 s; tope de filas. El rol `usuario` no puede leer `fec_nac` ni `genero_cte` |
| `data_quality_profile` (admin) | `table` | Por columna: % nulos, distintos, min, max (valores personales enmascarados) |
| `run_governance_checks` (admin) | – | 11 reglas DQ con PASA/FALLA y filas que violan |
| `get_audit_log` (admin) | `limit` | Últimos registros de auditoría: quién llamó qué tool, con qué argumentos y si se permitió |

Reglas: DQ-01 unicidad de cuenta-mes · DQ-02 saldos no nulos · DQ-03 saldo ≥ 0 · DQ-04 importe txn > 0 · DQ-05 integridad cuenta→cliente · DQ-06 integridad txn→catálogo · DQ-07 dominio único por producto · DQ-08 dominio = catálogo · DQ-09 PF mayor de edad · DQ-10 atributos organizacionales informados · DQ-11 conciliación saldo vs. movimientos.
Resultado esperado con los datos del socio: **fallan DQ-07, DQ-08 y DQ-10**; el resto pasa.

### Servidor `governance` (`src/mcp_governance_server.py`)
| Tool | Entrada | Salida |
|---|---|---|
| `search_governance_knowledge` | `query` (ES/EN) | Hasta `RAG_TOP_K` fragmentos con `SOURCE: archivo, page/row (score)`; si ninguno supera `MIN_SCORE` → `NOT_IN_DOCUMENTS` |

### Tool local opcional
`web_search` (Tavily, `langchain-tavily`): se activa automáticamente si existe `TAVILY_API_KEY` en `.env`; el prompt la restringe a preguntas ajenas a datos y gobernanza. El agente imprime `Tools disponibles: ... web_search` al iniciar, y `check_setup` hace una búsqueda de prueba.

## Fuentes de gobernanza (`rag_documents/`)
| Archivo | Origen | Contenido |
|---|---|---|
| The Government Data Quality Framework - GOV.UK.pdf | GOV.UK | Principios, ciclo de vida, seis dimensiones de calidad |
| The Government Data Quality Framework_ guidance - GOV.UK.pdf | GOV.UK | Guía: plan de acción, causa raíz, metadatos, madurez |
| onsdataqualitypolicy.pdf | ONS | Política de gestión de calidad de datos, roles |
| politica_calidad_datos_sintetica.md | **Equipo (ejemplo)** | Roles, clasificación, reglas DQ-01..11, remediación, retención |
| catalogo_datos_sintetico.csv | **Equipo (ejemplo)** | 36 campos: descripción, clasificación, dueño, steward, retención, regla |

Los dos últimos son **sintéticos y deben sustituirse por documentos oficiales del socio**.

## Datos
Scripts del socio formador: `sql/001`, `002`, `003` (sin modificar). Aporte del equipo: `sql/000` (esquema `cfg`); los roles de solo lectura (`steward_ro` y `steward_usuario`) los crea `scripts/load_db.py`.
