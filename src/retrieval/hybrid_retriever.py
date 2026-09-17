"""Hybrid retrieval combining vector search and graph traversal."""

from loguru import logger

from src.retrieval.graph_retriever import GraphRetriever
from src.retrieval.intent_classifier import classify_intent
from src.retrieval.vector_retriever import VectorRetriever
from src.storage.graph_store import KnowledgeGraph
from src.storage.sql_store import SQLStore
from src.storage.vector_store import VectorStore
from src.utils.embedding import get_embedding_model


class HybridRetriever:
    """Merges vector and graph retrieval based on query intent."""

    def __init__(self):
        vector_store = VectorStore()
        embedding_model = get_embedding_model()
        graph = KnowledgeGraph()

        self.vector_retriever = VectorRetriever(vector_store, embedding_model)
        self.graph_retriever = GraphRetriever(graph)
        self.sql_store = SQLStore()
        self.graph = graph

    def retrieve(self, query: str) -> dict:
        """Run intent-aware hybrid retrieval and return merged context."""
        intent = classify_intent(query)
        logger.info("Query intent: {} for '{}'", intent, query[:80])

        vector_results = self.vector_retriever.retrieve(query)

        known_services = self.graph.get_all_services()
        services_found = self.graph_retriever.extract_service_names(query, known_services)

        graph_results = {}

        if intent.value == "blast_radius" and services_found:
            graph_results = self.graph_retriever.retrieve_blast_radius(services_found[0])

        elif intent.value == "pattern":
            graph_results = self.graph_retriever.retrieve_patterns()

        elif intent.value == "resolution":
            if services_found:
                sql_results = self.sql_store.search_incidents(service=services_found[0])
                graph_results = {"sql_incidents": sql_results}

        elif intent.value == "similarity":
            if services_found:
                graph_results = {
                    "related_incidents": self.graph_retriever.retrieve_related_incidents(
                        query, services_found
                    )
                }

        seen_incidents: set[str] = set()
        context_parts: list[str] = []

        for vr in vector_results:
            iid = vr["metadata"].get("incident_id", "")
            seen_incidents.add(iid)
            context_parts.append(vr["text"])

        if isinstance(graph_results, dict):
            if "related_incidents" in graph_results:
                for inc in graph_results["related_incidents"]:
                    if inc["incident_id"] not in seen_incidents:
                        seen_incidents.add(inc["incident_id"])
                        context_parts.append(
                            f"[Graph] Incident: {inc['title']} "
                            f"(severity={inc['severity']}, date={inc['date']})"
                        )
            if "downstream_services" in graph_results:
                svc_list = ", ".join(
                    f"{s['name']} ({s['historical_incident_count']} past incidents)"
                    for s in graph_results["downstream_services"]
                )
                context_parts.append(f"[Graph] Blast radius: {svc_list}")
            if "root_cause_distribution" in graph_results:
                rc_str = ", ".join(
                    f"{k}: {v}" for k, v in graph_results["root_cause_distribution"].items()
                )
                context_parts.append(f"[Graph] Root cause patterns: {rc_str}")

        merged_context_string = "\n\n---\n\n".join(context_parts)

        logger.info("Hybrid retrieval: {} vector results, {} services found, intent={}",
                     len(vector_results), len(services_found), intent)

        return {
            "intent": intent,
            "vector_results": vector_results,
            "graph_results": graph_results,
            "merged_context_string": merged_context_string,
            "services_found": services_found,
        }
