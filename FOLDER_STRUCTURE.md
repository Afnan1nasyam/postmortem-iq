# Folder Structure

```
postmortem-iq/
│
├── CLAUDE.md                    # Instructions for Claude Code
├── ARCHITECTURE.md              # System architecture doc
├── FOLDER_STRUCTURE.md          # This file
├── README.md                    # Project README (built last)
│
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── .gitignore                   # Git ignore rules
├── pyproject.toml               # Project metadata
│
├── data/
│   ├── raw/                     # Raw postmortem files (.md, .txt, .html)
│   │   └── .gitkeep
│   ├── sample/                  # 10-15 sample postmortems for demo
│   │   └── .gitkeep
│   └── processed/               # Extracted JSON outputs
│       └── .gitkeep
│
├── src/
│   ├── __init__.py
│   │
│   ├── config.py                # Central config (paths, model names, thresholds)
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loader.py            # Document loader (MD/TXT/HTML → plain text)
│   │   ├── extractor.py         # LLM-based structured extraction
│   │   ├── chunker.py           # Semantic chunking with overlap
│   │   └── pipeline.py          # Orchestrates full ingestion flow
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── vector_store.py      # ChromaDB wrapper
│   │   ├── graph_store.py       # NetworkX knowledge graph + JSON persistence
│   │   └── sql_store.py         # SQLite for metadata + structured data
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── intent_classifier.py # Classify query type
│   │   ├── vector_retriever.py  # Semantic search on chunks
│   │   ├── graph_retriever.py   # Graph traversal queries
│   │   ├── hybrid_retriever.py  # Merge + rank from both sources
│   │   └── generator.py         # LLM answer generation with citations
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models for all data structures
│   │
│   └── utils/
│       ├── __init__.py
│       ├── llm_client.py        # Groq API wrapper with retry/fallback
│       └── embedding.py         # Sentence-transformer embedding helper
│
├── app/
│   ├── streamlit_app.py         # Main Streamlit entry point
│   ├── pages/
│   │   ├── 1_query.py           # Query interface page
│   │   ├── 2_upload.py          # Upload postmortem page
│   │   ├── 3_graph.py           # Knowledge graph visualization
│   │   └── 4_analytics.py       # Incident analytics dashboard
│   └── components/
│       ├── __init__.py
│       ├── query_card.py        # Result display component
│       └── graph_viz.py         # Pyvis graph rendering helper
│
├── scripts/
│   ├── seed_data.py             # Generate sample postmortems
│   ├── ingest_all.py            # Batch ingest all files in data/raw/
│   ├── reset_stores.py          # Clear all stores for fresh start
│   └── query_cli.py             # Interactive CLI for quick testing
│
├── tests/
│   ├── __init__.py
│   ├── test_extractor.py
│   ├── test_chunker.py
│   ├── test_graph_store.py
│   ├── test_retrieval.py
│   └── conftest.py
│
└── eval/
    ├── EVAL_LOG.md
    ├── eval_extraction.py
    ├── eval_retrieval.py
    └── test_queries.json
```
