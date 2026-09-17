# PostmortemIQ

**Turn forgotten postmortems into searchable, graph-connected institutional knowledge.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## The Problem

Every engineering team writes postmortems. Almost nobody reads them again — until the same incident happens six months later and someone says, "didn't we fix this already?"

Postmortems are rich documents: they capture causal chains, service dependencies, resolution patterns, and hard-won operational knowledge. But they live in Google Docs, Confluence pages, or markdown files where they're effectively invisible. Search is keyword-based, there's no cross-referencing, and there's no way to ask "which services cascade when Redis goes down?" without reading every document manually.

PostmortemIQ solves this by treating postmortems as structured data. It extracts causal chains and service relationships into a knowledge graph, embeds the full text for semantic search, and provides a graph-augmented RAG system that can answer complex questions — with citations back to the original incidents.

---

## Key Features

- **Structured LLM Extraction** — Automatically extracts root cause categories, failure chains, affected services, resolution types, and service dependencies from free-text postmortems
- **Knowledge Graph** — Builds a directed graph of services, incidents, root causes, and causal relationships that grows with every ingested document
- **Hybrid Retrieval** — Combines vector similarity search (ChromaDB) with graph traversal (NetworkX) for richer, more connected results
- **Graph-Augmented RAG** — Generates answers that leverage both semantic context and structural graph data, with citations to source incidents
- **Interactive Visualization** — Explore the knowledge graph in-browser with color-coded nodes and filterable views
- **Analytics Dashboard** — Severity distributions, root cause trends, most-affected services, and resolution patterns at a glance

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                         │
│              Streamlit Web App (port 8501)                   │
│   [Query Box] [Upload Postmortem] [Dashboard] [Graph View]  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     QUERY ENGINE                            │
│                                                             │
│  1. Intent Classifier (query type detection)                │
│  2. Hybrid Retriever                                        │
│     ├── Vector Search (ChromaDB)                            │
│     └── Graph Traversal (NetworkX)                          │
│  3. Context Merger & Ranker                                 │
│  4. LLM Answer Generator (with citations)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────────┐
│  Vector Store │ │ Knowledge    │ │ Structured Store  │
│  (ChromaDB)   │ │ Graph        │ │ (SQLite)          │
│               │ │ (NetworkX +  │ │                   │
│ - postmortem  │ │  JSON persist│ │ - incident meta   │
│   chunks      │ │              │ │ - extractions     │
│ - embeddings  │ │ - services   │ │ - query logs      │
│               │ │ - failures   │ │ - analytics       │
│               │ │ - causality  │ │                   │
└───────────────┘ └──────────────┘ └──────────────────┘
              ▲            ▲            ▲
              └────────────┼────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                   INGESTION PIPELINE                        │
│                                                             │
│  1. Document Loader (MD, TXT, HTML)                         │
│  2. LLM Structured Extractor                                │
│  3. Chunker (semantic chunking with overlap)                │
│  4. Embedding Generator (sentence-transformers)             │
│  5. Graph Builder (entities → nodes, relations → edges)     │
│  6. Persistence (all three stores)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| LLM (extraction + RAG) | Groq (llama-3.1-8b-instant) | Free tier, fast inference |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local, free, good quality |
| Vector Store | ChromaDB | Persistent, no server needed |
| Knowledge Graph | NetworkX + JSON | Lightweight, no Neo4j server |
| Structured Store | SQLite | Zero config, file-based |
| Web UI | Streamlit | Fast to build, good for demos |
| Visualization | Pyvis (graph) + Plotly (charts) | Interactive, embeds in Streamlit |

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com/keys) (free tier works)

### Setup

```bash
# Clone
git clone https://github.com/your-username/postmortem-iq.git
cd postmortem-iq

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Generate sample postmortems (no API needed)
python scripts/seed_data.py

# Ingest into all stores (needs Groq API)
python scripts/ingest_all.py --data-dir data/sample

# Launch the web UI
streamlit run app/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) to explore.

---

## Usage

### Example Queries

| Query | What It Does |
|---|---|
| *"What happens if payment-service goes down?"* | Traverses the knowledge graph to find downstream services, historical incidents, and blast radius |
| *"What is our most common root cause category?"* | Aggregates root cause data across all incidents to surface patterns |
| *"How did we fix the database connection pool exhaustion?"* | Finds the specific incident, extracts resolution steps, and cites the source postmortem |
| *"Have we seen Redis memory issues before?"* | Semantic search across all postmortem chunks, returns similar past incidents with context |

### CLI Testing

```bash
python scripts/query_cli.py
```

### Reset Stores

```bash
python scripts/reset_stores.py --all --force
```

---

## How It Works

### Ingestion Flow

1. **Load** — Read markdown, text, or HTML files; strip frontmatter; normalize whitespace
2. **Extract** — LLM extracts structured data: title, severity, root cause, affected services, failure chain, resolution, and service dependencies
3. **Store** — Extraction saved to SQLite; entities and relationships added to the knowledge graph; document chunked with sentence-level splitting and overlap
4. **Embed** — Chunks embedded locally with sentence-transformers, stored in ChromaDB

### Query Flow

1. **Classify** — Heuristic intent classifier determines query type: similarity, blast radius, pattern, or resolution
2. **Retrieve** — Hybrid retriever runs vector search (always) plus intent-specific graph traversal
3. **Merge** — Results deduplicated by incident, graph insights appended to semantic context
4. **Generate** — LLM produces a cited answer grounded in the merged context

---

## Evaluation

PostmortemIQ includes a structured evaluation framework for iterating on prompt quality:

- **`eval/test_queries.json`** — 15 test queries across 3 difficulty levels (easy, medium, hard) with expected intents, services, and keywords
- **`eval/eval_extraction.py`** — Scores extraction completeness: root cause category, affected services, failure chain, service dependencies
- **`eval/eval_retrieval.py`** — Scores retrieval accuracy: intent classification, service detection, keyword presence in answers
- **`eval/EVAL_LOG.md`** — Tracks prompt versions, changes, and results across iterations

```bash
# Run extraction eval (needs ingested data)
python eval/eval_extraction.py

# Run retrieval eval (needs Groq API)
python eval/eval_retrieval.py
```

The prompt iteration workflow: change a prompt constant → re-run eval → compare scores → log results in EVAL_LOG.md. Extraction and generation prompts are versioned as module-level constants for traceability.

---

## Project Structure

```
postmortem-iq/
├── src/
│   ├── config.py                 # Central config (pydantic-settings)
│   ├── ingestion/
│   │   ├── loader.py             # Document loader (MD/TXT/HTML)
│   │   ├── extractor.py          # LLM structured extraction
│   │   ├── chunker.py            # Semantic chunking with overlap
│   │   └── pipeline.py           # End-to-end ingestion orchestrator
│   ├── storage/
│   │   ├── vector_store.py       # ChromaDB wrapper
│   │   ├── graph_store.py        # NetworkX knowledge graph
│   │   └── sql_store.py          # SQLite for metadata + analytics
│   ├── retrieval/
│   │   ├── intent_classifier.py  # Query type detection
│   │   ├── vector_retriever.py   # Semantic search
│   │   ├── graph_retriever.py    # Graph traversal queries
│   │   ├── hybrid_retriever.py   # Merged retrieval
│   │   └── generator.py          # LLM answer generation
│   └── models/
│       └── schemas.py            # Pydantic v2 data models
├── app/
│   ├── streamlit_app.py          # Main Streamlit entry
│   └── pages/                    # Query, Upload, Graph, Analytics
├── scripts/                      # seed, ingest, reset, query CLI
├── tests/                        # pytest suite (offline + @slow)
└── eval/                         # Evaluation framework
```

---

## Future Enhancements

- **Slack Integration** — Ingest postmortems directly from Slack channels; notify teams when similar incidents are detected
- **Real-Time Alert Matching** — Connect to PagerDuty/OpsGenie webhooks and automatically surface relevant past incidents during active pages
- **Neo4j Backend** — Swap NetworkX for Neo4j when graph size warrants a dedicated graph database
- **Multi-Tenant Support** — Team-scoped graphs and access controls for enterprise deployment
- **Embedding Fine-Tuning** — Fine-tune the embedding model on SRE/incident vocabulary for better retrieval relevance
- **Automated Trend Reports** — Weekly digests highlighting emerging patterns and repeat failure modes

---

## License

MIT
