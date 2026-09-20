"""Tests for the NetworkX knowledge graph store."""


import pytest

from src.models.schemas import (
    AffectedService,
    IncidentExtraction,
    Resolution,
    RootCause,
    ServiceDependency,
)
from src.storage.graph_store import KnowledgeGraph


@pytest.fixture(autouse=True)
def _patch_graph_path(monkeypatch, tmp_data_dir):
    monkeypatch.setattr("src.config.settings.GRAPH_PATH", tmp_data_dir / "kg.json")


def _make_extraction(incident_id, title, services, rc_category="config_change", deps=None):
    return IncidentExtraction(
        incident_id=incident_id,
        title=title,
        severity="critical",
        summary=f"Test incident: {title}",
        trigger_event="test trigger",
        root_cause=RootCause(description="test", category=rc_category),
        affected_services=[
            AffectedService(name=s, role="primary" if i == 0 else "secondary", impact="test")
            for i, s in enumerate(services)
        ],
        failure_chain=["Step 1: thing broke", "Step 2: cascade"],
        resolution=Resolution(description="fixed it", type="rollback"),
        preventive_actions=["do better"],
        service_dependencies=deps or [],
    )


def test_add_incident(sample_extraction):
    g = KnowledgeGraph()
    g.add_incident(sample_extraction)

    stats = g.get_stats()
    assert stats["total_nodes"] > 0
    assert stats["total_edges"] > 0
    assert "Incident" in stats["node_types"]
    assert "Service" in stats["node_types"]
    assert "RootCause" in stats["node_types"]


def test_blast_radius():
    g = KnowledgeGraph()

    ext1 = _make_extraction(
        "inc-1",
        "Outage 1",
        ["api-gateway", "user-service"],
        deps=[
            ServiceDependency(
                from_service="api-gateway",
                to_service="user-service",
                type="hard",
            )
        ],
    )

    ext2 = _make_extraction(
        "inc-2",
        "Outage 2",
        ["user-service", "notification-service"],
        deps=[
            ServiceDependency(
                from_service="user-service",
                to_service="notification-service",
                type="soft",
            )
        ],
    )

    g.add_incident(ext1)
    g.add_incident(ext2)

    blast = g.get_blast_radius("notification-service")

    assert "user-service" in blast
    assert "api-gateway" in blast


def test_save_load_roundtrip(tmp_data_dir):
    g = KnowledgeGraph()
    ext = _make_extraction("inc-rt", "Roundtrip Test", ["svc-a", "svc-b"])
    g.add_incident(ext)
    g.save()

    g2 = KnowledgeGraph()
    stats1 = g.get_stats()
    stats2 = g2.get_stats()
    assert stats1["total_nodes"] == stats2["total_nodes"]
    assert stats1["total_edges"] == stats2["total_edges"]


def test_duplicate_service():
    g = KnowledgeGraph()
    ext1 = _make_extraction("inc-d1", "Dup 1", ["shared-service"])
    ext2 = _make_extraction("inc-d2", "Dup 2", ["shared-service"])
    g.add_incident(ext1)
    g.add_incident(ext2)

    service_count = g.get_stats()["node_types"].get("Service", 0)
    assert service_count == 1


def test_get_stats():
    g = KnowledgeGraph()
    stats = g.get_stats()
    assert "total_nodes" in stats
    assert "total_edges" in stats
    assert "node_types" in stats
    assert "edge_types" in stats
    assert "top_services" in stats

def test_service_alias_canonicalization():
    g = KnowledgeGraph()

    ext = _make_extraction(
        "inc-redis",
        "Redis Alias Test",
        ["cache-service (redis)"],
    )

    g.add_incident(ext)

    # The raw name should be normalized to the canonical graph identity.
    services = g.get_all_services()
    assert services.count("cache-service") == 1
    assert "cache-service (redis)" not in services

    # All supported aliases should resolve to the same incident.
    assert g.get_incidents_for_service("cache-service") == ["inc-redis"]
    assert g.get_incidents_for_service("redis") == ["inc-redis"]
    assert g.get_incidents_for_service("cache-service (redis)") == ["inc-redis"]
