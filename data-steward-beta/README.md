# Data Steward Beta (RAG + web-search fallback)

Agent that answers data-governance questions from your documents (Pinecone RAG) and,
when a question is NOT covered by them, says so and searches the web (Tavily).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill GOOGLE_API_KEY, PINECONE_API_KEY, TAVILY_API_KEY, INDEX_NAME
ollama pull bge-large && ollama pull llama3.1   # embeddings (+ LLM for script 8)
```
Create a Pinecone index with **dimension 1024**, metric **cosine** (bge-large), named as `INDEX_NAME`.

## Run
1. Put documents in `rag_documents/`.
2. (Optional) local check without Pinecone: `python 8_first_rag.py "your question"`
3. Ingest: `python 9_pinecone_ingestion.py`
4. Agent: `python 10_agentic_rag_pinecone.py` (demo), `... "question"`, or `... -i` (interactive)

Each answer prints `TOOLS USED:` so you can verify: governance questions -> `search_governance_knowledge`;
off-topic questions -> `search_governance_knowledge, web_search`.
