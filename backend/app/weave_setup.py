"""Weave initialization + trace deep-link helpers.

weave.init() auto-patches the OpenAI client, so every live Inference call is
traced with token cost. We also expose the current trace id so the frontend can
deep-link into the W&B UI as proof.
"""
from __future__ import annotations

import weave

from . import config

_initialized = False
_client = None


def init_weave():
    """Initialize weave once. Safe to call repeatedly."""
    global _initialized, _client
    if _initialized:
        return _client
    try:
        _client = weave.init(config.weave_project_name())
        _initialized = True
        print(f"[weave] initialized project '{config.weave_project_name()}'")
    except Exception as e:  # noqa: BLE001
        # Don't let a Weave auth hiccup kill the demo; tracing degrades gracefully.
        print(f"[weave] init failed ({e}); continuing without tracing")
        _client = None
    return _client


def get_client():
    return _client


def trace_url(trace_id: str | None = None) -> str:
    """Build a deep-link to the Weave traces UI for this project."""
    entity = config.WANDB_ENTITY or "_"
    project = config.WANDB_PROJECT
    base = f"https://wandb.ai/{entity}/{project}/weave/traces"
    if trace_id:
        return f"{base}?peekPath=/{entity}/{project}/trace/{trace_id}"
    return base


def calls_for_trace(trace_id: str):
    """Pull the call tree for a trace id (used for provenance/cost inspection)."""
    if _client is None:
        return []
    try:
        from weave.trace_server.trace_server_interface import CallsFilter

        return list(
            _client.get_calls(
                filter=CallsFilter(trace_ids=[trace_id]), include_costs=True
            )
        )
    except Exception as e:  # noqa: BLE001
        print(f"[weave] get_calls failed: {e}")
        return []
