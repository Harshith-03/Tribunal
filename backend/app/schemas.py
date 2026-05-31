"""Shared data shapes — the integration contract between Worker and Tribunal (§4).

These are intentionally plain pydantic models so they serialize cleanly over
SSE/JSON and round-trip through weave ops.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Integration contract objects
# ---------------------------------------------------------------------------
class HardConstraint(BaseModel):
    type: str                      # deployment | data_residency | compliance | budget ...
    value: str                     # e.g. "on-prem", "HIPAA", "US"
    description: str = ""


class IntakeDocument(BaseModel):
    """The intake artifact a consultant would file: meeting minutes + a detailed
    intake form. Downloadable on its own, separate from the final deliverable."""
    client_name: str
    date: str
    attendees: list[str] = Field(default_factory=list)
    meeting_minutes: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    current_state: str = ""
    desired_outcomes: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    constraints_noted: list[str] = Field(default_factory=list)
    budget_note: str = ""
    stakeholders: list[str] = Field(default_factory=list)


class RequirementsObject(BaseModel):
    """Produced by Intake. The single source of truth for what the client needs."""
    client_id: str
    client_name: str
    industry: str = ""
    needs: list[str] = Field(default_factory=list)
    hard_constraints: list[HardConstraint] = Field(default_factory=list)
    budget_usd: Optional[float] = None
    required_stakeholders: list[str] = Field(default_factory=list)
    summary: str = ""              # intake's natural-language restatement
    document: Optional[IntakeDocument] = None


class Claim(BaseModel):
    """An atomic, attributable assertion in the deliverable.

    `origin_agent` is the provenance tag that powers the soft scorecard and
    earliest-stage attribution.
    """
    id: str
    section: str                   # which report section it belongs to
    text: str
    origin_agent: str              # "intake" | "vendor" | "roi" | "prioritizer" | "synthesis"
    data: dict[str, Any] = Field(default_factory=dict)  # structured backing (e.g. vendor_id, price)


class Reference(BaseModel):
    category: str
    title: str
    url: Optional[str] = None
    note: str = ""


class ProposalObject(BaseModel):
    """Produced by Synthesis. The deliverable, with every claim tagged."""
    engagement_id: str
    client_id: str
    title: str
    executive_summary: str = ""
    sections: dict[str, str] = Field(default_factory=dict)  # section -> full prose
    headlines: dict[str, str] = Field(default_factory=dict)  # section -> one-liner
    section_order: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    recommended_vendor_id: Optional[str] = None
    assigned_stakeholders: list[str] = Field(default_factory=list)
    estimated_cost_usd: Optional[float] = None
    budget_usd: Optional[float] = None
    annual_savings_usd: Optional[float] = None
    payback_months: Optional[int] = None


# ---------------------------------------------------------------------------
# Tribunal outputs
# ---------------------------------------------------------------------------
class Violation(BaseModel):
    dimension: str                 # compliance | internal_consistency | cost
    summary: str
    detail: str = ""
    offending_claim_ids: list[str] = Field(default_factory=list)
    candidates: list[str] = Field(default_factory=list)  # agents that could be guilty


class Conviction(BaseModel):
    dimension: str
    guilty_agent: Optional[str]
    stage: Optional[str]           # human-readable earliest responsible stage
    reasoning: str = ""            # from the heavy reasoner
    evidence: str = ""             # what the counterfactual replay showed
    cleared: bool = False          # did correcting that agent clear the violation?


class CellScore(BaseModel):
    score: float                   # 0..1
    rationale: str = ""


class Scorecard(BaseModel):
    # agent -> dimension -> CellScore
    matrix: dict[str, dict[str, CellScore]] = Field(default_factory=dict)
    dimensions: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)


class CostReport(BaseModel):
    total_tokens: int = 0
    total_usd: float = 0.0
    budget_tokens: int = 0
    by_agent: dict[str, dict[str, float]] = Field(default_factory=dict)  # agent -> {tokens,usd,calls}
    over_budget: bool = False


class EngagementResult(BaseModel):
    engagement_id: str
    client_id: str
    requirements: Optional[RequirementsObject] = None
    proposal: Optional[ProposalObject] = None
    repaired_proposal: Optional[ProposalObject] = None
    violations: list[Violation] = Field(default_factory=list)
    convictions: list[Conviction] = Field(default_factory=list)
    scorecard: Optional[Scorecard] = None
    cost: Optional[CostReport] = None
    weave_trace_url: Optional[str] = None
    status: str = "running"        # running | complete | error


# ---------------------------------------------------------------------------
# SSE event
# ---------------------------------------------------------------------------
EventType = Literal[
    "stage_started",
    "agent_done",
    "requirements_ready",
    "proposal_ready",
    "violation_found",
    "conviction",
    "scorecard",
    "cost_update",
    "repair_done",
    "complete",
    "error",
]


class StageEvent(BaseModel):
    type: str
    engagement_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: float = 0.0
