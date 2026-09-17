# Incident Postmortem Knowledge Graph + RAG

## Project: PostmortemIQ

### Vision
An intelligent system that ingests engineering incident postmortems, extracts causal chains into a knowledge graph, and provides graph-augmented RAG to answer questions about past incidents, predict blast radius, and surface historical patterns.

---

## System Architecture

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
│  1. Document Loader (MD, TXT, HTML, PDF)                    │
│  2. LLM Structured Extractor                                │
│  3. Chunker (semantic chunking with overlap)                │
│  4. Embedding Generator (sentence-transformers)             │
│  5. Graph Builder (entities → nodes, relations → edges)     │
│  6. Persistence (all three stores)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Ingestion Flow
```
Raw Postmortem (.md/.txt/.html)
    │
    ▼
Document Loader (parse + normalize to plain text)
    │
    ├──▶ LLM Structured Extraction ──▶ JSON schema
    │       │
    │       ├──▶ SQLite (metadata + structured fields)
    │       └──▶ Knowledge Graph (services, failure modes, causal edges)
    │
    └──▶ Semantic Chunker
            │
            └──▶ Embedding Model ──▶ ChromaDB (vectors + chunk text)
```

### Query Flow
```
User Query
    │
    ▼
Intent Classifier
    │
    ├── "similarity" → Vector search only
    ├── "blast_radius" → Graph traversal + vector search
    ├── "pattern" → Graph aggregation + vector search
    └── "resolution" → Vector search + structured filter
    │
    ▼
Hybrid Retriever (merge results from both paths)
    │
    ▼
Context Ranker (deduplicate, rank by relevance)
    │
    ▼
LLM Generator (answer + citations to source postmortems)
    │
    ▼
Response with cited sources
```

---

## Knowledge Graph Schema

### Nodes
| Node Type    | Properties                                    |
|-------------|-----------------------------------------------|
| Service     | name, team, tier (critical/standard)          |
| Incident    | id, title, date, severity, duration, source   |
| FailureMode | name, category (latency/crash/data_loss/etc)  |
| RootCause   | name, category (config/capacity/dependency/bug/human) |
| Resolution  | description, type (rollback/fix/scale/config) |

### Edges
| Edge Type           | From         | To           | Properties        |
|--------------------|--------------|--------------|-------------------|
| AFFECTED_BY        | Service      | Incident     | role (primary/secondary) |
| DEPENDS_ON         | Service      | Service      | type (hard/soft)  |
| CAUSED_BY          | Incident     | RootCause    | confidence        |
| EXHIBITED          | Incident     | FailureMode  | —                 |
| RESOLVED_WITH      | Incident     | Resolution   | time_to_resolve   |
| CASCADED_TO        | Service      | Service      | via_incident      |
| SIMILAR_TO         | Incident     | Incident     | similarity_score  |

---

## Tech Stack

| Component             | Technology                          | Why                                    |
|----------------------|-------------------------------------|----------------------------------------|
| LLM (extraction+RAG)| Groq (llama-3.1-8b-instant)        | Free tier, fast inference              |
| Embeddings           | sentence-transformers (all-MiniLM-L6-v2) | Local, free, good quality       |
| Vector Store         | ChromaDB                            | Simple, no server needed, persistent   |
| Knowledge Graph      | NetworkX + JSON persistence         | Lightweight, no Neo4j server needed    |
| Structured Store     | SQLite                              | Zero config, file-based                |
| Web UI               | Streamlit                           | Fast to build, good for demos          |
| Visualization        | Pyvis (graph) + Plotly (charts)     | Interactive, embeds in Streamlit       |
| Document Parsing     | BeautifulSoup + markdown lib        | Handle multiple input formats          |

---

## Extraction Schema (what the LLM extracts from each postmortem)

```json
{
  "incident_id": "auto-generated",
  "title": "string",
  "date": "YYYY-MM-DD or null",
  "severity": "critical | major | minor | unknown",
  "duration": "string (e.g. '4 hours 23 minutes')",
  "summary": "2-3 sentence summary",
  "trigger_event": "what initiated the incident",
  "root_cause": {
    "description": "detailed root cause",
    "category": "config_change | capacity | dependency_failure | bug | human_error | infrastructure | unknown"
  },
  "affected_services": [
    {
      "name": "service name",
      "role": "primary | secondary",
      "impact": "brief description of impact"
    }
  ],
  "failure_chain": [
    "step 1: what happened first",
    "step 2: what cascaded",
    "step 3: final impact"
  ],
  "resolution": {
    "description": "what fixed it",
    "type": "rollback | hotfix | scaling | config_change | failover | manual",
    "time_to_resolve": "string"
  },
  "preventive_actions": ["action 1", "action 2"],
  "services_dependency_hints": [
    {"from": "service A", "to": "service B", "type": "hard | soft"}
  ]
}
```
