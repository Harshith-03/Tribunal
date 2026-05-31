"""Targeted repair — regenerate only the branch downstream of the guilty stage.

Fixing at the source: we correct the convicted agent and replay forward to a
new ProposalObject, then re-score to confirm the violation cleared. If no agent
was convicted (infeasible requirements), we escalate rather than fabricate a fix.
"""
from __future__ import annotations

import weave

from ..cost_governor import CostMeter
from ..data_loader import client_by_id
from ..schemas import Conviction, ProposalObject
from ..worker.pipeline import re_run_agent
from .conviction import _best_compliant_vendor, _ground_truth_req


@weave.op()
async def repair(conviction: Conviction, ctx: dict, meter: CostMeter) -> tuple[ProposalObject | None, str]:
    guilty = conviction.guilty_agent
    eid = ctx["engagement_id"]
    client = ctx["client"]
    req = ctx["requirements"]
    vendor = ctx["vendor"]
    roi = ctx["roi"]
    prioritization = ctx["prioritization"]

    if guilty is None:
        return None, (
            "No targeted repair applied: the violation persists under every "
            "single-agent correction. Escalated as an infeasible-requirements "
            "issue for human review."
        )

    if guilty == "intake":
        # Fix at the source: replace Intake's output with the correct
        # (ground-truth) requirements, then replay the full downstream branch.
        req = _ground_truth_req(client)
        vendor = await re_run_agent("vendor", {"requirements": req}, meter)
        roi = await re_run_agent("roi", {"requirements": req, "vendor": vendor}, meter)
        prioritization = await re_run_agent("prioritizer", {"requirements": req}, meter)
    elif guilty == "vendor":
        vendor = _best_compliant_vendor(client)
        roi = await re_run_agent("roi", {"requirements": req, "vendor": vendor}, meter)
    elif guilty == "roi":
        roi = await re_run_agent("roi", {"requirements": req, "vendor": vendor}, meter)
    # synthesis: just regenerate the report below

    repaired = await re_run_agent("synthesis", {
        "engagement_id": eid,
        "requirements": req,
        "vendor": vendor,
        "roi": roi,
        "prioritization": prioritization,
        "client": client,
    }, meter)

    note = (
        f"Repaired at the {conviction.stage} stage: corrected {guilty} and "
        f"replayed the downstream branch. New recommendation: "
        f"{vendor.get('vendor_name', repaired.recommended_vendor_id)}."
    )
    return repaired, note
