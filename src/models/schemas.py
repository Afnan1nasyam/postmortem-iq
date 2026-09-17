"""Pydantic v2 models for all PostmortemIQ data structures."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PostmortemDocument(BaseModel):
    """Raw document ingested from disk before any processing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    file_path: str
    file_type: Literal["md", "txt", "html"]
    raw_text: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AffectedService(BaseModel):
    """A service impacted by an incident."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    role: Literal["primary", "secondary"]
    impact: str


class RootCause(BaseModel):
    """Root cause extracted from a postmortem."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str
    category: Literal[
        "config_change",
        "capacity",
        "dependency_failure",
        "bug",
        "human_error",
        "infrastructure",
        "unknown",
    ]


class Resolution(BaseModel):
    """How an incident was resolved."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str
    type: Literal["rollback", "hotfix", "scaling", "config_change", "failover", "manual"]
    time_to_resolve: str | None = None


class ServiceDependency(BaseModel):
    """A dependency link between two services."""

    model_config = ConfigDict(str_strip_whitespace=True)

    from_service: str
    to_service: str
    type: Literal["hard", "soft"]


class IncidentExtraction(BaseModel):
    """Full structured extraction from a single postmortem."""

    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    date: str | None = None
    severity: Literal["critical", "major", "minor", "unknown"]
    duration: str | None = None
    summary: str
    trigger_event: str
    root_cause: RootCause
    affected_services: list[AffectedService]
    failure_chain: list[str]
    resolution: Resolution
    preventive_actions: list[str]
    service_dependencies: list[ServiceDependency] = Field(default_factory=list)


class ChunkMetadata(BaseModel):
    """Metadata attached to each vector-store chunk."""

    incident_id: str
    chunk_index: int
    source_file: str


class QueryResult(BaseModel):
    """Response returned to the user after RAG retrieval + generation."""

    answer: str
    sources: list[dict]
    graph_context: str | None = None


class QueryIntent(StrEnum):
    """Classification of user query intent."""

    SIMILARITY = "similarity"
    BLAST_RADIUS = "blast_radius"
    PATTERN = "pattern"
    RESOLUTION = "resolution"
