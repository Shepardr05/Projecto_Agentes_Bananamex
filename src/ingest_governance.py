"""
ingest_governance.py

Construye la base de conocimiento de gobernanza en Pinecone:
  rag_documents/ -> Documents -> chunks -> embeddings (Ollama) -> Pinecone

- Crea el indice en Pinecone automaticamente si no existe (serverless, dimension 1024, cosine).
- Re-ejecutar es seguro: los IDs de los chunks son deterministas (no se duplica nada).
- `--reset` vacia el indice antes de ingestar (usalo si cambiaste de modelo de embeddings).

Uso (desde la raiz):  python src/ingest_governance.py --reset
"""

import hashlib
import os
import sys

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common import DOCS_DIR, ROOT, get_embeddings, load_corpus

load_dotenv(ROOT / ".env")
DIMENSION = 1024  # bge-m3 y bge-large


def stable_chunk_id(doc: Document) -> str:
    identity = (
        f"{doc.metadata.get('source', '')}|{doc.metadata.get('page', '')}|"
        f"{doc.metadata.get('row', '')}|{doc.page_content}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def ensure_index(index_name: str) -> None:
    """Crea el indice en Pinecone si no existe; si existe, valida la dimension."""
    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    if not pc.has_index(index_name):
        print(f"Creando indice Pinecone '{index_name}' (dim={DIMENSION}, cosine) ...", flush=True)
        pc.create_index(
            name=index_name,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=os.getenv("PINECONE_CLOUD", "aws"), region=os.getenv("PINECONE_REGION", "us-east-1")),
        )
    dim = pc.describe_index(index_name).dimension
    if dim != DIMENSION:
        raise SystemExit(
            f"El indice '{index_name}' tiene dimension {dim}, pero se necesita {DIMENSION}. "
            f"Usa otro INDEX_NAME en .env (se creara solo) o borra ese indice en Pinecone."
        )


def main(argv: list[str]) -> None:
    index_name = os.environ["INDEX_NAME"]
    ensure_index(index_name)

    print(f"Cargando documentos de: {DOCS_DIR}")
    documents = load_corpus()
    if not documents:
        raise SystemExit("No hay documentos en rag_documents/ (soportados: pdf, txt, md, csv).")
    print(f"{len(documents)} paginas/filas/documentos cargados")

    chunks = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150).split_documents(documents)
    print(f"{len(chunks)} chunks. Generando embeddings (puede tardar unos minutos) ...", flush=True)

    store = PineconeVectorStore(index_name=index_name, embedding=get_embeddings())
    if "--reset" in argv:
        try:
            store.delete(delete_all=True)
            print(f"Indice '{index_name}' vaciado")
        except Exception as exc:  # indice nuevo/vacio: Pinecone puede responder 404 al vaciar
            print(f"(indice ya vacio: {type(exc).__name__})")

    store.add_documents(documents=chunks, ids=[stable_chunk_id(c) for c in chunks])
    print(f"Listo: {len(chunks)} chunks ingestados en Pinecone ('{index_name}')")


if __name__ == "__main__":
    main(sys.argv[1:])
