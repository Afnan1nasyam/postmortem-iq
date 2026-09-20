# PostmortemIQ

**Turn forgotten postmortems into searchable, graph-connected institutional knowledge.**

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## The Problem

Every engineering team writes postmortems. Almost nobody reads them again — until the same incident happens six months later and someone asks, "didn't we fix this already?"

Postmortems are rich documents: they capture causal chains, service dependencies, resolution patterns, and hard-won operational knowledge. But they often live in documents or markdown files where they're difficult to search and connect across incidents.

PostmortemIQ treats postmortems as structured operational knowledge. It extracts causal chains and service relationships into a knowledge graph, embeds the full text for semantic search, and uses graph-augmented retrieval to answer questions across historical incidents.

---

## Key Features

* **Structured LLM Extraction** — Extracts root cause categories, failure chains, affected services, resolution details, and service dependencies from free-text postmortems.

* **Knowledge Graph** — Builds a directed graph of incidents, services, root causes, failure modes, and resolutions using NetworkX with JSON persistence.

* **Hybrid Retrieval** — Combines vector similarity search with intent-specific graph traversal.

* **Grounded RAG** — Generates answers from retrieved postmortem evidence and graph context while applying grounding constraints to reduce unsupported claims.

* **Service Canonicalization** — Normalizes equivalent service names such as `redis`, `cache`, and `cache-service (redis)` to a shared graph identity.

* **Analytics and Graph Exploration** — Provides the foundation for incident analytics and knowledge-graph exploration through the application layer.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                      │
│                 Streamlit Web Application                  │
│                                                             │
│       Query        Upload        Analytics        Graph     │
└──────────────────────────────┬────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        QUERY ENGINE                         │
│                                                             │
│  1. Intent Classifier                                       │
│  2. Hybrid Retriever                                        │
│       ├── Vector Retrieval                                  │
│       └── Graph Retrieval                                   │
│  3. Context Merger / Deduplication                          │
│  4. Grounded Answer Generator                               │
└──────────────────────────────┬────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
       ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
       │ Vector Store │ │ Knowledge    │ │ SQLite       │
       │ ChromaDB     │ │ Graph        │ │              │
       │              │ │ NetworkX     │ │ Incident     │
       │ Postmortem   │ │ + JSON       │ │ metadata     │
       │ chunks       │ │ persistence  │ │ + extracted  │
       │ embeddings   │ │              │ │ data         │
       └──────────────┘ └──────────────┘ └──────────────┘
                ▲              ▲              ▲
                └──────────────┼──────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                       │
│                                                             │
│  1. Document Loader                                         │
│  2. Structured LLM Extraction                               │
│  3. Sentence-boundary Chunking + Character Overlap         │
│  4. Local Embedding Generation                              │
│  5. Knowledge Graph Construction                            │
│  6. Persistence to all stores                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component        | Technology                               | Purpose                                                       |
| ---------------- | ---------------------------------------- | ------------------------------------------------------------- |
| LLM              | Groq — `openai/gpt-oss-20b`              | Primary extraction and answer generation                      |
| LLM Fallback     | Groq — `openai/gpt-oss-120b`             | Fallback when the primary model fails or is rate-limited      |
| Embeddings       | `sentence-transformers/all-MiniLM-L6-v2` | Local semantic embeddings                                     |
| Vector Store     | ChromaDB                                 | Persistent vector retrieval                                   |
| Knowledge Graph  | NetworkX + JSON                          | Service relationships, incidents, dependencies, and traversal |
| Structured Store | SQLite                                   | Incident metadata and extracted records                       |
| Web UI           | Streamlit                                | Interactive application                                       |
| Visualization    | Pyvis + Plotly                           | Graph and analytical visualization                            |
| Data Models      | Pydantic v2                              | Structured schemas and validation                             |

---

## Quick Start

### Prerequisites

* Python 3.11+
* A Groq API key

### Setup

```bash
# Clone
git clone https://github.com/Afnan1nasyam/postmortem-iq.git
cd postmortem-iq

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env

# Edit .env and add your GROQ_API_KEY

# Generate sample postmortems
python scripts/seed_data.py

# Ingest sample data into all stores
python scripts/ingest_all.py --data-dir data/sample

# Launch the web UI
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## Usage

### Example Queries

| Query                                                         | Purpose                                                                                           |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **"What happens if payment-service goes down?"**              | Uses dependency traversal to identify downstream services and historical blast-radius information |
| **"What is our most common root cause category?"**            | Aggregates root-cause categories across incidents                                                 |
| **"How did we fix the database connection pool exhaustion?"** | Retrieves the relevant incident and its recorded remediation                                      |
| **"Have we seen Redis memory issues before?"**                | Uses semantic retrieval and service-aware graph context to find related incidents                 |

### CLI Querying

```bash
python scripts/query_cli.py
```

### Resetting Stores

```bash
python scripts/reset_stores.py --all --force
```

---

## How It Works

### Ingestion Flow

1. **Load** — Read supported document formats and normalize the source text.

2. **Extract** — Use structured LLM output to extract incident metadata, root cause, affected services, failure chain, resolution, preventive actions, and service dependencies.

3. **Store** — Save the structured extraction to SQLite and create incident, service, root-cause, failure-mode, and resolution relationships in the knowledge graph.

4. **Chunk** — Split documents on sentence boundaries while preserving character-level overlap between adjacent chunks. Chunk size and overlap are configurable through application settings.

5. **Embed** — Generate local embeddings for each chunk and store them in ChromaDB.

### Query Flow

1. **Classify** — Determine the query intent: `similarity`, `blast_radius`, `pattern`, or `resolution`.

2. **Retrieve** — Run vector retrieval together with intent-specific graph retrieval where applicable.

3. **Merge** — Combine and deduplicate evidence, grouping chunks belonging to the same incident.

4. **Generate** — Produce a grounded answer from the supplied evidence and graph context.

---

## Evaluation

PostmortemIQ includes separate evaluation scripts for extraction and retrieval.

### Extraction Evaluation

`eval/eval_extraction.py` evaluates extraction completeness across the sample incidents, including fields such as:

* root cause category
* affected services
* failure chain
* service dependencies

The current sample evaluation covers **12 postmortems**.

### Retrieval Evaluation

`eval/eval_retrieval.py` evaluates:

* intent classification
* expected service detection
* expected keyword presence in generated answers

The current retrieval benchmark contains **15 queries** across easy, medium, and hard difficulty levels.

### Current Validation Results

On the current 12-incident sample dataset:

```text
Extraction evaluation:   100.0%
Retrieval evaluation:    28/28 (100.0%)
E2E smoke test:          5/5 passed
```

The end-to-end test resets the persistent stores before ingestion and verifies that the sample dataset is not duplicated between runs.

### Run Evaluations

```bash
# Extraction evaluation
python eval/eval_extraction.py

# Retrieval evaluation
python eval/eval_retrieval.py

# End-to-end smoke test
python scripts/test_e2e.py
```

---

## Project Structure

```text
postmortem-iq/
│
├── src/
│   ├── config.py
│   ├── ingestion/
│   │   ├── loader.py
│   │   ├── extractor.py
│   │   ├── chunker.py
│   │   └── pipeline.py
│   │
│   ├── storage/
│   │   ├── vector_store.py
│   │   ├── graph_store.py
│   │   └── sql_store.py
│   │
│   ├── retrieval/
│   │   ├── intent_classifier.py
│   │   ├── vector_retriever.py
│   │   ├── graph_retriever.py
│   │   ├── hybrid_retriever.py
│   │   └── generator.py
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   └── utils/
│       ├── llm_client.py
│       ├── embedding.py
│       └── logging utilities
│
├── app/
│   ├── streamlit_app.py
│   └── pages/
│
├── scripts/
│   ├── seed_data.py
│   ├── ingest_all.py
│   ├── reset_stores.py
│   ├── query_cli.py
│   └── test_e2e.py
│
├── tests/
├── eval/
├── data/
│   ├── sample/
│   └── raw/
│
├── ARCHITECTURE.md
├── FOLDER_STRUCTURE.md
├── CLAUDE.md
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Design Notes

### Grounded Answers

The answer generator is explicitly instructed to stay within retrieved evidence. It is also designed to avoid treating every dependency, affected service, or frequently occurring category as an unsupported recommendation or conclusion.

### Graph Direction

Service dependency edges use the convention:

```text
dependent service → dependency
```

For example:

```text
checkout-service → payment-service
```

This allows blast-radius traversal to move through predecessor services to identify components that depend on a failed service.

### Service Identity

Service names are normalized before being stored in the graph. This prevents equivalent names such as:

```text
redis
cache
cache-service (redis)
```

from becoming separate graph entities.

---

## Future Enhancements

* Slack integration for automated postmortem ingestion
* PagerDuty / Opsgenie integration for active incident matching
* Neo4j backend for substantially larger knowledge graphs
* Multi-tenant team-scoped graphs and access controls
* Domain-specific embedding improvements
* Automated trend and recurring-incident reports
* Stronger semantic evaluation using structured ground truth rather than keyword-only checks

---

## License

MIT
