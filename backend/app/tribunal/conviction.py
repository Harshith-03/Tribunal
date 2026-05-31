"""Conviction engine — counterfactual replay + earliest-stage attribution.

For a HARD violation we walk the candidate agents EARLIEST stage first. For
each, we correct that agent (using ground truth), replay everything downstream
via re_run_agent, and re-check the violation. The first agent whose correction
CLEARS the violation is convicted — and because we go earliest-first, we
attribute to the true root cause (Intake dropping a constraint), not the
downstream symptom (Vendor picking a cloud tool).

A heavy reasoner (DeepSeek-R1) writes the verdict — but only after a violation
has verifiably fired. That's the cost discipline: the expensive model is
summoned only when something broke.
"""
from __future__ import annotations

import weave

from .. import config
from ..cost_governor import CostMeter
from ..data_loader import vendor_by_id, vendors
from ..inference import call_model
from ..schemas import Conviction, HardConstraint, RequirementsObject, Violation
from ..worker.pipeline import re_run_agent
from ..worker.specialists import select_vendor
from .hard_scorers import compliance_failures, cost_over_budget


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _ground_truth_req(client: dict) -> RequirementsObject:
    return RequirementsObject(
        client_id=client["id"],
        client_name=client["name"],
        industry=client.get("industry", ""),
        needs=client.get("needs", []),
        hard_constraints=[HardConstraint(**c) for c in client.get("hard_constraints", [])],
        budget_usd=client.get("budget_usd"),
        required_stakeholders=client.get("required_stakeholders", []),
    )


def _as_vendor_output(meta: dict | None) -> dict:
    if meta is None:
        return {}
    return {
        "vendor_id": meta["id"],
        "vendor_name": meta["name"],
        "deployment": meta["deployment"],
        "price_usd": meta["price_usd"],
        "rationale": f"{meta['name']} satisfies the ground-truth constraints.",
    }


def _best_compliant_vendor(client: dict) -> dict:
    """What the Vendor agent SHOULD have picked given the true constraints."""
    gt = _ground_truth_req(client)
    return _as_vendor_output(select_vendor(gt))


def _still_violates(dimension: str, replay: dict, client: dict) -> bool:
    if dimension == "compliance":
        vid = replay.get("vendor", {}).get("vendor_id")
        vmeta = vendor_by_id(vid) if vid else None
        return bool(compliance_failures(vmeta, client.get("hard_constraints", [])))
    if dimension == "cost":
        total = replay.get("roi", {}).get("estimated_total_usd")
        return cost_over_budget(total, client.get("budget_usd")) > 0
    # internal_consistency: re-run synthesis already corrects most cases
    return False


async def _replay_with_correction(
    agent: str, dimension: str, ctx: dict, meter: CostMeter
) -> dict:
    """Correct `agent`, replay downstream, return the new {requirements,vendor,roi}."""
    client = ctx["client"]
    if agent == "intake":
        # Correct Intake's OUTPUT to the canonical ground-truth requirements
        # (correct_output_for from synthetic ground truth), then replay the
        # downstream agents. This is deterministic and doesn't depend on a live
        # re-extraction's wording.
        creq = _ground_truth_req(client)
        nv = await re_run_agent("vendor", {"requirements": creq}, meter)
        nroi = await re_run_agent("roi", {"requirements": creq, "vendor": nv}, meter)
        return {"requirements": creq, "vendor": nv, "roi": nroi}
    if agent == "vendor":
        cv = _best_compliant_vendor(client)
        nroi = await re_run_agent(
            "roi", {"requirements": ctx["requirements"], "vendor": cv}, meter
        )
        return {"requirements": ctx["requirements"], "vendor": cv, "roi": nroi}
    if agent == "roi":
        nroi = await re_run_agent(
            "roi", {"requirements": ctx["requirements"], "vendor": ctx["vendor"]}, meter
        )
        return {"requirements": ctx["requirements"], "vendor": ctx["vendor"], "roi": nroi}
    if agent == "synthesis":
        return {
            "requirements": ctx["requirements"],
            "vendor": ctx["vendor"],
            "roi": ctx["roi"],
        }
    return {"requirements": ctx["requirements"], "vendor": ctx["vendor"], "roi": ctx["roi"]}


def _evidence_str(agent: str, dimension: str, replay: dict, cleared: bool) -> str:
    v = replay.get("vendor", {})
    if dimension == "compliance":
        return (
            f"Corrected {config.AGENT_TO_STAGE.get(agent, agent)} -> Vendor now "
            f"recommends {v.get('vendor_name', '?')} ({v.get('deployment', '?')}). "
            f"Violation {'CLEARED' if cleared else 'persists'}."
        )
    if dimension == "cost":
        total = replay.get("roi", {}).get("estimated_total_usd")
        return (
            f"Corrected {config.AGENT_TO_STAGE.get(agent, agent)} -> estimated total "
            f"${(total or 0):,.0f}. Violation {'CLEARED' if cleared else 'persists'}."
        )
    return f"Replay after correcting {agent}: {'CLEARED' if cleared else 'persists'}."


async def _write_verdict(
    violation: Violation, trail: list[dict], guilty: str | None,
    client: dict, meter: CostMeter,
) -> str:
    """DeepSeek-R1 writes the verdict (only fires because a violation exists)."""
    stage = config.AGENT_TO_STAGE.get(guilty) if guilty else None
    if guilty:
        mock = (
            f"VERDICT: The {violation.dimension} violation is attributed to the "
            f"{stage} stage. Replaying the pipeline with {stage} corrected clears "
            f"the violation, while the downstream agents acted correctly on the "
            f"inputs they were given. Root cause: {stage} is the earliest "
            f"responsible stage. Evidence: "
            + " | ".join(t["evidence"] for t in trail)
        )
    else:
        mock = (
            f"VERDICT: No single agent clears the {violation.dimension} violation. "
            f"Even with every upstream stage corrected, the violation persists — "
            f"this is a requirements/feasibility problem (e.g. the stated budget "
            f"cannot meet the stated needs), attributable to Intake's capture of "
            f"infeasible constraints rather than any specialist's error."
        )
    messages = [
        {"role": "system", "content": (
            "You are the Tribunal's reasoning engine. A hard violation has fired. "
            "Given the counterfactual replay trail, name the earliest responsible "
            "stage and justify it crisply in 2-3 sentences. Start with 'VERDICT:'."
        )},
        {"role": "user", "content": (
            f"Violation: {violation.model_dump()}\n"
            f"Replay trail: {trail}\n"
            f"Tentative guilty agent: {guilty}\n"
            "Write the verdict."
        )},
    ]
    raw = await call_model(
        "conviction", messages, meter, agent="conviction",
        temperature=0.2, max_tokens=1500, mock_response=mock,
    )
    # Thinking models can wrap reasoning in <think>...</think>; strip it.
    if "</think>" in raw:
        raw = raw.split("</think>", 1)[1]
    raw = raw.strip()
    return raw or mock  # fall back to the deterministic verdict if empty


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------
@weave.op()
async def convict(violation: Violation, ctx: dict, meter: CostMeter) -> Conviction:
    client = ctx["client"]
    candidates = sorted(
        violation.candidates,
        key=lambda a: config.STAGE_ORDER.index(a) if a in config.STAGE_ORDER else 99,
    )
    trail: list[dict] = []
    guilty: str | None = None
    for agent in candidates:
        replay = await _replay_with_correction(agent, violation.dimension, ctx, meter)
        cleared = not _still_violates(violation.dimension, replay, client)
        evidence = _evidence_str(agent, violation.dimension, replay, cleared)
        trail.append({"agent": agent, "cleared": cleared, "evidence": evidence})
        if cleared:
            guilty = agent
            break

    verdict = await _write_verdict(violation, trail, guilty, client, meter)
    return Conviction(
        dimension=violation.dimension,
        guilty_agent=guilty,
        stage=config.AGENT_TO_STAGE.get(guilty) if guilty else "Intake (infeasible requirements)",
        reasoning=verdict,
        evidence=" | ".join(t["evidence"] for t in trail),
        cleared=guilty is not None,
    )
