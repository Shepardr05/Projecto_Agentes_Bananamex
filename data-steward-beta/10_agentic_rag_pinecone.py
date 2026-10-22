"""
10_agentic_rag_pinecone.py

Data Steward agent with TWO tools:

  1. search_governance_knowledge -> RAG over the Pinecone governance knowledge base
  2. web_search                  -> Tavily web search, ONLY as a fallback when the
                                    question is not covered by the governance documents

The agent decides which tool to call. For every question the script prints which
tools were actually used, so you can verify the routing.

Usage:
    python 10_agentic_rag_pinecone.py                  # runs the demo questions
    python 10_agentic_rag_pinecone.py "your question"  # single question
    python 10_agentic_rag_pinecone.py -i               # interactive chat
"""

import os
import sys

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_tavily import TavilySearch

load_dotenv()

INDEX_NAME = os.environ["INDEX_NAME"]
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
# MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

vector_store = PineconeVectorStore(
    index_name=INDEX_NAME,
    embedding=OllamaEmbeddings(model="bge-large"),
)
MIN_SCORE = float(os.getenv("MIN_SCORE", "0"))  # 0 = no filter
tavily = TavilySearch(max_results=5)


@tool
def search_governance_knowledge(query: str) -> str:
    """Search the internal data-governance documents: policies, definitions, data
    classification, ownership, approved uses, retention, privacy and AI-use rules.
    ALWAYS try this tool first."""
    print(f"\n[TOOL CALL] search_governance_knowledge(query={query!r})")
    results = vector_store.similarity_search_with_score(query, k=8)
    # Optional relevance filter (set MIN_SCORE in .env after looking at the printed scores)
    docs = [(d, sc) for d, sc in results if sc >= MIN_SCORE]
    for d, sc in results:
        print(f"    score={sc:.3f}  {d.metadata.get('source', '?')}")
    if not docs:
        return (
            "NOT_IN_DOCUMENTS: nothing in the governance documents is relevant to this "
            "question. You MUST now call the web_search tool with the user's question. "
            "Begin your final answer with: 'This is not covered in the governance "
            "documents I have access to, so I searched the internet.'"
        )

    evidence = []
    for doc, _score in docs:
        loc = doc.metadata.get("source", "unknown")
        if doc.metadata.get("page") is not None:
            loc += f", page {doc.metadata['page']}"
        if doc.metadata.get("row") is not None:
            loc += f", row {doc.metadata['row']}"
        evidence.append(f"SOURCE: {loc}\n{doc.page_content}")
    return "\n\n---\n\n".join(evidence)


@tool
def web_search(query: str) -> str:
    """Search the public internet. Use ONLY when the question is NOT answered by the
    governance documents (e.g. general knowledge, sports, news, current events) or
    when search_governance_knowledge returned nothing relevant."""
    print(f"\n[TOOL CALL] web_search(query={query!r})  <- question not covered by the governance documents")
    results = tavily.invoke({"query": query})
    items = results.get("results", []) if isinstance(results, dict) else results
    if not items:
        return "The web search returned no results."
    return "\n\n---\n\n".join(
        f"SOURCE: {r.get('url', 'unknown')}\nTITLE: {r.get('title', '')}\n{r.get('content', '')}"
        for r in items
    )


SYSTEM_PROMPT = """
You are a Data Steward assistant. You have two tools:

1. search_governance_knowledge: the data-governance knowledge base: the UK Government
   Data Quality Framework (principles, data lifecycle, the six quality dimensions,
   action plans, root cause analysis, metadata, communicating quality, maturity models)
   and the ONS Data Quality Management Policy (policy statements, roles and
   responsibilities, Integrated Data Service).
2. web_search: the public internet.

Procedure for EVERY question:
1. First call search_governance_knowledge.
2. If the retrieved evidence answers the question, answer using ONLY that evidence
   and cite the source filename. Do not invent permissions, owners, or rules.
   If the evidence is insufficient or does not authorize the proposed use, say so.
3. If the question is NOT related to the governance documents, or the retrieved
   evidence is irrelevant to it (e.g. "who won the World Cup?"), do this:
   - Start your answer by saying clearly: "This is not covered in the governance
     documents I have access to, so I searched the internet."
   - Call web_search and answer from those results, citing the URLs.
   - Never present web information as an internal governance rule.
4. If the question IS about data governance / data quality but the documents do not
   contain the specific detail, say it is not in the documents. You may then offer
   to search the web, but never present web information as part of the documents.
5. Only say you searched the internet if you actually called web_search.
   Never answer general-knowledge questions from memory and never invent URLs.
6. When listing items (principles, dimensions, roles), list ONLY what appears in
   the retrieved evidence. If the evidence does not show the complete list, say
   that the list is incomplete. Never fill gaps from memory.
"""

# agent = create_agent(
#    model=ChatGoogleGenerativeAI(model=MODEL, temperature=0),
#    tools=[search_governance_knowledge, web_search],
#    system_prompt=SYSTEM_PROMPT,
# )

agent = create_agent(
    model=ChatOllama(model=MODEL, temperature=0),
    tools=[search_governance_knowledge, web_search],
    system_prompt=SYSTEM_PROMPT,
)

def final_text(message) -> str:
    if isinstance(message.content, str):
        return message.content
    return "".join(
        b.get("text", "") for b in message.content if isinstance(b, dict) and b.get("type") == "text"
    )


def ask(question: str) -> None:
    print("\n" + "=" * 80)
    print("QUESTION:", question)
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})

    used = [tc["name"] for m in result["messages"] for tc in getattr(m, "tool_calls", None) or []]
    print("TOOLS USED:", ", ".join(used) if used else "(none)")
    print("\nANSWER:")
    print(final_text(result["messages"][-1]))


DEMO_QUESTIONS = [
    # Answerable from the documents -> search_governance_knowledge only
    "What are the six core data quality dimensions and how is completeness defined?",
    "According to the ONS policy, who approves substantial changes to the Data Quality Management Policy?",
    "What are the five data quality principles in the Government Data Quality Framework?",
    # Not in the documents -> search_governance_knowledge, then web_search
    "Who won the last FIFA World Cup?",
    "What is the capital of Australia?",
]

if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["-i"]:
        while (q := input("\nQuestion (empty to exit): ").strip()):
            ask(q)
    elif args:
        ask(" ".join(args))
    else:
        for q in DEMO_QUESTIONS:
            ask(q)