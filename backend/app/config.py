"""Central configuration: env loading, model routing, budgets.

Everything tunable lives here so the rest of the code reads cleanly.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (one level up from app/).
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = REPO_DIR / "data"

load_dotenv(BACKEND_DIR / ".env")

WANDB_API_KEY = os.getenv("WANDB_API_KEY", "").strip()
WANDB_ENTITY = os.getenv("WANDB_ENTITY", "").strip()
WANDB_PROJECT = os.getenv("WANDB_PROJECT", "consultiq-tribunal").strip()
WB_INFERENCE_BASE_URL = os.getenv(
    "WB_INFERENCE_BASE_URL", "https://api.inference.wandb.ai/v1"
).strip()

# Mock mode: explicit flag wins; otherwise mock when there is no API key.
_explicit_mock = os.getenv("USE_MOCK_INFERENCE", "").strip()
if _explicit_mock in ("1", "true", "True"):
    USE_MOCK_INFERENCE = True
elif _explicit_mock in ("0", "false", "False"):
    USE_MOCK_INFERENCE = False
else:
    USE_MOCK_INFERENCE = not bool(WANDB_API_KEY)

ENGAGEMENT_TOKEN_BUDGET = int(os.getenv("ENGAGEMENT_TOKEN_BUDGET", "200000"))
INFERENCE_CONCURRENCY = int(os.getenv("INFERENCE_CONCURRENCY", "4"))

# When naive, the Intake agent under-extracts hard constraints — this is what
# makes the trap fire and gives the Tribunal something real to convict. Set to
# "0" for a diligent intake that captures every constraint.
INTAKE_NAIVE = os.getenv("INTAKE_NAIVE", "1").strip() in ("1", "true", "True")

# The weave project string used by weave.init() and for trace deep-links.
def weave_project_name() -> str:
    if WANDB_ENTITY:
        return f"{WANDB_ENTITY}/{WANDB_PROJECT}"
    return WANDB_PROJECT


# ---- Model routing (§3 of the kickoff doc) ----
# agent role -> W&B Inference model id. The doc's model IDs were stale; these
# are validated against the live W&B Inference catalog, keeping the same intent
# (capable instruction model for intake/synthesis, structured/numerical model
# for ROI, a heavy *thinking* model for conviction, a cheap judge, etc.).
MODELS = {
    "intake": "meta-llama/Llama-3.3-70B-Instruct",          # adaptive questioning
    "vendor": "google/gemma-4-31B-it",                      # reads vendor sheets/tables
    "roi": "deepseek-ai/DeepSeek-V3.1",                     # numerical / structured
    "prioritizer": "meta-llama/Llama-3.1-8B-Instruct",      # cheap, fast
    "synthesis": "meta-llama/Llama-3.3-70B-Instruct",       # long-form, conflict resolution
    "judge": "microsoft/Phi-4-mini-instruct",               # cheap judging at volume
    "conviction": "Qwen/Qwen3-235B-A22B-Thinking-2507",     # heavy reasoner (fires on violation)
    "repair": "deepseek-ai/DeepSeek-V3.1",                  # targeted regeneration
}

# Approximate USD price per 1M tokens (blended) for the live cost meter.
# Hackathon-grade estimates; the token meter is the source of truth.
MODEL_PRICE_PER_MTOK = {
    "meta-llama/Llama-3.3-70B-Instruct": 0.90,
    "google/gemma-4-31B-it": 0.50,
    "deepseek-ai/DeepSeek-V3.1": 1.20,
    "meta-llama/Llama-3.1-8B-Instruct": 0.20,
    "microsoft/Phi-4-mini-instruct": 0.15,
    "Qwen/Qwen3-235B-A22B-Thinking-2507": 3.50,
}
DEFAULT_PRICE_PER_MTOK = 1.00


def usd_for(model: str, total_tokens: int) -> float:
    price = MODEL_PRICE_PER_MTOK.get(model, DEFAULT_PRICE_PER_MTOK)
    return round(price * total_tokens / 1_000_000, 6)


# ---- Pipeline stage ordering (for earliest-stage attribution) ----
# Lower index = earlier stage = preferred culprit when a fix at that stage
# clears the violation.
STAGE_ORDER = ["intake", "vendor", "roi", "prioritizer", "synthesis"]

AGENT_TO_STAGE = {
    "intake": "Intake",
    "vendor": "Vendor / Compliance",
    "roi": "ROI / Cost",
    "prioritizer": "Use-case Prioritizer",
    "synthesis": "Synthesis",
}

SOFT_DIMS = ["relevance", "risk"]
HARD_DIMS = ["compliance", "internal_consistency", "cost"]
