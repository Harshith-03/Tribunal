"""Specialist agents (parallel fan-out): Vendor, ROI, Prioritizer.

Each is a @weave.op(). The deterministic mock selection logic is also the
*ground-truth-aware* logic the conviction engine relies on when it re-runs an
agent with corrected upstream inputs.
"""
from __future__ import annotations

import json

import weave

from ..cost_governor import CostMeter
from ..data_loader import vendors
from ..inference import call_model, parse_json_safe
from ..schemas import RequirementsObject

# ---------------------------------------------------------------------------
# Vendor / Compliance Recommender  (Llama-4-Scout)
# ---------------------------------------------------------------------------
# need-substring (lowercased) -> category-substrings (lowercased) that satisfy it
_NEED_KEYWORDS = {
    "claims": ["claims"],
    "fraud": ["fraud"],
    "document": ["document", "claims"],
    "credit": ["credit"],
    "forecast": ["forecast", "demand"],
    "pricing": ["pricing", "demand"],
    "support": ["support"],
    "knowledge": ["knowledge"],
}


def acceptable_deployments(value: str) -> set[str]:
    v = value.lower()
    if v == "on-prem":
        return {"on-prem"}
    if v in ("hybrid-or-on-prem", "hybrid", "on-prem-or-hybrid"):
        return {"on-prem", "hybrid"}
    if v == "cloud":
        return {"cloud", "hybrid", "on-prem"}
    return {"cloud", "on-prem", "hybrid"}


def _is_relevant(vendor: dict, needs: list[str]) -> bool:
    cat = vendor["category"].lower()
    text = " ".join(needs).lower()
    for key, cats in _NEED_KEYWORDS.items():
        if key in text and any(c in cat for c in cats):
            return True
    return False


def select_vendor(req: RequirementsObject) -> dict | None:
    """Cheapest available vendor that fits the (captured) needs + constraints.

    When Intake dropped a constraint, that constraint simply isn't applied here
    — which is exactly how a dropped on-prem requirement lets a cloud tool win.
    """
    # The headline recommendation targets the PRIMARY (top-priority) need.
    primary = req.needs[:1]
    cands = [v for v in vendors() if v["available"] and _is_relevant(v, primary)]
    if not cands:
        cands = [v for v in vendors() if v["available"] and _is_relevant(v, req.needs)]
    if not cands:
        cands = [v for v in vendors() if v["available"]]

    for c in req.hard_constraints:
        if c.type == "deployment":
            ok = acceptable_deployments(c.value)
            cands = [v for v in cands if v["deployment"] in ok] or cands
        elif c.type == "compliance":
            cands = [v for v in cands if c.value in v["compliance_certs"]] or cands
        elif c.type == "data_residency" and c.value != "any":
            cands = [
                v for v in cands if c.value in v["data_residency"]
            ] or cands

    if not cands:
        return None
    return min(cands, key=lambda v: v["price_usd"])


@weave.op()
async def run_vendor(req: RequirementsObject, meter: CostMeter) -> dict:
    """Best-fit-by-captured-requirements selection (deterministic, catalog-grounded)
    + an LLM-written rationale.

    The selection is a deterministic function of the requirements Intake
    produced — so when Intake drops a constraint, the agent operates on
    incomplete requirements and picks the cheapest tool (which may be cloud).
    The agentic failure lives upstream in Intake; the LLM here justifies the
    grounded recommendation.
    """
    pick = select_vendor(req)
    if pick is None:
        return {"vendor_id": None, "vendor_name": None, "deployment": None,
                "price_usd": None, "rationale": "No catalog vendor matched the needs."}

    mock_rationale = (
        f"{pick['name']} is the lowest-cost catalog option that fits the captured "
        f"requirements (${pick['price_usd']:,}, deployment={pick['deployment']}, "
        f"certs={', '.join(pick['compliance_certs'])})."
    )
    constraints_txt = (
        "; ".join(f"{c.type}={c.value}" for c in req.hard_constraints)
        or "(none captured)"
    )
    messages = [
        {"role": "system", "content": (
            "You are a vendor & compliance recommender. We have selected the "
            "lowest-cost catalog vendor that fits the CAPTURED requirements. "
            "Write a crisp 1-2 sentence rationale for this recommendation, noting "
            "deployment model and certifications. Do not pick a different vendor."
        )},
        {"role": "user", "content": (
            f"Captured needs: {req.needs}\n"
            f"Captured hard constraints: {constraints_txt}\n"
            f"Selected vendor: {json.dumps(pick)}\n"
            "Return ONLY JSON: {rationale}."
        )},
    ]
    raw = await call_model("vendor", messages, meter, agent="vendor",
                           json_mode=True, mock_response={"rationale": mock_rationale})
    data = parse_json_safe(raw, {"rationale": mock_rationale})
    return {
        "vendor_id": pick["id"],
        "vendor_name": pick["name"],
        "deployment": pick["deployment"],
        "price_usd": pick["price_usd"],
        "rationale": data.get("rationale") or mock_rationale,
    }


# ---------------------------------------------------------------------------
# ROI / Cost Modeler  (DeepSeek-V3)
# ---------------------------------------------------------------------------
@weave.op()
async def run_roi(req: RequirementsObject, vendor: dict, meter: CostMeter) -> dict:
    price = float(vendor.get("price_usd") or 0)
    # license + implementation (25%) + first-year support (10%)
    implementation = round(price * 0.25)
    support = round(price * 0.10)
    total = round(price + implementation + support)
    annual_savings = round(total * 0.55)  # illustrative
    payback_months = round(total / max(annual_savings, 1) * 12)
    mock = {
        "license_usd": price,
        "implementation_usd": implementation,
        "first_year_support_usd": support,
        "estimated_total_usd": total,
        "annual_savings_usd": annual_savings,
        "payback_months": payback_months,
        "roi_narrative": (
            f"Estimated first-year total cost of ${total:,} "
            f"(license ${price:,} + implementation ${implementation:,} + support "
            f"${support:,}). Projected annual savings ${annual_savings:,}, "
            f"payback ~{payback_months} months."
        ),
    }
    messages = [
        {"role": "system", "content": (
            "You are an ROI and cost modeler. Build a first-year cost model "
            "(license + implementation + support) and an ROI narrative."
        )},
        {"role": "user", "content": (
            f"Client budget: ${req.budget_usd}\n"
            f"Recommended vendor: {json.dumps(vendor)}\n"
            "Return ONLY JSON with keys license_usd, implementation_usd, "
            "first_year_support_usd, estimated_total_usd, annual_savings_usd, "
            "payback_months, roi_narrative."
        )},
    ]
    raw = await call_model("roi", messages, meter, agent="roi",
                           json_mode=True, mock_response=mock)
    data = parse_json_safe(raw, mock)
    # Cost math is ground truth (catalog price), not an LLM hallucination — the
    # cost hard scorer and the savings figures depend on it. Keep only the LLM's
    # narrative for flavor.
    for k in ("license_usd", "implementation_usd", "first_year_support_usd",
              "estimated_total_usd", "annual_savings_usd", "payback_months"):
        data[k] = mock[k]
    data.setdefault("roi_narrative", mock["roi_narrative"])
    return data


# ---------------------------------------------------------------------------
# Use-case Prioritizer  (Llama-3.1-8B)
# ---------------------------------------------------------------------------
@weave.op()
async def run_prioritizer(req: RequirementsObject, meter: CostMeter) -> dict:
    ranked = []
    for i, need in enumerate(req.needs):
        ranked.append({
            "use_case": need,
            "rank": i + 1,
            "impact": round(0.9 - i * 0.15, 2),
            "feasibility": round(0.85 - i * 0.1, 2),
            "rationale": f"'{need}' ranked #{i + 1} by impact-to-effort.",
        })
    mock = {"ranked_use_cases": ranked,
            "summary": "Sequenced by impact-to-effort; tackle the top item first."}
    messages = [
        {"role": "system", "content": (
            "You are a use-case prioritizer. Rank the client's needs by "
            "impact-to-effort and explain the sequencing."
        )},
        {"role": "user", "content": (
            f"Needs: {json.dumps(req.needs)}\n"
            "Return ONLY JSON: {ranked_use_cases:[{use_case,rank,impact,"
            "feasibility,rationale}], summary}."
        )},
    ]
    raw = await call_model("prioritizer", messages, meter, agent="prioritizer",
                           json_mode=True, mock_response=mock)
    return parse_json_safe(raw, mock)
