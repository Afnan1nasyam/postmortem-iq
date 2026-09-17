"""SQLite store for incident metadata and query logs."""

import json
import sqlite3
from datetime import datetime, timezone

from loguru import logger

from src.config import settings
from src.models.schemas import IncidentExtraction


class SQLStore:
    """SQLite wrapper for structured incident data and query analytics."""

    def __init__(self):
        db_path = str(settings.SQLITE_PATH)
        settings.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info("SQLStore ready at {}", db_path)

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT,
                severity TEXT,
                duration TEXT,
                summary TEXT,
                trigger_event TEXT,
                root_cause_json TEXT,
                affected_services_json TEXT,
                failure_chain_json TEXT,
                resolution_json TEXT,
                preventive_actions_json TEXT,
                service_dependencies_json TEXT,
                source_file TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                intent TEXT,
                result_count INTEGER,
                timestamp TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def save_incident(self, extraction: IncidentExtraction, source_file: str = "") -> None:
        """Insert or replace an incident from an extraction."""
        self._conn.execute(
            """INSERT OR REPLACE INTO incidents
               (id, title, date, severity, duration, summary, trigger_event,
                root_cause_json, affected_services_json, failure_chain_json,
                resolution_json, preventive_actions_json, service_dependencies_json,
                source_file, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                extraction.incident_id,
                extraction.title,
                extraction.date,
                extraction.severity,
                extraction.duration,
                extraction.summary,
                extraction.trigger_event,
                extraction.root_cause.model_dump_json(),
                json.dumps([s.model_dump() for s in extraction.affected_services]),
                json.dumps(extraction.failure_chain),
                extraction.resolution.model_dump_json(),
                json.dumps(extraction.preventive_actions),
                json.dumps([d.model_dump() for d in extraction.service_dependencies]),
                source_file,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()
        logger.debug("Saved incident {} to SQLite", extraction.incident_id)

    def get_incident(self, incident_id: str) -> dict | None:
        """Fetch a single incident by ID."""
        row = self._conn.execute(
            "SELECT * FROM incidents WHERE id = ?", (incident_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_incidents(self) -> list[dict]:
        """Return all stored incidents."""
        rows = self._conn.execute("SELECT * FROM incidents ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def log_query(self, query: str, intent: str, result_count: int) -> None:
        """Log a user query for analytics."""
        self._conn.execute(
            "INSERT INTO query_log (query, intent, result_count, timestamp) VALUES (?, ?, ?, ?)",
            (query, intent, result_count, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def get_query_stats(self) -> dict:
        """Return query analytics: total, by intent, and most common queries."""
        total = self._conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]

        by_intent = {}
        for row in self._conn.execute(
            "SELECT intent, COUNT(*) as cnt FROM query_log GROUP BY intent ORDER BY cnt DESC"
        ).fetchall():
            by_intent[row["intent"]] = row["cnt"]

        top_queries = []
        for row in self._conn.execute(
            "SELECT query, COUNT(*) as cnt FROM query_log GROUP BY query ORDER BY cnt DESC LIMIT 10"
        ).fetchall():
            top_queries.append({"query": row["query"], "count": row["cnt"]})

        return {
            "total_queries": total,
            "by_intent": by_intent,
            "top_queries": top_queries,
        }

    def search_incidents(
        self,
        severity: str | None = None,
        root_cause_category: str | None = None,
        service: str | None = None,
    ) -> list[dict]:
        """Filter incidents by severity, root cause category, or affected service."""
        query = "SELECT * FROM incidents WHERE 1=1"
        params: list = []

        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if root_cause_category:
            query += " AND json_extract(root_cause_json, '$.category') = ?"
            params.append(root_cause_category)
        if service:
            query += " AND affected_services_json LIKE ?"
            params.append(f"%{service}%")

        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def reset(self) -> None:
        """Drop and recreate both tables."""
        self._conn.executescript("""
            DROP TABLE IF EXISTS incidents;
            DROP TABLE IF EXISTS query_log;
        """)
        self._create_tables()
        logger.info("SQLStore reset")
