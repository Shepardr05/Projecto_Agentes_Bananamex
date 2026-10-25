# Data Steward Beta (RAG + búsqueda web de respaldo)

## Objetivo del Data Steward

Asistente que responde preguntas de **gobierno y calidad de datos** a partir de documentos oficiales (RAG sobre Pinecone). Cuando una pregunta **no está cubierta por esos documentos**, el agente lo indica y busca la respuesta en internet (Tavily). No inventa reglas de gobernanza: las afirmaciones sobre políticas deben provenir de los documentos.

## Integrantes del equipo

- Eduardo Ramírez Almanza - A01660118
- Eduardo Xavier Castellanos Montero - A01665358
- Helena Eridani Escandón López - A01659511
- José Antonio Pacheco Chargoy - A01663815
- Jerónimo Gerardo García Landa - A01644050

## Arquitectura general

```
                 Pregunta del usuario
                          │
                          ▼
              Agente (LangChain, LLM en Ollama)
                  │                    │
     ┌────────────┘                    └────────────┐
     ▼                                              ▼
search_governance_knowledge                     web_search
(RAG sobre Pinecone)                          (Tavily, internet)
     ▲
     │ embeddings bge-large (Ollama)
     │
9_pinecone_ingestion.py  ◄──  rag_documents/ (PDF, TXT, CSV)
```

- **Ingesta (`9_pinecone_ingestion.py`)**: leer los documentos de `rag_documents/`, dividirlos en chunks, generar embeddings con `bge-large` y almacenarlos en Pinecone.
- **Agente (`10_agentic_rag_pinecone.py`)**: recibir la pregunta y decidir qué herramienta utilizar. Primero se consultan los documentos; si no son relevantes, se busca en la web y se avisa en la respuesta.
- **RAG local (`8_first_rag.py`)**: versión sencilla en memoria, sin Pinecone, para probar los documentos.

## Estructura del repositorio

```
.
├── 8_first_rag.py              # RAG local en memoria (sin Pinecone)
├── 9_pinecone_ingestion.py     # Ingesta de documentos a Pinecone
├── 10_agentic_rag_pinecone.py  # Agente con RAG y búsqueda web
├── common.py                   # Funciones compartidas para cargar documentos
├── requirements.txt            # Dependencias
├── rag_documents/              # Documentos de gobernanza (base de conocimiento)
└── README.md
```

## Archivos de metadata / governance que utiliza

Los documentos se encuentran en `rag_documents/`:

| Archivo | Contenido |
|---|---|
| `The Government Data Quality Framework - GOV.UK.pdf` | Principios, ciclo de vida de los datos y dimensiones de calidad |
| `The Government Data Quality Framework_ guidance - GOV.UK.pdf` | Guía: planes de acción, análisis de causa raíz, metadata, comunicación de calidad y modelos de madurez |
| `onsdataqualitypolicy.pdf` | Política de gestión de calidad de datos del ONS: roles y responsabilidades |

## Requisitos previos

- Python 3.10 o superior
- [Ollama](https://ollama.com) instalado y **abierto**, con los modelos descargados:
  ```bash
  ollama pull bge-large
  ollama pull llama3.1
  ```
- Cuenta de [Pinecone](https://www.pinecone.io) con un índice vacío: dimensión **1024**, métrica **cosine**
- API key de [Tavily](https://app.tavily.com) (búsqueda web, plan gratuito)

## Cómo instalar dependencias

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Mac / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencias principales: `langchain`, `langchain-ollama`, `langchain-pinecone`, `langchain-tavily`, `pypdf` y `python-dotenv`.

### Configurar las variables de entorno

Crear un archivo llamado `.env` en la raíz del proyecto (junto a los scripts) con la siguiente estructura, reemplazando `XXXXXXX` por las API keys propias:

```dotenv
PINECONE_API_KEY=XXXXXXX
INDEX_NAME=rag-governance
TAVILY_API_KEY=XXXXXXX
MIN_SCORE=0.6
```

| Variable | Descripción |
|---|---|
| `PINECONE_API_KEY` | API key de la cuenta de Pinecone |
| `INDEX_NAME` | Nombre del índice de Pinecone (dimensión 1024, métrica cosine). Debe coincidir con el índice creado |
| `TAVILY_API_KEY` | API key de Tavily para la búsqueda web |
| `MIN_SCORE` | Umbral de relevancia (0 a 1). Por debajo de este valor, los documentos se consideran no relevantes y el agente busca en internet |

El archivo `.env` está incluido en `.gitignore`: **no debe subirse al repositorio**.

## Cómo ejecutar la beta

1. Colocar los documentos de gobernanza en `rag_documents/`.
2. Cargar los documentos en Pinecone (la primera vez, o cuando cambien los documentos):
   ```bash
   python 9_pinecone_ingestion.py
   ```
   Con la opción `--reset` se vacía el índice antes de cargar.
3. Ejecutar el agente:
   ```bash
   python 10_agentic_rag_pinecone.py            # preguntas de demostración
   python 10_agentic_rag_pinecone.py "pregunta" # una sola pregunta
   python 10_agentic_rag_pinecone.py -i         # modo interactivo
   ```
4. (Opcional) Probar el RAG local sin Pinecone: `python 8_first_rag.py "pregunta"`

Cada respuesta imprime `TOOLS USED:` para verificar el enrutamiento:
- Pregunta sobre los documentos → `search_governance_knowledge`
- Pregunta fuera de los documentos → `web_search` (con aviso de que no está en los documentos)

## Ejemplos de preguntas que puede responder

Desde los documentos:
- What are the six core data quality dimensions and how is completeness defined?
- According to the ONS policy, who approves substantial changes to the Data Quality Management Policy?
- What responsibilities does the Data Quality Hub have?
- What is a data quality action plan?
- What does "fit for purpose" mean for data quality?

Fuera de los documentos (utiliza búsqueda web):
- Who won the last FIFA World Cup?
- What is the capital of Australia?

## Limitaciones actuales

- Utiliza un modelo local pequeño (`llama3.1`): puede elegir mal la herramienta, omitir la consulta a los documentos o dejar incompletas las respuestas con listas largas (por ejemplo, los cinco principios del framework).
- Los dos PDFs del Government Data Quality Framework tienen contenido casi idéntico, por lo que los fragmentos se repiten entre resultados.
- La decisión de usar la web depende del modelo y no de una regla fija; los casos ambiguos (preguntas del tema que no aparecen en los PDFs) pueden comportarse distinto entre ejecuciones.
- Los resultados de internet no se verifican: provienen de Tavily y deben contrastarse con la fuente.
- Los documentos están en inglés; no hay manejo específico de otros idiomas.
- No tiene interfaz gráfica ni memoria entre preguntas: cada pregunta se responde de forma independiente.
