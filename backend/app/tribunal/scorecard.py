"""SOFT scorecard — provenance-weighted, LLM-judged (Phi-4-mini).

This is the OTHER credit-assignment mode, kept strictly separate from
conviction. We NEVER try to "convict" an agent of a soft dimension. Instead we
score each agent's own claims on each soft dimension and build an
agent x dimension matrix from trace provenance (claim.origin_agent).
"""
from __future__ import annotations

import weave

from .. import config
from ..cost_governor import CostMeter
from ..data_loader import risks_for_client
from ..inference import call_model, parse_json_safe
from ..schemas import CellScore, ProposalObject, RequirementsObject, Scorecard

# deterministic mock scores so the heatmap is meaningful offline
_MOCK = {
    "intake":      {"relevance": 0.90, "risk": 0.70},
    "vendor":      {"relevance": 0.86, "risk": 0.58},
    "roi":         {"relevance": 0.82, "risk": 0.55},
    "prioritizer": {"relevance": 0.84, "risk": 0.62},
    "synthesis":   {"relevance": 0.88, "risk": 0.52},
}

_DIM_GUIDANCE = {
    "relevance": (
        "How directly do these claims address the client's stated needs and "
        "context? 1.0 = perfectly on-point, 0.0 = irrelevant."
    ),
    "risk": (
        "How well do these claims surface and mitigate the risks that matter for "
        "this scenario? 1.0 = thorough risk awareness, 0.0 = ignores key risks."
    ),
}


@weave.op()
async def judge_score(
    agent: str, dimension: str, claims_text: str, context: str, meter: CostMeter
) -> CellScore:
    mock = {
        "score": _MOCK.get(agent, {}).get(dimension, 0.7),
        "rationale": (
            f"{config.AGENT_TO_STAGE.get(agent, agent)} scored on {dimension}: "
            f"claims are largely on-target for this dimension."
        ),
    }
    messages = [
        {"role": "system", "content": (
            "You are a strict consulting reviewer. Score ONE agent's claims on "
            f"ONE dimension. {_DIM_GUIDANCE.get(dimension, '')} "
            "Return ONLY JSON {score: float 0..1, rationale: string}."
        )},
        {"role": "user", "content": (
            f"Dimension: {dimension}\nContext: {context}\n"
            f"Agent's claims:\n{claims_text}"
        )},
    ]
    raw = await call_model("judge", messages, meter, agent="judge",
                           json_mode=True, temperature=0.2, max_tokens=300,
                           mock_response=mock)
    data = parse_json_safe(raw, mock)
    try:
        score = float(data.get("score", mock["score"]))
    except (TypeError, ValueError):
        score = mock["score"]
    return CellScore(score=max(0.0, min(1.0, score)), rationale=data.get("rationale", ""))


@weave.op()
async def build_scorecard(
    proposal: ProposalObject, req: RequirementsObject, client: dict, meter: CostMeter
) -> Scorecard:
    # group claims by originating agent (provenance)
    by_agent: dict[str, list[str]] = {}
    for c in proposal.claims:
        by_agent.setdefault(c.origin_agent, []).append(f"- {c.text}")

    risk_ref = "; ".join(risks_for_client(client["id"])[:6])
    context_base = (
        f"Client: {req.client_name} ({req.industry}). Needs: {', '.join(req.needs)}."
    )

    matrix: dict[str, dict[str, CellScore]] = {}
    for agent, lines in by_agent.items():
        claims_text = "\n".join(lines)
        matrix[agent] = {}
        for dim in config.SOFT_DIMS:
            ctx = context_base
            if dim == "risk":
                ctx += f" Known risks to consider: {risk_ref}."
            matrix[agent][dim] = await judge_score(agent, dim, claims_text, ctx, meter)

    return Scorecard(
        matrix=matrix,
        dimensions=list(config.SOFT_DIMS),
        agents=list(matrix.keys()),
    )
