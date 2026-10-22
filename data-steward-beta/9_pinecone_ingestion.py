"""
9_pinecone_ingestion.py

Build the persistent data-governance knowledge base in Pinecone.

files in rag_documents/ -> Documents -> chunks -> embeddings (bge-large) -> Pinecone

Re-running is safe: chunk IDs are deterministic, so nothing is duplicated.
Use `python 9_pinecone_ingestion.py --reset` to empty the index first (old documents).
Requires the Pinecone index to exist already (dimension 1024, metric cosine).
"""

import hashlib
import os
import sys

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common import DOCS_DIR, load_corpus

load_dotenv()
INDEX_NAME = os.environ["INDEX_NAME"]


def stable_chunk_id(doc: Document) -> str:
    identity = (
        f"{doc.metadata.get('source', '')}|{doc.metadata.get('page', '')}|"
        f"{doc.metadata.get('row', '')}|{doc.page_content}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    print(f"Loading governance documents from: {DOCS_DIR}")
    documents = load_corpus()
    if not documents:
        raise SystemExit("No documents found in rag_documents/ (supported: pdf, txt, md, csv).")
    print(f"Loaded {len(documents)} source documents/pages/rows")

    chunks = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150).split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    store = PineconeVectorStore(index_name=INDEX_NAME, embedding=OllamaEmbeddings(model="bge-large"))

    # `--reset` wipes everything already in the index (e.g. the old student documents)
    # so the agent only retrieves the new data-governance corpus.
    if "--reset" in sys.argv:
        store.delete(delete_all=True)
        print(f"Deleted all existing vectors in index: {INDEX_NAME}")

    store.add_documents(documents=chunks, ids=[stable_chunk_id(c) for c in chunks])
    print(f"Ingested {len(chunks)} chunks into Pinecone index: {INDEX_NAME}")