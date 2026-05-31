"""W&B Inference client (OpenAI-compatible).

ONE global asyncio.Semaphore gates every call (the 429 cap). Exponential
backoff on 429/503. Token usage is recorded into the per-engagement CostMeter.
When USE_MOCK_INFERENCE is on, a deterministic mock is returned instead so the
whole pipeline runs offline.
"""
from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Optional

from . import config
from .cost_governor import CostMeter

# ONE semaphore shared across all engagements (§5).
_semaphore = asyncio.Semaphore(config.INFERENCE_CONCURRENCY)

_client = None  # lazy AsyncOpenAI


def _get_client():
    global _client
    if _client is None:
        from openai import AsyncOpenAI

        headers = {}
        if config.weave_project_name():
            # W&B Inference associates usage with this project.
            headers["OpenAI-Project"] = config.weave_project_name()
        _client = AsyncOpenAI(
            base_url=config.WB_INFERENCE_BASE_URL,
            api_key=config.WANDB_API_KEY or "missing",
            default_headers=headers or None,
            max_retries=0,  # we do our own backoff
        )
    return _client


def _estimate_tokens(text: str) -> int:
    # ~4 chars/token rough estimate, used only in mock mode.
    return max(1, len(text) // 4)


async def call_model(
    role: str,
    messages: list[dict[str, str]],
    meter: CostMeter,
    *,
    agent: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 1200,
    mock_response: Any = None,
) -> str:
    """Call the model routed for `role`. Returns the text content.

    `agent` labels the cost bucket (defaults to role). `mock_response`, when
    provided, is what the deterministic mock returns (a dict/list is JSON-encoded);
    it is ignored in live mode.
    """
    model = config.MODELS[role]
    agent = agent or role

    # Hard budget gate before spending more tokens.
    meter.check()

    if config.USE_MOCK_INFERENCE:
        return await _mock_call(model, messages, meter, agent, mock_response)

    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_err: Optional[Exception] = None
    for attempt in range(6):
        try:
            async with _semaphore:
                resp = await client.chat.completions.create(**kwargs)
            usage = getattr(resp, "usage", None)
            total = int(getattr(usage, "total_tokens", 0) or 0)
            meter.record(agent, model, total)
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001 - normalize SDK error variants
            status = getattr(e, "status_code", None)
            retryable = status in (429, 503, 500, 502) or "rate" in str(e).lower()
            last_err = e
            if not retryable or attempt == 5:
                raise
            backoff = min(20.0, (2 ** attempt) + random.uniform(0, 1))
            await asyncio.sleep(backoff)
    raise last_err  # pragma: no cover


async def _mock_call(
    model: str,
    messages: list[dict[str, str]],
    meter: CostMeter,
    agent: str,
    mock_response: Any,
) -> str:
    # Simulate latency + concurrency so the SSE animation feels real.
    async with _semaphore:
        await asyncio.sleep(random.uniform(0.25, 0.7))
    if mock_response is None:
        content = "[mock] no canned response provided"
    elif isinstance(mock_response, str):
        content = mock_response
    else:
        content = json.dumps(mock_response)
    prompt_text = " ".join(m.get("content", "") for m in messages)
    total = _estimate_tokens(prompt_text) + _estimate_tokens(content)
    meter.record(agent, model, total)
    return content


def parse_json(text: str) -> Any:
    """Best-effort JSON extraction from a model response."""
    text = text.strip()
    if text.startswith("```"):
        # strip markdown fences
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    # find the outermost JSON object/array
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(text)  # raise if truly malformed


def parse_json_safe(text: str, default: Any) -> Any:
    """parse_json but never raises — returns `default` on any failure.

    Lets live agents degrade gracefully to their deterministic result when a
    model returns malformed JSON, instead of crashing the engagement.
    """
    try:
        result = parse_json(text)
        # guard against a model returning a bare string/number
        if default is not None and not isinstance(result, type(default)):
            return default
        return result
    except Exception:  # noqa: BLE001
        return default
