"""LLM-based structured extraction from postmortem documents."""

from loguru import logger
from pydantic import ValidationError

from src.models.schemas import IncidentExtraction, PostmortemDocument
from src.utils.llm_client import GroqClient

# EXTRACTION_PROMPT_V1
EXTRACTION_SYSTEM_PROMPT = """\
You are an expert incident analysis engine. Given an engineering postmortem document, \
extract structured information into the exact JSON schema below.

FIELDS:
- "title": Short descriptive title of the incident.
- "date": Date the incident occurred in "YYYY-MM-DD" format. Use null if not found.
- "severity": One of "critical", "major", "minor", "unknown". Infer from impact scope \
  and duration if not stated explicitly.
- "duration": Human-readable duration string (e.g. "4 hours 23 minutes"). null if unknown.
- "summary": 2-3 sentence summary of what happened, the impact, and how it was resolved.
- "trigger_event": The specific event that initiated the incident (e.g. a deploy, config \
  change, traffic spike).
- "root_cause": Object with:
    - "description": Detailed explanation of the underlying root cause.
    - "category": One of "config_change", "capacity", "dependency_failure", "bug", \
      "human_error", "infrastructure", "unknown".
- "affected_services": List of objects, each with:
    - "name": Service or component name.
    - "role": "primary" (directly failed) or "secondary" (impacted downstream).
    - "impact": Brief description of how this service was affected.
- "failure_chain": Ordered list of strings describing the causal chain step by step, \
  from trigger to final impact. Each step should start with "Step N: ". Extract at least \
  2 steps. This is critical for building the knowledge graph.
- "resolution": Object with:
    - "description": What action resolved the incident.
    - "type": One of "rollback", "hotfix", "scaling", "config_change", "failover", "manual".
    - "time_to_resolve": Duration string or null.
- "preventive_actions": List of follow-up action items mentioned in the postmortem.
- "service_dependencies": List of dependency relationships inferred from the postmortem. \
  Each with:
    - "from_service": The dependent service name.
    - "to_service": The service it depends on.
    - "type": "hard" (will fail without it) or "soft" (degraded but functional).
  Infer dependencies from the failure chain and affected services even if not explicitly \
  stated. For example, if Service A timed out waiting for Service B, that is a hard \
  dependency from A to B.

REQUIRED JSON SCHEMA:
{
  "title": "string",
  "date": "string or null",
  "severity": "critical | major | minor | unknown",
  "duration": "string or null",
  "summary": "string",
  "trigger_event": "string",
  "root_cause": {"description": "string", "category": "string"},
  "affected_services": [{"name": "string", "role": "primary | secondary", "impact": "string"}],
  "failure_chain": ["string"],
  "resolution": {"description": "string", "type": "string", "time_to_resolve": "string or null"},
  "preventive_actions": ["string"],
  "service_dependencies": [{"from_service": "string", "to_service": "string", "type": "hard | soft"}]
}

RULES:
- Use "unknown" or null for any field you cannot determine from the text.
- Do NOT invent information. Only extract what is stated or can be directly inferred.
- Return ONLY valid JSON matching the schema. No markdown, no explanation."""


class PostmortemExtractor:
    """Extracts structured IncidentExtraction data from postmortem documents via LLM."""

    def __init__(self):
        self.client = GroqClient()

    def extract(self, document: PostmortemDocument) -> IncidentExtraction:
        """Extract structured data from a single postmortem document."""
        user_prompt = (
            "Extract structured incident data from the following postmortem:\n\n"
            + document.raw_text
        )

        try:
            data = self.client.generate_json(
                prompt=user_prompt,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
            )
            return IncidentExtraction.model_validate(data)
        except ValidationError as exc:
            logger.warning("Validation failed for {}: {}", document.file_path, exc)
            return self._retry_with_repair(document, user_prompt, exc)
        except Exception as exc:
            logger.error("Extraction failed for {}: {}", document.file_path, exc)
            return self._make_failed_extraction(document)

    def _retry_with_repair(
        self,
        document: PostmortemDocument,
        original_prompt: str,
        error: ValidationError,
    ) -> IncidentExtraction:
        """Attempt one repair pass including the validation error details."""
        repair_prompt = (
            f"{original_prompt}\n\n"
            f"The previous extraction had validation errors:\n{error}\n\n"
            "Please fix the JSON to match the required schema exactly."
        )
        try:
            data = self.client.generate_json(
                prompt=repair_prompt,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
            )
            return IncidentExtraction.model_validate(data)
        except Exception as exc:
            logger.error("Repair extraction also failed for {}: {}", document.file_path, exc)
            return self._make_failed_extraction(document)

    def _make_failed_extraction(self, document: PostmortemDocument) -> IncidentExtraction:
        """Return a minimal placeholder when extraction completely fails."""
        return IncidentExtraction(
            title="EXTRACTION_FAILED",
            severity="unknown",
            summary=f"Extraction failed for {document.file_path}",
            trigger_event="unknown",
            root_cause={"description": "unknown", "category": "unknown"},
            affected_services=[],
            failure_chain=[],
            resolution={"description": "unknown", "type": "manual"},
            preventive_actions=[],
        )

    def extract_batch(
        self, documents: list[PostmortemDocument]
    ) -> list[IncidentExtraction]:
        """Extract from multiple documents, logging progress and never crashing on one failure."""
        total = len(documents)
        results: list[IncidentExtraction] = []

        for i, doc in enumerate(documents, 1):
            logger.info("Extracting {}/{}: {}", i, total, doc.file_path)
            result = self.extract(doc)
            results.append(result)

        logger.info("Batch extraction complete: {}/{} succeeded",
                     sum(1 for r in results if r.title != "EXTRACTION_FAILED"), total)
        return results
