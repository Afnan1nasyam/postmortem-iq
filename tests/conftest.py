"""Shared pytest fixtures for PostmortemIQ tests."""

import pytest

from src.models.schemas import (
    AffectedService,
    IncidentExtraction,
    Resolution,
    RootCause,
    ServiceDependency,
)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests that need Groq API (deselect with '-m not slow')")


@pytest.fixture
def sample_postmortem_text():
    return (
        "# Redis Cluster Outage — Session Data Loss\n\n"
        "**Date:** 2024-06-10\n"
        "**Severity:** Critical\n"
        "**Duration:** 1 hour 45 minutes\n\n"
        "## Summary\n\n"
        "On June 10, 2024, the primary Redis cluster experienced a complete outage "
        "due to a misconfigured maxmemory-policy directive. The cache-service stopped "
        "serving requests, which caused the checkout-service to lose all active session "
        "data. Approximately 8,000 users were forced to restart their checkout flows. "
        "The api-gateway experienced elevated error rates as every cache miss fell through "
        "to the database, overwhelming the connection pool.\n\n"
        "## Timeline\n\n"
        "- 14:00 UTC — Routine config deployment applied to Redis cluster.\n"
        "- 14:05 UTC — maxmemory-policy changed from allkeys-lru to noeviction.\n"
        "- 14:12 UTC — Redis memory hits limit. New writes rejected with OOM errors.\n"
        "- 14:15 UTC — cache-service health checks fail. checkout-service sessions lost.\n"
        "- 14:20 UTC — monitoring-service pages on-call engineer.\n"
        "- 14:30 UTC — Root cause identified as config change.\n"
        "- 14:35 UTC — Config rolled back to allkeys-lru.\n"
        "- 15:00 UTC — Cache warm-up initiated. Sessions gradually restored.\n"
        "- 15:45 UTC — Full recovery confirmed.\n\n"
        "## Root Cause\n\n"
        "A configuration deployment changed the Redis maxmemory-policy from allkeys-lru "
        "to noeviction. Under noeviction, once memory is full Redis rejects all write "
        "commands. The change was intended for a staging environment but was applied "
        "to production due to an environment variable mismatch in the deployment script.\n\n"
        "## Impact\n\n"
        "- 8,000 active checkout sessions lost.\n"
        "- api-gateway error rate spiked to 35% for 30 minutes.\n"
        "- database connection pool saturated from cache miss stampede.\n"
        "- Estimated revenue impact: $95,000.\n\n"
        "## Resolution\n\n"
        "The Redis configuration was rolled back to allkeys-lru. A cache warm-up script "
        "repopulated hot keys. The deployment script was patched to require explicit "
        "environment confirmation before applying config changes.\n\n"
        "## Action Items\n\n"
        "1. Add environment guard to all config deployment scripts.\n"
        "2. Implement Redis config diff review before apply.\n"
        "3. Add circuit breaker in checkout-service for cache failures.\n"
    )


@pytest.fixture
def sample_extraction():
    return IncidentExtraction(
        incident_id="test-incident-001",
        title="Redis Cluster Outage — Session Data Loss",
        date="2024-06-10",
        severity="critical",
        duration="1 hour 45 minutes",
        summary="Redis config change caused cache outage, losing 8,000 checkout sessions.",
        trigger_event="Config deployment changed maxmemory-policy to noeviction",
        root_cause=RootCause(
            description="maxmemory-policy changed to noeviction on production Redis",
            category="config_change",
        ),
        affected_services=[
            AffectedService(name="cache-service", role="primary", impact="Complete outage"),
            AffectedService(name="checkout-service", role="primary", impact="Session data lost"),
            AffectedService(name="api-gateway", role="secondary", impact="Elevated error rates"),
        ],
        failure_chain=[
            "Step 1: Config deployment changed maxmemory-policy to noeviction",
            "Step 2: Redis memory filled, new writes rejected with OOM",
            "Step 3: cache-service health checks failed",
            "Step 4: checkout-service lost session data, api-gateway connection pool saturated",
        ],
        resolution=Resolution(
            description="Rolled back Redis config to allkeys-lru",
            type="rollback",
            time_to_resolve="1 hour 45 minutes",
        ),
        preventive_actions=[
            "Add environment guard to config deployment scripts",
            "Implement Redis config diff review",
            "Add circuit breaker in checkout-service",
        ],
        service_dependencies=[
            ServiceDependency(from_service="checkout-service", to_service="cache-service", type="hard"),
            ServiceDependency(from_service="api-gateway", to_service="cache-service", type="soft"),
        ],
    )


@pytest.fixture
def tmp_data_dir(tmp_path):
    (tmp_path / "chroma").mkdir()
    return tmp_path
