"""HARD scorers — checkable pass/fail against synthetic ground truth.

Crucially, these score the PROPOSAL against the CLIENT'S ground-truth
constraints (from clients.json), NOT against the requirements Intake produced.
That's how a dropped constraint still gets caught: the proposal recommends a
cloud tool, the client truly needs on-prem, the scorer fires — and the
conviction engine works out that Intake is the earliest culprit.

The check_* helpers are pure predicates reused by the conviction engine when it
re-evaluates a counterfactual replay.
"""
from __future__ import annotations

import weave

from ..data_loader import vendor_by_id
from ..schemas import ProposalObject, Violation
from ..worker.specialists import acceptable_deployments


# ---------------------------------------------------------------------------
# Pure predicates (shared with conviction)
# ---------------------------------------------------------------------------
def compliance_failures(vendor_meta: dict | None, constraints: list[dict]) -> list[str]:
    """Return human-readable descriptions of every compliance failure."""
    if vendor_meta is None:
        return ["No vendor recommended, so compliance cannot be satisfied."]
    fails: list[str] = []
    for c in constraints:
        ctype, value = c.get("type"), c.get("value")
        if ctype == "deployment":
            ok = acceptable_deployments(value)
            if vendor_meta["deployment"] not in ok:
                fails.append(
                    f"Deployment: client requires '{value}' but "
                    f"{vendor_meta['name']} is '{vendor_meta['deployment']}'."
                )
        elif ctype == "compliance":
            if value not in vendor_meta["compliance_certs"]:
                fails.append(
                    f"Certification: client requires '{value}' but "
                    f"{vendor_meta['name']} holds "
                    f"{vendor_meta['compliance_certs']}."
                )
        elif ctype == "data_residency" and value != "any":
            if value not in vendor_meta["data_residency"]:
                fails.append(
                    f"Data residency: client requires '{value}' but "
                    f"{vendor_meta['name']} supports {vendor_meta['data_residency']}."
                )
    return fails


def cost_over_budget(estimated_total: float | None, budget: float | None) -> float:
    """Positive overage if over budget, else 0."""
    if estimated_total is None or budget is None:
        return 0.0
    return max(0.0, estimated_total - budget)


# ---------------------------------------------------------------------------
# Scorers (proposal vs ground truth) -> Violations
# ---------------------------------------------------------------------------
@weave.op()
def score_compliance(proposal: ProposalObject, client: dict) -> Violation | None:
    constraints = client.get("hard_constraints", [])
    vmeta = vendor_by_id(proposal.recommended_vendor_id) if proposal.recommended_vendor_id else None
    fails = compliance_failures(vmeta, constraints)
    if not fails:
        return None
    return Violation(
        dimension="compliance",
        summary=f"Recommended vendor violates {len(fails)} hard constraint(s).",
        detail=" ".join(fails),
        offending_claim_ids=["vendor-rec"]
        + [f"constraint-{c['type']}" for c in constraints],
        candidates=["intake", "vendor", "synthesis"],
    )


@weave.op()
def score_cost(proposal: ProposalObject, client: dict) -> Violation | None:
    budget = client.get("budget_usd")
    over = cost_over_budget(proposal.estimated_cost_usd, budget)
    if over <= 0:
        return None
    return Violation(
        dimension="cost",
        summary=f"Estimated cost exceeds budget by ${over:,.0f}.",
        detail=(
            f"Estimated first-year total ${proposal.estimated_cost_usd:,.0f} "
            f"vs budget ${budget:,.0f}."
        ),
        offending_claim_ids=["cost-model", "vendor-rec"],
        candidates=["intake", "vendor", "roi"],
    )


@weave.op()
def score_internal_consistency(proposal: ProposalObject, client: dict) -> Violation | None:
    issues: list[str] = []
    vmeta = vendor_by_id(proposal.recommended_vendor_id) if proposal.recommended_vendor_id else None
    # Cost model should be at least the vendor license.
    if vmeta and proposal.estimated_cost_usd is not None:
        if proposal.estimated_cost_usd < vmeta["price_usd"]:
            issues.append(
                f"Estimated total ${proposal.estimated_cost_usd:,.0f} is below "
                f"the recommended vendor's license ${vmeta['price_usd']:,.0f}."
            )
    # The recommended vendor must actually be referenced in a claim.
    vendor_claim = next((c for c in proposal.claims if c.id == "vendor-rec"), None)
    if vendor_claim and vendor_claim.data.get("vendor_id") != proposal.recommended_vendor_id:
        issues.append("Recommended vendor id does not match the vendor claim.")
    if not issues:
        return None
    return Violation(
        dimension="internal_consistency",
        summary="Cross-section inconsistency detected.",
        detail=" ".join(issues),
        offending_claim_ids=["cost-model", "vendor-rec"],
        candidates=["synthesis", "roi"],
    )


HARD_SCORERS = {
    "compliance": score_compliance,
    "cost": score_cost,
    "internal_consistency": score_internal_consistency,
}


def run_hard_scorers(proposal: ProposalObject, client: dict) -> list[Violation]:
    out: list[Violation] = []
    for fn in HARD_SCORERS.values():
        v = fn(proposal, client)
        if v is not None:
            out.append(v)
    return out
