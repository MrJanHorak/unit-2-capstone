"""Lazy Gemini adapter. Every completed API response is metered before parsing."""
import json
import time

_last_request_at = 0.0


class ModelError(RuntimeError):
    """A response was unavailable, truncated, empty, or malformed."""


class Gemini:
    def __init__(self, settings, ledger):
        self.settings, self.ledger = settings, ledger
        self._client = None

    def generate(self, stage, prompt, *, system, max_tokens=512, schema=None):
        global _last_request_at
        import os
        from google import genai
        from google.genai import types
        if self._client is None:
            from config import load_environment
            load_environment()
            self._client = genai.Client(http_options=types.HttpOptions(timeout=60_000))
        config = {"system_instruction": system, "max_output_tokens": max_tokens, "temperature": 0}
        if schema:
            config.update(response_mime_type="application/json", response_json_schema=schema)
        started = time.monotonic()
        for attempt in range(3):
            try:
                # Free-tier RPM is shared by all agents. Pace requests within this
                # process; limits vary by account, so the interval is configurable.
                interval = float(os.getenv("GEMINI_REQUEST_INTERVAL_SECONDS", "7"))
                time.sleep(max(0, interval - (time.monotonic() - _last_request_at)))
                _last_request_at = time.monotonic()
                response = self._client.models.generate_content(
                    model=self.settings.model, contents=prompt, config=config)
                break
            except Exception as exc:
                # Retry transient provider failures, not invalid credentials/model names.
                code = getattr(exc, "code", None)
                if code not in (429, 500, 502, 503, 504) or attempt == 2:
                    self.ledger.failed(stage, f"{type(exc).__name__} (code {code})")
                    raise ModelError(f"Gemini request failed (code {code}); check key, model and quota.") from exc
                time.sleep(10 * (attempt + 1))
        self.ledger.record(stage, response.usage_metadata, time.monotonic() - started)
        # Rejected or truncated responses still consume tokens, so log them first.
        candidates = response.candidates or []
        finish = str(getattr(candidates[0], "finish_reason", "")) if candidates else ""
        if "MAX_TOKENS" in finish:
            raise ModelError(f"{stage}: output hit its token limit")
        text = (response.text or "").strip()
        if not text:
            raise ModelError(f"{stage}: model returned no text")
        if schema:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise ModelError(f"{stage}: invalid JSON response") from exc
        return text
