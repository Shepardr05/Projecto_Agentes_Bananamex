"""Shared loaders for the governance corpus (PDF, TXT, CSV, MD)."""

import csv
from pathlib import Path

from langchain_core.documents import Document

DOCS_DIR = Path(__file__).parent / "rag_documents"


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
