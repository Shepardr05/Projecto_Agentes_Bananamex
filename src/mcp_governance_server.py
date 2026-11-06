"""
mcp_governance_server.py

Servidor MCP del RAG de GOBERNANZA (Pinecone). Expone la busqueda semantica sobre
los documentos de rag_documents/ (politicas, marco de calidad, catalogo de datos)
como una tool MCP, independiente de cualquier agente o LLM.

Evolucion del 11_mcp_rag_server.py del proyecto base:
  - filtro de relevancia MIN_SCORE (si nada lo supera responde NOT_IN_DOCUMENTS)
  - devuelve el score y la fuente (archivo, pagina/fila) de cada fragmento
  - modelo de embeddings configurable (EMBEDDING_MODEL)

Transporte stdio: NO usar print() a stdout. Para depurar: print(..., file=sys.stderr).
"""

import os
import sys

from dotenv import load_dotenv
os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")
from fastmcp import FastMCP  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

mcp = FastMCP("Governance RAG")

MIN_SCORE = float(os.getenv("MIN_SCORE", "0"))  # similitud coseno minima (0 = sin filtro)
TOP_K = int(os.getenv("RAG_TOP_K", "8"))

_store = None


def _get_store():
    """Se crea al primer uso: asi `fastmcp list` funciona aunque Pinecone/Ollama no esten listos."""
    global _store
    if _store is None:
        from langchain_pinecone import PineconeVectorStore

        from common import get_embeddings

        _store = PineconeVectorStore(index_name=os.environ["INDEX_NAME"], embedding=get_embeddings())
    return _store


@mcp.tool()
def search_governance_knowledge(query: str) -> str:
    """
    Search the internal data-governance corpus: data-quality framework and policy
    (UK Government Data Quality Framework, ONS policy), the internal quality policy
    (roles, classification, rules DQ-01..DQ-11, remediation, retention) and the data
    catalog (field descriptions, classification, owner, steward, quality rule).

    Use it to GROUND recommendations: definitions of quality dimensions, who owns a
    field, how a data issue must be remediated or escalated, retention, classification.
    It does NOT contain the data itself (use the SQL tools for numbers).

    Args:
        query: what to look for. The GOV.UK / ONS PDFs are in ENGLISH: for questions about
            them write the query in English with the key terms (e.g. "six dimensions of data
            quality completeness uniqueness consistency timeliness validity accuracy").
            The internal policy and the data catalog are in SPANISH: query in Spanish.
    """
    try:
        results = _get_store().similarity_search_with_score(query, k=TOP_K)
    except Exception as exc:
        return f"Error searching the knowledge base: {type(exc).__name__}: {exc}"

    kept = [(d, s) for d, s in results if s >= MIN_SCORE]
    if not kept:
        return (
            "NOT_IN_DOCUMENTS: nothing in the governance documents is relevant to this "
            "question. Say so explicitly; do not invent policies."
        )

    evidence = []
    for doc, score in kept:
        loc = doc.metadata.get("source", "unknown")
        if doc.metadata.get("page") is not None:
            loc += f", page {int(doc.metadata['page'])}"
        if doc.metadata.get("row") is not None:
            loc += f", row {int(doc.metadata['row'])}"
        evidence.append(f"SOURCE: {loc} (score {score:.2f})\n{doc.page_content}")
    return "\n\n---\n\n".join(evidence)


if __name__ == "__main__":
    mcp.run(show_banner=False)  # stdio