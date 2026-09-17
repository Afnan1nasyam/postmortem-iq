"""LLM answer generation with citations from retrieved context."""

from loguru import logger

from src.models.schemas import QueryResult
from src.storage.sql_store import SQLStore
from src.utils.llm_client import GroqClient

# GENERATION_PROMPT_V1
GENERATION_SYSTEM_PROMPT = """\
You are an SRE knowledge assistant for the PostmortemIQ system. Your role is to answer \
questions about past incidents using ONLY the provided context from postmortem documents \
and the knowledge graph.

Rules:
- Answer based ONLY on the provided incident context. Do not invent information.
- Cite specific incidents by title when referencing them.
- If the context doesn't contain enough information to answer, say so explicitly.
- Be concise and actionable. Focus on what the engineer needs to know.
- For blast radius questions, list affected services and historical incident counts.
- For pattern questions, highlight trends and recurring themes.
- For resolution questions, describe what was done and what preventive actions were taken.
- Format your answer in clear sections when appropriate."""


class AnswerGenerator:
    """Generates answers from retrieved context using the Groq LLM."""

    def __init__(self):
        self.client = GroqClient()
        self.sql_store = SQLStore()

    def generate(self, query: str, context: dict) -> QueryResult:
        """Generate an answer from the query and retrieved context."""
        intent = context.get("intent", "similarity")
        merged = context.get("merged_context_string", "")
        services = context.get("services_found", [])

        user_prompt = (
            f"Query type: {intent}\n"
            f"Services mentioned: {', '.join(services) if services else 'none'}\n\n"
            f"User question: {query}\n\n"
            f"Context from postmortem database:\n{merged}"
        )

        try:
            answer_text = self.client.generate(
                prompt=user_prompt,
                system_prompt=GENERATION_SYSTEM_PROMPT,
            )
        except Exception as exc:
            logger.error("Generation failed: {}", exc)
            answer_text = (
                "I was unable to generate an answer due to an error. "
                "Please check the system logs or try again."
            )

        sources = []
        seen = set()
        for vr in context.get("vector_results", []):
            iid = vr.get("metadata", {}).get("incident_id", "")
            if iid and iid not in seen:
                seen.add(iid)
                sources.append({
                    "incident_id": iid,
                    "source_file": vr.get("metadata", {}).get("source_file", ""),
                    "distance": vr.get("distance"),
                })

        graph_context = None
        graph_results = context.get("graph_results", {})
        if graph_results:
            if "downstream_services" in graph_results:
                names = [s["name"] for s in graph_results["downstream_services"]]
                graph_context = f"Blast radius: {', '.join(names)}"
            elif "root_cause_distribution" in graph_results:
                graph_context = f"Patterns: {graph_results['root_cause_distribution']}"
            elif "related_incidents" in graph_results:
                titles = [i["title"] for i in graph_results["related_incidents"][:5]]
                graph_context = f"Related: {', '.join(titles)}"

        result_count = len(sources)
        self.sql_store.log_query(query, str(intent), result_count)

        logger.info("Generated answer ({} chars, {} sources) for '{}'",
                     len(answer_text), result_count, query[:80])

        return QueryResult(
            answer=answer_text,
            sources=sources,
            graph_context=graph_context,
        )
