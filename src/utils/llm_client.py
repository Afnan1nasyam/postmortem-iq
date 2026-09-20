"""Groq API wrapper with retry, rate limiting, fallback, and structured JSON output."""

import json
import time
from copy import deepcopy
from typing import Any

from loguru import logger
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import settings


def _is_rate_limit_error(exc: BaseException) -> bool:
    try:
        from groq import RateLimitError

        return isinstance(exc, RateLimitError)
    except ImportError:
        return getattr(exc, "status_code", None) == 429


def _prepare_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a Pydantic JSON schema into a Groq strict-compatible schema.

    Strict structured outputs require object properties to be explicitly
    listed in `required` and object schemas to disallow extra properties.
    Pydantic already represents nullable fields using unions such as
    `anyOf: [string, null]`, so those remain valid while becoming required
    properties in the output object.
    """
    result = deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                properties = node["properties"]

                # Groq strict mode expects all object properties to be required.
                node["required"] = list(properties.keys())

                # Prevent fields that are not part of the contract.
                node["additionalProperties"] = False

                for child in properties.values():
                    visit(child)

            # Handle arrays and their item schemas.
            if "items" in node:
                visit(node["items"])

            # Handle unions / nullable fields / anyOf.
            if "anyOf" in node:
                for child in node["anyOf"]:
                    visit(child)

            if "oneOf" in node:
                for child in node["oneOf"]:
                    visit(child)

            if "allOf" in node:
                for child in node["allOf"]:
                    visit(child)

        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(result)

    # Pydantic v2 places nested models/enums here.
    definitions = result.get("$defs", {})
    for definition in definitions.values():
        visit(definition)

    return result


class GroqClient:
    """Wraps the Groq Python SDK with rate limiting, retry, fallback, and structured output."""

    def __init__(self, model_name: str | None = None):
        from groq import Groq

        self.model_name = model_name or settings.PRIMARY_MODEL
        self._client = Groq(api_key=settings.GROQ_API_KEY)
        self._min_interval = 60.0 / settings.GROQ_RPM
        self._last_request_time: float = 0.0

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time

        if elapsed < self._min_interval:
            sleep_for = self._min_interval - elapsed
            logger.debug(
                "Rate-limit throttle: sleeping {:.2f}s",
                sleep_for,
            )
            time.sleep(sleep_for)

        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(settings.GROQ_RETRY_ATTEMPTS),
        reraise=True,
    )
    def _call_api(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self._throttle()

        logger.debug(
            "Calling Groq model={} tokens={} structured={}",
            model,
            max_tokens,
            response_format is not None,
        )

        request_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format is not None:
            request_kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**request_kwargs)

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise ValueError("Groq returned an empty response")

        return content

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate a text completion.

        The same response format is preserved when falling back to the
        secondary model, so structured-output requests remain structured.
        """
        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        try:
            return self._call_api(
                self.model_name,
                messages,
                temperature,
                max_tokens,
                response_format=response_format,
            )

        except Exception as exc:
            fallback = settings.FALLBACK_MODEL

            if self.model_name == fallback:
                raise

            logger.warning(
                "Primary model {} failed ({}), falling back to {}",
                self.model_name,
                exc,
                fallback,
            )

            return self._call_api(
                fallback,
                messages,
                temperature,
                max_tokens,
                response_format=response_format,
            )

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        schema: dict[str, Any] | None = None,
        schema_name: str = "structured_response",
    ) -> dict:
        """
        Generate a JSON response.

        When `schema` is provided, Groq Structured Outputs are used in strict
        JSON-schema mode. The normal json.loads() path remains as a defensive
        fallback for callers that do not provide a schema.
        """
        response_format = None

        if schema is not None:
            strict_schema = _prepare_strict_schema(schema)

            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": strict_schema,
                },
            }

        raw = self.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        try:
            return json.loads(raw)

        except json.JSONDecodeError:
            # With strict structured outputs this should normally never happen.
            # Keep the repair path for backwards compatibility and unexpected
            # provider/client behavior.
            logger.warning(
                "JSON parse failed, attempting repair prompt"
            )

            repair_prompt = (
                "The following text was supposed to be valid JSON but failed "
                "to parse. Return ONLY the corrected valid JSON, with no "
                "markdown or explanation:\n\n"
                + raw
            )

            raw_retry = self.generate(
                repair_prompt,
                temperature=0.0,
                max_tokens=max_tokens,
            )

            return json.loads(raw_retry)
