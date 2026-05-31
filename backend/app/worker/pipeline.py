"""Worker orchestration + the re_run_agent primitive (§4 integration contract).

run_worker drives Intake -> parallel fan-out -> Synthesis, emitting SSE stage
events as it goes. re_run_agent re-executes a SINGLE agent with explicit
(possibly corrected) upstream inputs — the pure-ish callable the conviction
engine and targeted repair rely on.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import weave

from ..cost_governor import CostMeter
from ..events import EngagementBus
from ..schemas import ProposalObject, RequirementsObject
from . import intake as intake_mod
from . import specialists, synthesis


@dataclass
class WorkerOutput:
    requirements: RequirementsObject
    vendor: dict
    roi: dict
    prioritization: dict
    proposal: ProposalObject
    # snapshot of raw agent inputs/outputs, useful for replay & debugging
    trace: dict[str, Any] = field(default_factory=dict)


def _agent_done_payload(meter: CostMeter, agent: str, extra: dict | None = None) -> dict:
    bucket = meter.by_agent.get(agent, {})
    payload = {
        "agent": agent,
        "tokens": bucket.get("tokens", 0),
        "usd": bucket.get("usd", 0.0),
        "calls": bucket.get("calls", 0),
    }
    if extra:
        payload.update(extra)
    return payload


@weave.op()
async def run_worker(
    engagement_id: str, client: dict, meter: CostMeter, bus: EngagementBus
) -> WorkerOutput:
    eid = engagement_id

    # --- Intake ---
    bus.emit("stage_started", eid, {"stage": "intake"})
    req = await intake_mod.run_intake(client, meter)
    bus.emit("requirements_ready", eid, {"requirements": req.model_dump()})
    bus.emit("agent_done", eid, _agent_done_payload(meter, "intake"))

    # --- Fan-out (parallel) ---
    bus.emit("stage_started", eid, {"stage": "fanout",
                                    "agents": ["vendor", "roi", "prioritizer"]})

    async def vendor_task():
        v = await specialists.run_vendor(req, meter)
        bus.emit("agent_done", eid, _agent_done_payload(meter, "vendor",
                 {"result": v}))
        return v

    async def prioritizer_task():
        p = await specialists.run_prioritizer(req, meter)
        bus.emit("agent_done", eid, _agent_done_payload(meter, "prioritizer",
                 {"result": p}))
        return p

    # vendor must finish before ROI (ROI prices the chosen vendor)
    vendor, prioritization = await asyncio.gather(vendor_task(), prioritizer_task())
    roi = await specialists.run_roi(req, vendor, meter)
    bus.emit("agent_done", eid, _agent_done_payload(meter, "roi", {"result": roi}))

    # --- Synthesis ---
    bus.emit("stage_started", eid, {"stage": "synthesis"})
    proposal = await synthesis.run_synthesis(
        eid, req, vendor, roi, prioritization, client, meter
    )
    bus.emit("proposal_ready", eid, {"proposal": proposal.model_dump()})
    bus.emit("agent_done", eid, _agent_done_payload(meter, "synthesis"))

    return WorkerOutput(
        requirements=req, vendor=vendor, roi=roi,
        prioritization=prioritization, proposal=proposal,
        trace={"client_id": client["id"]},
    )


@weave.op()
async def re_run_agent(name: str, upstream_inputs: dict, meter: CostMeter) -> Any:
    """Re-execute one agent with explicit upstream inputs (counterfactual replay).

    Used by the conviction engine (swap an upstream output for a corrected one)
    and by targeted repair (regenerate one branch).
    """
    if name == "intake":
        return await intake_mod.run_intake(
            upstream_inputs["client"], meter,
            naive=upstream_inputs.get("naive", False),
        )
    if name == "vendor":
        return await specialists.run_vendor(upstream_inputs["requirements"], meter)
    if name == "roi":
        return await specialists.run_roi(
            upstream_inputs["requirements"], upstream_inputs["vendor"], meter
        )
    if name == "prioritizer":
        return await specialists.run_prioritizer(upstream_inputs["requirements"], meter)
    if name == "synthesis":
        return await synthesis.run_synthesis(
            upstream_inputs["engagement_id"],
            upstream_inputs["requirements"],
            upstream_inputs["vendor"],
            upstream_inputs["roi"],
            upstream_inputs["prioritization"],
            upstream_inputs["client"],
            meter,
        )
    raise ValueError(f"unknown agent: {name}")
