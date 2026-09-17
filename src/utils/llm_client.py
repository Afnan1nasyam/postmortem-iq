"""Groq API wrapper with retry, rate limiting, and fallback."""

import json
import time

from loguru import logger
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import settings


def _is_rate_limit_error(exc: BaseException) -> bool:
    try:
        from groq import RateLimitError
        return isinstance(exc, RateLimitError)
    except ImportError:
        return getattr(exc, "status_code", None) == 429


class GroqClient:
    """Wraps the Groq Python SDK with rate limiting, retry, and model fallback."""

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
            logger.debug("Rate-limit throttle: sleeping {:.2f}s", sleep_for)
            time.sleep(sleep_for)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(settings.GROQ_RETRY_ATTEMPTS),
        reraise=True,
    )
    def _call_api(self, model: str, messages: list[dict], temperature: float, max_tokens: int) -> str:
        self._throttle()
        logger.debug("Calling Groq model={} tokens={}", model, max_tokens)
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a text completion, falling back to the secondary model on failure."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            return self._call_api(self.model_name, messages, temperature, max_tokens)
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
            return self._call_api(fallback, messages, temperature, max_tokens)

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
    ) -> dict:
        """Generate and parse a JSON response, retrying once with a repair prompt on parse failure."""
        raw = self.generate(prompt, system_prompt=system_prompt, temperature=temperature)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed, attempting repair prompt")
            repair_prompt = (
                "The following text was supposed to be valid JSON but failed to parse. "
                "Return ONLY the corrected valid JSON, no explanation:\n\n" + raw
            )
            raw_retry = self.generate(repair_prompt, temperature=0.0)
            return json.loads(raw_retry)
