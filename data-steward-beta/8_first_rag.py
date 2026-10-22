"""
8_first_rag.py

First RAG: local, in-memory (no Pinecone needed). Good for a quick sanity check
of the documents in rag_documents/ before ingesting them.

documents -> chunks -> embeddings -> vector store -> retrieval -> prompt -> LLM

Usage:
    python 8_first_rag.py "Who owns the student_gpa field?"
"""

import sys

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from common import load_corpus

question = " ".join(sys.argv[1:]) or "Who owns the student_gpa field and how long is it retained?"

documents = load_corpus()
chunks = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150).split_documents(documents)
print(f"Loaded {len(documents)} documents -> {len(chunks)} chunks")

embeddings = OllamaEmbeddings(model="bge-large")
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(chunks)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

prompt = ChatPromptTemplate.from_template("""
You are a Data Steward assistant.
Use only the following retrieved governance context to answer the question.
Do not invent policies, ownership information, definitions, or governance rules.
If the retrieved context does not contain enough information, say that the
information is not available in the governance documents.
Question: {question}
Context:
{context}
Answer:
""")

llm = ChatOllama(model="llama3.1:latest", temperature=0)

retrieved = retriever.invoke(question)
print("\n--- RETRIEVED DOCUMENTS ---")
for i, doc in enumerate(retrieved, start=1):
    print(f"\nDocument {i} | source: {doc.metadata.get('source', 'unknown')}")
    print(doc.page_content)

context = "\n\n".join(d.page_content for d in retrieved)
response = llm.invoke(prompt.invoke({"question": question, "context": context}))
print("\n--- FINAL ANSWER ---")
print(response.content)
