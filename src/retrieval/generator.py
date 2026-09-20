"""LLM answer generation with citations from retrieved context."""

from loguru import logger

from src.models.schemas import QueryResult
from src.storage.sql_store import SQLStore
from src.utils.llm_client import GroqClient

# GENERATION_PROMPT_V1
GENERATION_SYSTEM_PROMPT = """\
You are an SRE knowledge assistant for the PostmortemIQ system.

Answer questions using ONLY the incident evidence supplied in the context.

STRICT GROUNDING RULES:
- Never invent an incident, incident title, date, service, root cause, metric, or event.
- Treat Incident ID as the identity of an incident.
- Multiple chunks with the same Incident ID are parts of ONE incident, not multiple incidents.
- A root-cause event, batch job, deployment, timeline event, service, or component mentioned inside an incident is NOT a separate historical incident.
- When asked whether something happened before, count only distinct Incident IDs represented in the retrieved context.
- When referencing an incident, use only the title/date explicitly present in the supplied evidence.
- Never create a second incident merely because the same root cause or workload is described more than once.
- If the context supports only one incident, say that only one incident is confirmed by the retrieved evidence.
- If the context does not contain enough evidence, explicitly say that the retrieved evidence is insufficient.
- Do not rely on outside knowledge.
- Do not infer that an affected service is a single point of failure unless the evidence explicitly establishes that its failure alone caused or could cause the observed impact.
- Do not treat "primary affected service" as equivalent to "single point of failure."
- Do not infer service dependency relationships merely because multiple services were affected by the same incident.
- For pattern questions, distinguish between affected service, dependency, causal service, and single point of failure.
- For prioritization questions, distinguish observed frequency from operational priority.
- A more frequent root cause is not automatically a higher operational priority unless the evidence provides additional support such as severity, blast radius, recurrence, or explicit remediation priority.
- For questions asking for "single points of failure", identify a service as a single point of failure only when the supplied evidence explicitly establishes that classification or clearly states that the service's failure alone caused the relevant outage.
- Do not infer "single point of failure" from "primary service", "affected service", "dependency", "cascade", "resource exhaustion", or large blast radius.
- If no service is explicitly established as a single point of failure, state that the retrieved evidence does not explicitly identify any single point of failure.
- For prioritization questions, distinguish "most frequent" from "highest priority".
- If the evidence only provides frequency, report the most frequent pattern and state that frequency alone does not establish operational priority.
- Do not present an operational priority ranking unless the evidence explicitly provides a priority, severity, blast-radius, recurrence, or comparable basis for ranking.

ANSWERING RULES:
- Cite incidents by their exact title when that title is available in the context.
- For blast-radius questions, list affected services supported by the evidence.
- For pattern questions, describe only patterns supported by distinct incident records in the context.
- For resolution questions, describe only actions present in the evidence.
- Be concise and actionable.
- When evidence does not establish a requested characterization, explicitly say that the evidence does not establish it rather than inferring it.
- Prefer "the incidents show..." or "the evidence identifies..." over stronger causal or operational claims when the evidence is limited.
"""


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
        )

        if intent == "pattern" and any(
            term in query.lower()
            for term in ("prioritize", "priority", "priorities")
        ):
            user_prompt += (
                "SPECIAL PRIORITIZATION CONSTRAINT:\n"
                "- Do not make an operational recommendation unless the supplied "
                "evidence explicitly establishes a priority.\n"
                "- Do not convert frequency into priority.\n"
                "- You may report which root-cause category is most frequent.\n"
                "- State clearly that frequency alone does not establish what should "
                "be prioritized operationally.\n"
                "- Do not use phrases such as 'prioritize first', 'highest priority', "
                "'most effective', or 'will reduce incidents' unless the evidence "
                "explicitly supports that claim.\n\n"
            )

        user_prompt += (
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

        # Build a concise, intent-aware source list from the retrieved
        # vector evidence instead of exposing every vector result.
        vector_results = context.get("vector_results", [])

        ranked_results = sorted(
            vector_results,
            key=lambda x: x.get("distance", float("inf")),
        )

        source_limits = {
            "resolution": 1,
            "similarity": 3,
            "blast_radius": 3,
            "pattern": 5,
        }

        source_limit = source_limits.get(
            str(intent).lower(),
            3,
        )

        sources = []
        seen = set()

        for vr in ranked_results:
            metadata = vr.get("metadata", {})
            incident_id = metadata.get("incident_id", "")

            if not incident_id or incident_id in seen:
                continue

            seen.add(incident_id)

            sources.append(
                {
                    "incident_id": incident_id,
                    "source_file": metadata.get("source_file", ""),
                    "distance": vr.get("distance"),
                }
            )

            if len(sources) >= source_limit:
                break

        graph_context = None
        graph_results = context.get("graph_results", {})

        if graph_results:
            if "downstream_services" in graph_results:
                names = [
                    service["name"]
                    for service in graph_results["downstream_services"]
                ]
                graph_context = f"Blast radius: {', '.join(names)}"

            elif "root_cause_distribution" in graph_results:
                graph_context = (
                    f"Patterns: "
                    f"{graph_results['root_cause_distribution']}"
                )

            elif "related_incidents" in graph_results:
                titles = [
                    incident["title"]
                    for incident in graph_results["related_incidents"][:5]
                ]
                graph_context = f"Related: {', '.join(titles)}"

        result_count = len(sources)

        self.sql_store.log_query(
            query,
            str(intent),
            result_count,
        )

        logger.info(
            "Generated answer ({} chars, {} sources) for '{}'",
            len(answer_text),
            result_count,
            query[:80],
        )

        return QueryResult(
            answer=answer_text,
            sources=sources,
            graph_context=graph_context,
        )
