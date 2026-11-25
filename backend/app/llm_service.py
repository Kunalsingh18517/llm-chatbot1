import time
from typing import Any

import litellm
from litellm import Cache
from .config import LLM_API_KEYS, LLM_MODEL

# LiteLLM's built-in disk cache. The cache is shared across requests handled by this process.
litellm.cache = Cache(type="disk")
litellm.set_verbose = False


class AllProvidersUnavailable(Exception):
    pass


def _simulated_statuses(header_value: str | None) -> dict[str, int]:
    statuses: dict[str, int] = {}
    if not header_value:
        return statuses
    for item in header_value.split(","):
        if "=" not in item:
            continue
        key_id, status_text = item.strip().split("=", 1)
        try:
            status = int(status_text)
        except ValueError:
            continue
        if status in {429, 500, 502, 503}:
            statuses[key_id.strip()] = status
    return statuses


def _is_retryable_provider_error(error: Exception) -> bool:
    status = getattr(error, "status_code", None)
    if status in {429, 500, 502, 503}:
        return True
    message = str(error).lower()
    return any(term in message for term in ("rate limit", "quota", "429", "500", "502", "503", "internal server error"))


async def generate_reply(messages: list[dict[str, str]], simulated_header: str | None) -> dict[str, Any]:
    if len(LLM_API_KEYS) < 2:
        raise RuntimeError("Configure at least two comma-separated LLM_API_KEYS")

    simulated = _simulated_statuses(simulated_header)
    started = time.perf_counter()
    failures = 0

    for index, api_key in enumerate(LLM_API_KEYS, start=1):
        key_id = f"key_{index}"
        if "*" in simulated or key_id in simulated:
            failures += 1
            continue

        try:
            response = await litellm.acompletion(
                model=LLM_MODEL,
                messages=messages,
                api_key=api_key,
                caching=True,
            )
            elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
            hidden = getattr(response, "_hidden_params", {}) or {}
            cache_hit = bool(hidden.get("cache_hit", False))
            usage = getattr(response, "usage", None)
            choices = getattr(response, "choices", [])
            reply = choices[0].message.content if choices else None
            if not isinstance(reply, str) or not reply.strip():
                raise RuntimeError("The model returned an empty response")

            return {
                "reply": reply,
                "metadata": {
                    "resolution_source": "LLM_CACHE" if cache_hit else "LIVE_INFERENCE",
                    "model": LLM_MODEL,
                    "latency_ms": elapsed_ms,
                    "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                    "key_id": None if cache_hit else key_id,
                    "fallback_attempts": 0 if cache_hit else failures,
                },
            }
        except Exception as error:
            if _is_retryable_provider_error(error):
                failures += 1
                continue
            # Provider-specific auth/quota failures should also allow the next configured key.
            failures += 1
            continue

    raise AllProvidersUnavailable("all providers unavailable")
