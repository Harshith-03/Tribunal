"""Synthesis agent — conflict resolver + AI-consulting report generator.

Model: Llama-3.3-70B. Produces a ProposalObject structured like a real AI
consulting deliverable (Situation → Why AI Now → Recommended Solution →
Roadmap → Investment & ROI → Risk & Compliance → Governance → Next Steps),
where EVERY claim carries an `origin_agent` tag and the report cites
authoritative references (e.g. the HIPAA standard) the client can verify.
"""
from __future__ import annotations

import json

import weave

from ..cost_governor import CostMeter
from ..data_loader import risks_for_client, vendor_by_id
from ..inference import call_model, parse_json_safe
from ..references import references_for
from ..schemas import Claim, ProposalObject, Reference, RequirementsObject

SECTION_ORDER = [
    "Situation",
    "Why AI, Why Now",
    "Recommended Solution",
    "Implementation Roadmap",
    "Investment & ROI",
    "Risk & Compliance",
    "Governance & Stakeholders",
    "Recommended Next Steps",
]


def _claim(cid: str, section: str, text: str, agent: str, **data) -> Claim:
    return Claim(id=cid, section=section, text=text, origin_agent=agent, data=data)


def _seed_sections(req, vendor, roi, prioritization, client) -> dict:
    vname = vendor.get("vendor_name") or "the recommended vendor"
    deployment = vendor.get("deployment") or "—"
    price = vendor.get("price_usd") or 0
    total = roi.get("estimated_total_usd") or 0
    savings = roi.get("annual_savings_usd") or 0
    payback = roi.get("payback_months") or 0
    budget = req.budget_usd or 0
    needs = req.needs or ["AI adoption"]
    ranked = prioritization.get("ranked_use_cases", [])
    top = ranked[0]["use_case"] if ranked else needs[0]
    risks = risks_for_client(client["id"])[:3]
    stakeholders = ", ".join(req.required_stakeholders) or "an executive sponsor and process owner"
    industry = client.get("industry", "the industry")

    roadmap = " ".join(
        f"Phase {i + 1} ({i * 3}–{i * 3 + 3} mo): {uc.get('use_case')}."
        for i, uc in enumerate(ranked[:3])
    ) or f"Phase 1 (0–3 mo): pilot {top}; Phase 2 (3–6 mo): scale."

    return {
        "Situation": (
            f"{client['name']} ({industry}, {client.get('size', '')}) wants to move "
            f"from manual, time-intensive operations toward an AI-enabled model. The "
            f"priority pains are {', '.join(needs)}. This engagement defines a "
            f"concrete, compliant path to embedding AI into day-to-day operations — "
            f"not a science project, but a route to staying market-current."
        ),
        "Why AI, Why Now": (
            f"Across {industry.lower()}, AI is shifting from differentiator to table "
            f"stakes: peers are compressing cycle times, cutting error rates, and "
            f"redeploying skilled staff to higher-value work. Acting now lets "
            f"{client['name']} capture efficiency on {top.lower()} while building the "
            f"data and governance foundations that make broader AI adoption safe and fast."
        ),
        "Recommended Solution": (
            f"We recommend {vname} — a {deployment} solution at ${price:,}. "
            f"{vendor.get('rationale', '')} It targets the highest-impact use case, "
            f"{top.lower()}, and is intended to be operated, not just installed."
        ),
        "Implementation Roadmap": (
            f"A phased rollout de-risks adoption and proves value early. {roadmap} "
            f"Each phase ships a measurable outcome before the next begins."
        ),
        "Investment & ROI": (
            f"Estimated first-year investment of ${total:,} against a ${budget:,} "
            f"budget. {roi.get('roi_narrative', '')} Projected annual savings of "
            f"${savings:,} imply a payback of roughly {payback} months."
        ),
        "Risk & Compliance": (
            f"The material risks for this initiative are: "
            + "; ".join(risks)
            + f". The recommended deployment is {deployment}. Compliance obligations "
            f"are addressed in the References, where {client['name']} can consult the "
            f"governing standards (e.g. HIPAA, SOC 2) directly for clarification."
        ),
        "Governance & Stakeholders": (
            f"We recommend a standing AI steering group ({stakeholders}) operating "
            f"under the NIST AI Risk Management Framework. Define decision rights, a "
            f"model-monitoring cadence, and an audit trail before go-live."
        ),
        "Recommended Next Steps": (
            f"1) Confirm hard constraints and complete a data inventory. "
            f"2) Stand up a 6-week pilot on {top.lower()}. "
            f"3) Negotiate {vname} commercial terms. "
            f"4) Convene the AI governance group and set success metrics."
        ),
    }


def _seed_headlines(req, vendor, roi, prioritization, client) -> dict:
    vname = vendor.get("vendor_name") or "a fit-for-purpose platform"
    deployment = vendor.get("deployment") or "—"
    total = roi.get("estimated_total_usd") or 0
    savings = roi.get("annual_savings_usd") or 0
    payback = roi.get("payback_months") or 0
    needs = req.needs or ["AI adoption"]
    ranked = prioritization.get("ranked_use_cases", [])
    top = (ranked[0]["use_case"] if ranked else needs[0]).lower()
    phases = min(3, max(1, len(ranked)))
    risk0 = (client.get("hard_constraints") or [{}])
    return {
        "Situation": f"{client['name']} runs {needs[0].lower()} manually and wants a compliant AI path.",
        "Why AI, Why Now": f"AI is becoming table stakes in {client.get('industry','the sector').lower()} — moving now protects competitiveness.",
        "Recommended Solution": f"Adopt {vname} ({deployment}) for {top}.",
        "Implementation Roadmap": f"{phases} phases, value shipped first.",
        "Investment & ROI": f"${total:,} year one · ~{payback}mo payback · ${savings:,}/yr saved.",
        "Risk & Compliance": f"{deployment.capitalize()} deployment keeps data compliant.",
        "Governance & Stakeholders": "Standing AI steering group under the NIST AI RMF.",
        "Recommended Next Steps": f"Confirm constraints, then pilot {top} in 6 weeks.",
    }


@weave.op()
async def run_synthesis(
    engagement_id: str,
    req: RequirementsObject,
    vendor: dict,
    roi: dict,
    prioritization: dict,
    client: dict,
    meter: CostMeter,
) -> ProposalObject:
    vendor_id = vendor.get("vendor_id")
    total = roi.get("estimated_total_usd")
    assigned = list(req.required_stakeholders)

    # --- claims with hard-wired provenance ---
    claims: list[Claim] = []
    for i, need in enumerate(req.needs):
        claims.append(_claim(f"need-{i}", "Situation", f"Address: {need}.", "intake", need=need))
    for c in req.hard_constraints:
        claims.append(_claim(f"constraint-{c.type}", "Situation",
                             f"Hard constraint — {c.type}: {c.value}. {c.description}",
                             "intake", constraint_type=c.type, value=c.value))
    claims.append(_claim(
        "vendor-rec", "Recommended Solution",
        f"Recommend {vendor.get('vendor_name', vendor_id)} "
        f"(deployment: {vendor.get('deployment')}, ${(vendor.get('price_usd') or 0):,}). "
        f"{vendor.get('rationale', '')}",
        "vendor", vendor_id=vendor_id, deployment=vendor.get("deployment"),
        price_usd=vendor.get("price_usd"),
    ))
    claims.append(_claim("cost-model", "Investment & ROI", roi.get("roi_narrative", ""),
                         "roi", estimated_total_usd=total, budget_usd=req.budget_usd))
    for uc in prioritization.get("ranked_use_cases", []):
        claims.append(_claim(f"prio-{uc.get('rank')}", "Implementation Roadmap",
                             f"#{uc.get('rank')} {uc.get('use_case')} — {uc.get('rationale', '')}",
                             "prioritizer", **uc))
    claims.append(_claim("stakeholders", "Governance & Stakeholders",
                         f"Reviewed/owned by: {', '.join(assigned) or 'TBD'}.",
                         "synthesis", assigned_stakeholders=assigned))

    seeds = _seed_sections(req, vendor, roi, prioritization, client)
    headlines = _seed_headlines(req, vendor, roi, prioritization, client)
    exec_seed = (
        f"{client['name']} can reach a compliant, ROI-positive AI footprint by "
        f"adopting {vendor.get('vendor_name', 'the recommended platform')} for "
        f"{(req.needs[0] if req.needs else 'its priority use case').lower()}, at an "
        f"estimated ${(total or 0):,} in year one."
    )

    messages = [
        {"role": "system", "content": (
            "You are a lead AI-strategy consultant writing the final client "
            "deliverable. Resolve conflicts between specialist inputs and write "
            "tight, client-ready prose for EACH section. Frame it as a path to "
            "incorporate AI and stay market-current. Do not invent vendors or "
            "numbers beyond what is provided."
        )},
        {"role": "user", "content": (
            f"Requirements:\n{req.model_dump_json()}\n\n"
            f"Vendor: {json.dumps(vendor)}\nROI: {json.dumps(roi)}\n"
            f"Prioritization: {json.dumps(prioritization)}\n\n"
            f"Write these sections: {SECTION_ORDER}.\n"
            "Return ONLY JSON: {executive_summary, sections:{<name>:<prose>}}."
        )},
    ]
    data = parse_json_safe(
        await call_model("synthesis", messages, meter, agent="synthesis",
                         json_mode=True, max_tokens=1800,
                         mock_response={"executive_summary": exec_seed, "sections": seeds}),
        {"executive_summary": exec_seed, "sections": seeds},
    )
    sections = data.get("sections", seeds)
    for k, v in seeds.items():
        if not sections.get(k):
            sections[k] = v

    vmeta = vendor_by_id(vendor_id) if vendor_id else None
    references = [
        Reference(**r) for r in references_for(client.get("hard_constraints", []), vmeta)
    ]

    return ProposalObject(
        engagement_id=engagement_id,
        client_id=req.client_id,
        title=f"AI Transformation Proposal — {req.client_name}",
        executive_summary=data.get("executive_summary", exec_seed),
        sections=sections,
        headlines=headlines,
        section_order=[s for s in SECTION_ORDER if s in sections],
        claims=claims,
        references=references,
        recommended_vendor_id=vendor_id,
        assigned_stakeholders=assigned,
        estimated_cost_usd=total,
        budget_usd=req.budget_usd,
        annual_savings_usd=roi.get("annual_savings_usd"),
        payback_months=int(round(roi["payback_months"]))
        if roi.get("payback_months") is not None
        else None,
    )
