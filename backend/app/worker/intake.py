"""Intake agent — turns a raw client brief into a RequirementsObject.

Model: Llama-3.3-70B (instruction following). When INTAKE_NAIVE is on, the
prompt deliberately under-emphasizes hard-constraint extraction, so the agent
drops deployment/compliance constraints — the seed of the demo's compliance
trap. Tribunal then attributes the downstream violation back here.
"""
from __future__ import annotations

import weave

from datetime import date

from .. import config
from ..cost_governor import CostMeter
from ..inference import call_model, parse_json_safe
from ..schemas import HardConstraint, IntakeDocument, RequirementsObject

STRICT_SYS = (
    "You are an expert consulting intake analyst. Read the client brief and "
    "extract a precise requirements object. You MUST capture every hard "
    "constraint, especially deployment model (on-prem/cloud/hybrid), data "
    "residency, and compliance certifications. Missing a hard constraint is a "
    "serious error."
)

NAIVE_SYS = (
    "You are a fast consulting intake assistant. Read the client brief and "
    "summarize what they need, their budget, and who should be involved. Focus "
    "on the business goals and keep it quick."
)

# Strict intake is asked for hard_constraints explicitly; naive intake is not —
# so a naive run genuinely omits them (the seed of the trap), live or mock.
USER_TMPL_STRICT = (
    "Client brief:\n\"\"\"\n{brief}\n\"\"\"\n\n"
    "Return ONLY a JSON object with keys: needs (list of strings), "
    "hard_constraints (list of objects with type, value, description) — capture "
    "EVERY deployment, data-residency, and compliance constraint — "
    "budget_usd (number or null), required_stakeholders (list of strings), "
    "summary (a one-paragraph restatement)."
)

USER_TMPL_NAIVE = (
    "Client brief:\n\"\"\"\n{brief}\n\"\"\"\n\n"
    "Return ONLY a JSON object with keys: needs (list of strings), "
    "budget_usd (number or null), required_stakeholders (list of strings), "
    "summary (a one-paragraph restatement). Keep it quick and focus on the "
    "business goals."
)


def _mock_requirements(client: dict, naive: bool) -> dict:
    """Deterministic intake result. Naive intake drops hard constraints (the trap)."""
    constraints = [] if naive else list(client.get("hard_constraints", []))
    return {
        "needs": client.get("needs", []),
        "hard_constraints": constraints,
        "budget_usd": client.get("budget_usd"),
        "required_stakeholders": client.get("required_stakeholders", []),
        "summary": (
            f"{client['name']} ({client.get('industry', '')}) wants to pursue: "
            + ", ".join(client.get("needs", []))
            + (
                f". First-year budget ~${client['budget_usd']:,.0f}."
                if client.get("budget_usd")
                else "."
            )
        ),
    }


@weave.op()
async def run_intake(
    client: dict, meter: CostMeter, *, naive: bool | None = None
) -> RequirementsObject:
    if naive is None:
        naive = config.INTAKE_NAIVE
    sys = NAIVE_SYS if naive else STRICT_SYS
    tmpl = USER_TMPL_NAIVE if naive else USER_TMPL_STRICT
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": tmpl.format(brief=client["raw_brief"])},
    ]
    fallback = _mock_requirements(client, naive)
    raw = await call_model(
        "intake",
        messages,
        meter,
        agent="intake",
        json_mode=True,
        mock_response=fallback,
    )
    data = parse_json_safe(raw, fallback)
    constraints = [
        HardConstraint(**c) if isinstance(c, dict) else HardConstraint(type="other", value=str(c))
        for c in data.get("hard_constraints", [])
    ]
    # Needs / budget / stakeholders are grounded in the canonical client profile
    # (the LLM otherwise conflates constraints into "needs", producing nonsense
    # pain points). The *trap* lives only in dropped hard_constraints, which a
    # naive intake still omits.
    needs = client.get("needs", [])
    stakeholders = client.get("required_stakeholders", [])
    budget = client.get("budget_usd")
    return RequirementsObject(
        client_id=client["id"],
        client_name=client["name"],
        industry=client.get("industry", ""),
        needs=needs,
        hard_constraints=constraints,
        budget_usd=budget,
        required_stakeholders=stakeholders,
        summary=data.get("summary", ""),
        document=_build_document(client, needs, constraints, budget, stakeholders),
    )


_DESIRE_PREFIXES = (
    "automated ", "automate ", "automatic ", "improved ", "improve ",
    "ai-powered ", "ai ", "real-time ", "enhanced ", "intelligent ",
)


def _pain(need: str) -> str:
    """Turn a desired-state need into a clear, current-state pain phrase."""
    n = need.strip()
    low = n.lower()
    for p in _DESIRE_PREFIXES:
        if low.startswith(p):
            n = n[len(p):]
            break
    n = n[:1].upper() + n[1:] if n else n
    return f"{n} is manual and slow today, limiting speed and scale"


PROFILE_SYS = (
    "You are a senior consulting analyst. Read the client brief and extract a "
    "complete, accurate client profile. Capture EVERY hard constraint the brief "
    "states or implies — especially deployment model (on-prem/cloud/hybrid), "
    "data residency, and compliance certifications (e.g. HIPAA, SOC 2). This "
    "profile is the ground truth other agents will be held to."
)

PROFILE_TMPL = (
    "Client brief:\n\"\"\"\n{brief}\n\"\"\"\n\n"
    "Return ONLY JSON with keys: name (string), industry (string), size (string), "
    "needs (list of short strings), hard_constraints (list of {{type, value, "
    "description}} where type is one of deployment|data_residency|compliance), "
    "budget_usd (number or null), required_stakeholders (list of strings)."
)


def _parse_budget(text: str) -> float | None:
    """Best-effort budget extraction from free text (e.g. $900,000 / 900k / $2M)."""
    import re

    mult = {"k": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}
    patterns = [
        r"\$\s*([\d][\d,\.]*)\s*(k|m|million|bn|billion)?",
        r"budget[^\d]{0,24}([\d][\d,\.]*)\s*(k|m|million|bn|billion)?",
        r"([\d][\d,\.]*)\s*(k|m|million|bn|billion)\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        suffix = (m.group(2) or "").lower()
        val *= mult.get(suffix, 1)
        if val >= 1000:  # ignore stray small numbers
            return round(val)
    return None


async def build_profile_from_brief(brief: str, name: str | None, meter: CostMeter) -> dict:
    """Thorough extraction → a ground-truth client profile from a free-text brief."""
    import re
    from .. import data_loader  # local import to avoid cycle at module load

    fallback = {
        "name": name or "Uploaded Client",
        "industry": "",
        "size": "",
        "needs": [],
        "hard_constraints": [],
        "budget_usd": None,
        "required_stakeholders": [],
    }
    messages = [
        {"role": "system", "content": PROFILE_SYS},
        {"role": "user", "content": PROFILE_TMPL.format(brief=brief)},
    ]
    raw = await call_model("intake", messages, meter, agent="intake",
                           json_mode=True, max_tokens=900, mock_response=fallback)
    data = parse_json_safe(raw, fallback)

    cid = "custom-" + re.sub(r"[^a-z0-9]+", "-", (name or "client").lower()).strip("-")[:24]
    cid = f"{cid}-{len(data_loader.CUSTOM_CLIENTS) + 1}"
    return {
        "id": cid,
        "name": data.get("name") or name or "Uploaded Client",
        "industry": data.get("industry", "") or "Custom engagement",
        "size": data.get("size", "") or "—",
        "raw_brief": brief,
        "needs": data.get("needs", []) or ["Adopt AI to modernize operations"],
        "hard_constraints": [
            c for c in data.get("hard_constraints", []) if isinstance(c, dict)
        ],
        "budget_usd": data.get("budget_usd") or _parse_budget(brief),
        "required_stakeholders": data.get("required_stakeholders", []),
        "is_trap": False,
        "_custom": True,
    }


def _build_document(client, needs, constraints, budget, stakeholders) -> IntakeDocument:
    """Synthesize the intake artifact (minutes + form) from the captured intake."""
    name = client["name"]
    industry = client.get("industry", "the organization")
    budget_txt = f"${budget:,.0f}" if budget else "to be confirmed"
    minutes = [
        f"{name} ({industry}) opened by describing goals around: {', '.join(needs) or 'AI adoption'}.",
        "Current operations were characterized as largely manual and time-intensive to scale.",
        f"First-year budget indicated at {budget_txt}.",
        f"Reviewers/owners identified: {', '.join(stakeholders) or 'TBD'}.",
    ]
    if constraints:
        minutes.append(
            "Hard constraints noted: "
            + "; ".join(f"{c.type} = {c.value}" for c in constraints)
            + "."
        )
    else:
        minutes.append(
            "No hard deployment/compliance constraints were formally logged in this session."
        )
    return IntakeDocument(
        client_name=name,
        date=date.today().isoformat(),
        attendees=["ConsultIQ Engagement Lead", "ConsultIQ Intake Analyst", *stakeholders],
        meeting_minutes=minutes,
        pain_points=[_pain(n) for n in needs] or ["Limited AI adoption across the business"],
        current_state=(
            f"{name} relies on manual processes for {', '.join(needs[:2]) or 'core operations'}, "
            "limiting speed, consistency, and the ability to scale."
        ),
        desired_outcomes=[f"AI-enabled {n.lower()}" for n in needs] or ["A clear path to adopt AI"],
        success_metrics=[
            "Reduction in cycle time per case",
            "Improved accuracy / lower error rate",
            "Cost-to-serve reduction",
            "Staff hours redeployed to higher-value work",
        ],
        constraints_noted=[f"{c.type}: {c.value} — {c.description}" for c in constraints],
        budget_note=f"First-year budget: {budget_txt}.",
        stakeholders=stakeholders,
    )
