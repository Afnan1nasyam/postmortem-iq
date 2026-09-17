# CLAUDE.md — PostmortemIQ

## Project Overview
An incident postmortem knowledge graph + RAG system. Ingests engineering postmortems, extracts causal chains into a knowledge graph, and provides graph-augmented retrieval to answer questions about past incidents.

## Development Constraints
- **Zscaler blocks outbound API calls.** Any code that calls the Groq API (`groq.Groq().chat.completions.create`) will fail at runtime. Do NOT attempt to call the Groq API during development.
- **sentence-transformers model download will also fail** (needs HuggingFace Hub access). Do not run code that triggers model download.
- **Everything else is fine.** You CAN and SHOULD:
  - Run `pip install -r requirements.txt` to install dependencies
  - Run Python scripts, import modules, verify code works
  - Run `pytest` for tests that don't call Groq or download models
  - Run `python scripts/seed_data.py` (offline, writes files)
  - Verify imports, config loading, chunker logic, graph operations, SQLite operations, etc.
  - Run Streamlit locally to check UI renders (it won't be functional for queries but layout can be verified)
- **Mark tests needing Groq API with `@pytest.mark.slow`** — those get skipped during dev and run later on personal laptop.

## IDE
Development happens in **VS Code** with Claude Code extension.

## Tech Stack
- Python 3.11+
- LLM: Groq API (llama-3.1-8b-instant primary, mixtral-8x7b-32768 fallback)
- Embeddings: sentence-transformers (all-MiniLM-L6-v2), runs locally
- Vector Store: ChromaDB (persistent, file-based)
- Knowledge Graph: NetworkX + JSON file persistence
- Structured Store: SQLite
- Web UI: Streamlit (multipage app)
- Visualization: Pyvis (graph) + Plotly (charts)
- Document Parsing: BeautifulSoup + markdown lib

## Key Architecture Decisions
- No Neo4j — use NetworkX with JSON serialization to keep deployment simple
- No OpenAI — use Groq free tier for all LLM calls (extraction + generation)
- Embeddings run locally, no API cost
- ChromaDB in persistent mode (files in data/chroma/)
- SQLite for metadata, not Postgres — single file, zero config

## Coding Standards
- Use Pydantic v2 models for all data schemas
- Type hints on all functions
- Docstrings on all public functions
- Use loguru for logging, not print statements
- All LLM prompts stored as constants in the module that uses them, with version comments
- Error handling: never crash on a single bad postmortem, log and skip
- Import guards: wrap external library imports in try/except where sensible for dev

## File Layout
See FOLDER_STRUCTURE.md for the complete tree.

## Commands — What works NOW (dev machine)
```bash
pip install -r requirements.txt
python scripts/seed_data.py                    # generates sample .md files (no network)
pytest tests/ -v -m "not slow"                 # tests that don't need Groq API
python -c "from src.config import settings; print(settings.PRIMARY_MODEL)"
python -c "from src.storage.graph_store import KnowledgeGraph; g = KnowledgeGraph(); print(g.get_stats())"
streamlit run app/streamlit_app.py             # UI layout check (queries won't work)
```

## Commands — Run LATER on personal laptop (needs Groq API + network)
```bash
cp .env.example .env   # add GROQ_API_KEY
python scripts/ingest_all.py --data-dir data/raw
python scripts/test_e2e.py
pytest tests/ -v                               # full suite including @slow
python eval/eval_extraction.py
python eval/eval_retrieval.py
```

## Important Constants
- Groq free tier: 30 req/min — rate limiting is in llm_client.py
- ChromaDB collection name: "postmortem_chunks"
- Graph persistence file: data/knowledge_graph.json
- SQLite DB file: data/postmortem.db
- All paths should use src/config.py constants, never hardcoded
