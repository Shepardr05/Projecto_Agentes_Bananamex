"""Shared loaders for the governance corpus (PDF, TXT, CSV, MD) + model factories."""

import csv
import os
import sys
from pathlib import Path

from langchain_core.documents import Document

def fix_console() -> None:
    """Windows/PowerShell: evita errores de acentos y caracteres especiales al imprimir."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


fix_console()

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "rag_documents"


def get_embeddings():
    """Embeddings locales con Ollama. El modelo es configurable por .env.

    OJO: la dimension del indice de Pinecone debe coincidir con el modelo
    (bge-m3 y bge-large = 1024). Si cambias de modelo, re-ingesta con --reset.
    """
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=os.getenv("EMBEDDING_MODEL", "bge-m3"))


def get_llm():
    """LLM del agente, elegido por LLM_PROVIDER = ollama | google | anthropic."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model = os.getenv("LLM_MODEL", "")
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model or "llama3.1:latest", temperature=0)
    if provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise SystemExit("Falta el paquete: pip install langchain-google-genai")

        return ChatGoogleGenerativeAI(model=model or "gemini-2.5-flash", temperature=0)
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise SystemExit("Falta el paquete: pip install langchain-anthropic")

        return ChatAnthropic(model=model or "claude-sonnet-4-5", temperature=0)
    raise SystemExit(f"LLM_PROVIDER no soportado: {provider} (usa ollama, google o anthropic)")


def load_pdf(path: Path) -> list[Document]:
    from pypdf import PdfReader

    docs = []
    for page_number, page in enumerate(PdfReader(path).pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(Document(
                page_content=text,
                metadata={"source": path.name, "document_type": "pdf", "page": page_number},
            ))
    return docs


def load_text(path: Path) -> list[Document]:
    return [Document(
        page_content=path.read_text(encoding="utf-8"),
        metadata={"source": path.name, "document_type": "text"},
    )]


def load_csv(path: Path) -> list[Document]:
    docs = []
    with path.open(newline="", encoding="utf-8") as f:
        for row_number, row in enumerate(csv.DictReader(f), start=2):
            content = "\n".join(f"{k}: {v}" for k, v in row.items())
            docs.append(Document(
                page_content=content,
                metadata={
                    "source": path.name,
                    "document_type": "data_catalog",
                    "row": row_number,
                    "field_name": row.get("field_name", ""),
                },
            ))
    return docs


def load_corpus(folder: Path = DOCS_DIR) -> list[Document]:
    """Load every supported file in the folder. README.md is skipped (it's project docs)."""
    docs = []
    for path in sorted(folder.iterdir()):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            docs.extend(load_pdf(path))
        elif suffix in (".txt", ".md") and path.name.lower() != "readme.md":
            docs.extend(load_text(path))
        elif suffix == ".csv":
            docs.extend(load_csv(path))
    return docs
