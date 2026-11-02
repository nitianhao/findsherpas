"""Shared Anthropic Messages API plumbing for every audit phase.

Three jobs:

1. **Per-model parameter compatibility.** Claude 5-series models (opus-5, sonnet-5, fable-5)
   reject ``temperature`` outright::

       400 invalid_request_error — `temperature` is deprecated for this model.

   The 4-series (sonnet-4-6, haiku-4-5, …) still accepts it. Every phase's model is
   env-overridable (see docs/CASE_STUDY_PLAYBOOK.md), so the parameter is decided per model at
   call time, not hardcoded.

   NOTE: on API version ``2026-10-21`` (sent by Anthropic SDK 1.x) ``temperature`` / ``top_p`` /
   ``top_k`` return a 400 on *every* model. The pinned SDK (0.x) still sends ``2023-06-01``, so
   the 4-series keep their low temperatures for now. Before upgrading the SDK, make
   :func:`supports_temperature` return False unconditionally and re-check output consistency.

2. **No silent degradation.** The failure mode this module exists to prevent: an API error, a
   truncated response or an empty text block gets caught by a phase's broad ``except``, the
   phase falls back to a heuristic, and the audit *appears* to succeed with none of the LLM
   work. That is how the first Zalando Phase 1 produced shoe-size filter labels as nav
   categories. :func:`response_text` and :func:`structured_call` therefore *raise*
   :class:`LLMResponseError` on empty, refused or truncated output — callers that still choose
   to fall back must record that they did.

3. **Structured outputs + usage accounting.** :func:`structured_call` asks the API to
   constrain the response to a Pydantic schema (``output_format``), so no phase has to regex
   JSON out of prose, and every call's token usage is accumulated per phase for the run
   manifest (:func:`usage_summary`).
"""

from __future__ import annotations

import logging
import re
import threading
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# claude-<family>-<major>[-<minor>][-<date>]
_MODEL_RE = re.compile(r"claude-(?:[a-z]+)-(\d+)")

# First major version that dropped `temperature`.
_TEMPERATURE_DROPPED_FROM = 5

# Transient API failures (429 / 5xx / connection) are retried by the SDK itself.
_SDK_MAX_RETRIES = 4

T = TypeVar("T", bound=BaseModel)


class LLMResponseError(RuntimeError):
    """The model returned nothing usable: refusal, truncation at max_tokens, or no text."""


def supports_temperature(model: str) -> bool:
    """Whether ``model`` accepts a ``temperature`` parameter.

    Unrecognised model strings return True — that preserves the historical behaviour for
    anything this shim doesn't know about, rather than silently dropping a parameter the
    caller asked for.
    """
    match = _MODEL_RE.search(model or "")
    if not match:
        return True
    return int(match.group(1)) < _TEMPERATURE_DROPPED_FROM


def temperature_kwargs(model: str, value: float) -> dict:
    """Return ``{"temperature": value}`` if ``model`` supports it, else ``{}``.

    Usage at a call site::

        client.messages.create(
            model=_MODEL,
            ...,
            **temperature_kwargs(_MODEL, 0.2),
        )
    """
    return {"temperature": value} if supports_temperature(model) else {}


def _check_stop_reason(response) -> None:
    stop = getattr(response, "stop_reason", None)
    if stop == "max_tokens":
        raise LLMResponseError("response truncated at max_tokens — raise max_tokens for this call")
    if stop == "refusal":
        details = getattr(response, "stop_details", None)
        raise LLMResponseError(f"model refused the request ({getattr(details, 'category', None)})")


def response_text(response) -> str:
    """Return all text content of a Messages API response, joined.

    ``response.content[0].text`` is unsafe: 5-series models may emit a ``ThinkingBlock``
    (no ``.text``) as the first content block. This scans every block that carries text, so it
    behaves identically on 4-series responses and tolerates any non-text block in front.

    Raises :class:`LLMResponseError` when the response was truncated, refused, or carries no
    text at all — an empty string would otherwise surface later as a JSON parse error and a
    silent heuristic fallback.
    """
    _check_stop_reason(response)
    parts = []
    for block in getattr(response, "content", None) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            parts.append(text)
    if not parts:
        raise LLMResponseError("response contained no text block")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Client + usage accounting
# ---------------------------------------------------------------------------

_client = None
_client_lock = threading.Lock()
_usage: dict[tuple[str, str], dict[str, int]] = {}
_usage_lock = threading.Lock()


def get_client():
    """Process-wide Anthropic client with SDK-level retries for transient failures."""
    global _client
    with _client_lock:
        if _client is None:
            import anthropic

            _client = anthropic.Anthropic(max_retries=_SDK_MAX_RETRIES)
        return _client


def record_usage(phase: str, model: str, response) -> None:
    """Accumulate ``response.usage`` under (phase, model). Never raises."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    with _usage_lock:
        bucket = _usage.setdefault((phase, model), {
            "calls": 0, "input_tokens": 0, "output_tokens": 0,
            "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
        })
        bucket["calls"] += 1
        for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            bucket[key] += int(getattr(usage, key, 0) or 0)


def usage_summary() -> list[dict]:
    """Token usage per (phase, model) for the run manifest."""
    with _usage_lock:
        return [{"phase": p, "model": m, **counts} for (p, m), counts in sorted(_usage.items())]


def reset_usage() -> None:
    with _usage_lock:
        _usage.clear()


def cached_system(text: str) -> list[dict]:
    """System prompt as a single cacheable block.

    Put every static rule here and the per-call data in the user turn, so repeated calls in a
    phase (one per query in the judge) read the rules from the prompt cache. Prefixes below the
    model's minimum cacheable length are simply not cached — harmless.
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def structured_call(
    *,
    model: str,
    system: str,
    user: str,
    schema: type[T],
    max_tokens: int,
    phase: str,
    temperature: float | None = None,
    client=None,
) -> T:
    """One Messages call whose output is constrained to ``schema``. Returns the parsed model.

    Raises :class:`LLMResponseError` on refusal, truncation, or output that fails validation;
    API errors propagate as the SDK's typed exceptions (after the SDK's own retries).
    """
    client = client or get_client()
    kwargs = temperature_kwargs(model, temperature) if temperature is not None else {}
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=cached_system(system),
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            **kwargs,
        )
    except ValidationError as e:
        # The SDK validates inside parse(): JSON cut off at max_tokens surfaces here, before
        # stop_reason can be inspected. It is a bad-output failure, not a programming error.
        raise LLMResponseError(f"{phase}: output failed {schema.__name__} validation (likely truncated): {e}") from e
    record_usage(phase, model, response)
    _check_stop_reason(response)
    parsed = getattr(response, "parsed_output", None)
    if parsed is None:
        raise LLMResponseError(f"{phase}: structured output missing or failed {schema.__name__} validation")
    return parsed
