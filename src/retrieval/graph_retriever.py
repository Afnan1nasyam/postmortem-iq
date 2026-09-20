"""Graph-based retrieval over the knowledge graph."""

from collections import Counter

from loguru import logger

from src.storage.graph_store import KnowledgeGraph


class GraphRetriever:
    """Retrieves structured incident data via knowledge graph traversal."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def retrieve_blast_radius(self, service_name: str) -> dict:
        """Get blast radius for a service with historical incident counts."""
        downstream = self.graph.get_blast_radius(service_name)

        result = {
            "service": service_name,
            "downstream_services": [],
        }

        for svc in downstream:
            incidents = self.graph.get_incidents_for_service(svc)

            result["downstream_services"].append(
                {
                    "name": svc,
                    "historical_incident_count": len(incidents),
                }
            )

        logger.debug(
            "Blast radius for {}: {} downstream services",
            service_name,
            len(downstream),
        )

        return result

    def retrieve_related_incidents(
        self,
        query: str,
        top_services: list[str],
    ) -> list[dict]:
        """Get incidents related to the given services, deduplicated."""
        seen_ids: set[str] = set()
        results: list[dict] = []

        for svc in top_services:
            for incident_id in self.graph.get_incidents_for_service(svc):
                if incident_id in seen_ids:
                    continue

                seen_ids.add(incident_id)

                node = self.graph._graph.nodes.get(incident_id, {})

                results.append(
                    {
                        "incident_id": incident_id,
                        "title": node.get("title", ""),
                        "severity": node.get("severity", ""),
                        "date": node.get("date", ""),
                        "via_service": svc,
                    }
                )

        logger.debug(
            "Related incidents for {}: {} found",
            top_services,
            len(results),
        )

        return results

    def retrieve_patterns(
        self,
        root_cause_category: str | None = None,
    ) -> dict:
        """Aggregate statistics from the graph."""
        g = self.graph._graph

        rc_counts: Counter = Counter()
        severity_counts: Counter = Counter()
        service_incident_counts: Counter = Counter()

        for node, attrs in g.nodes(data=True):
            if attrs.get("type") == "Incident":
                severity_counts[
                    attrs.get("severity", "unknown")
                ] += 1

                for nb in g.successors(node):
                    nb_attrs = g.nodes[nb]

                    if nb_attrs.get("type") == "RootCause":
                        rc_counts[
                            nb_attrs.get("category", "unknown")
                        ] += 1

            elif attrs.get("type") == "Service":
                incidents = self.graph.get_incidents_for_service(
                    attrs.get("name", node)
                )

                if incidents:
                    service_incident_counts[
                        attrs.get("name", node)
                    ] = len(incidents)

        result = {
            "root_cause_distribution": dict(
                rc_counts.most_common()
            ),
            "severity_distribution": dict(
                severity_counts.most_common()
            ),
            "most_affected_services": dict(
                service_incident_counts.most_common(10)
            ),
        }

        if root_cause_category:
            result["filtered_category"] = root_cause_category
            result["filtered_count"] = rc_counts.get(
                root_cause_category,
                0,
            )

        logger.debug(
            "Pattern retrieval: {} root causes, {} severities",
            len(rc_counts),
            len(severity_counts),
        )

        return result

    def extract_service_names(
        self,
        query: str,
        known_services: list[str],
    ) -> list[str]:
        """Find known service names and common aliases mentioned in the query."""
        q = query.lower()
        found: list[str] = []

        # Human-facing aliases mapped to canonical graph service names.
        aliases = {
            "redis": "cache-service",
            "cache": "cache-service",
            "database": "database (postgres)",
            "notification service": "notification-service",
            "notification-service": "notification-service",
            "api gateway": "api-gateway",
            "api-gateway": "api-gateway",
            "payment service": "payment-service",
            "payment-service": "payment-service",
            "checkout service": "checkout-service",
            "checkout-service": "checkout-service",
            "order service": "order-service",
            "order-service": "order-service",
        }

        for alias, canonical in aliases.items():
            if alias in q and canonical in known_services:
                if canonical not in found:
                    found.append(canonical)

        # Preserve direct matching for canonical service names.
        for svc in known_services:
            if svc.lower() in q and svc not in found:
                found.append(svc)

        return found
