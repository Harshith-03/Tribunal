"""End-to-end engagement orchestration.

Drives Worker -> hard scorers -> conviction -> soft scorecard -> repair, while
emitting SSE stage events the whole way. Holds run state in-memory (no DB).
"""
from __future__ import annotations

from .cost_governor import BudgetExceeded, CostMeter
from .data_loader import client_by_id, register_custom_client
from .events import EngagementBus, registry
from .worker.intake import build_profile_from_brief
from .schemas import EngagementResult
from .tribunal.conviction import convict
from .tribunal.hard_scorers import run_hard_scorers
from .tribunal.repair import repair
from .tribunal.scorecard import build_scorecard
from .weave_setup import trace_url
from .worker.pipeline import run_worker

# engagement_id -> EngagementResult
RESULTS: dict[str, EngagementResult] = {}


async def _run_worker_traced(engagement_id, client, meter, bus):
    """Run the worker and capture the Weave deep-link URL for the trace."""
    try:
        output, call = await run_worker.call(engagement_id, client, meter, bus)
        # weave's .call() captures inner exceptions instead of raising; if the
        # op errored, output is None — re-raise the real error for the handler.
        if output is None and getattr(call, "exception", None):
            raise RuntimeError(str(call.exception))
        if output is not None:
            return output, getattr(call, "ui_url", None)
    except Exception:
        pass
    # fall back to a plain run (also covers weave-not-initialized) so any real
    # error propagates to the orchestrator's error handler.
    output = await run_worker(engagement_id, client, meter, bus)
    return output, None


async def orchestrate(engagement_id: str, client_id: str) -> None:
    bus: EngagementBus = registry.get(engagement_id) or registry.create(engagement_id)
    eid = engagement_id
    client = client_by_id(client_id)
    if client is None:
        bus.emit("error", eid, {"message": f"unknown client_id: {client_id}"})
        return

    meter = CostMeter()
    meter.on_update(lambda rep: bus.emit("cost_update", eid, rep.model_dump()))

    result = EngagementResult(engagement_id=eid, client_id=client_id)
    RESULTS[eid] = result

    try:
        # ---- PROFILING (custom uploaded brief only) ----
        # Build the ground-truth profile from the brief before the worker runs.
        if client.get("_custom") and not client.get("_extracted"):
            bus.emit("stage_started", eid, {"stage": "intake"})
            profile = await build_profile_from_brief(
                client.get("raw_brief", ""), client.get("name"), meter
            )
            for k in ("name", "industry", "size", "needs", "hard_constraints",
                      "budget_usd", "required_stakeholders"):
                client[k] = profile[k]
            client["_extracted"] = True
            register_custom_client(client)

        # ---- WORKER ----
        worker_out, trace_ui_url = await _run_worker_traced(eid, client, meter, bus)
        result.requirements = worker_out.requirements
        result.proposal = worker_out.proposal
        result.weave_trace_url = trace_ui_url or trace_url()

        ctx = {
            "client": client,
            "engagement_id": eid,
            "requirements": worker_out.requirements,
            "vendor": worker_out.vendor,
            "roi": worker_out.roi,
            "prioritization": worker_out.prioritization,
            "proposal": worker_out.proposal,
        }

        # ---- TRIBUNAL: hard scorers ----
        bus.emit("stage_started", eid, {"stage": "tribunal"})
        violations = run_hard_scorers(worker_out.proposal, client)
        result.violations = violations
        for v in violations:
            bus.emit("violation_found", eid, {"violation": v.model_dump()})

        # ---- TRIBUNAL: counterfactual conviction (only on violations) ----
        convictions = []
        for v in violations:
            conv = await convict(v, ctx, meter)
            convictions.append(conv)
            bus.emit("conviction", eid, {"conviction": conv.model_dump()})
        result.convictions = convictions

        # ---- TRIBUNAL: soft scorecard (separate engine) ----
        scorecard = await build_scorecard(
            worker_out.proposal, worker_out.requirements, client, meter
        )
        result.scorecard = scorecard
        bus.emit("scorecard", eid, {"scorecard": scorecard.model_dump()})

        # ---- TRIBUNAL: targeted repair ----
        for conv in convictions:
            repaired, note = await repair(conv, ctx, meter)
            if repaired is not None:
                result.repaired_proposal = repaired
                ctx["proposal"] = repaired
                residual = run_hard_scorers(repaired, client)
                bus.emit("repair_done", eid, {
                    "note": note,
                    "proposal": repaired.model_dump(),
                    "residual_violations": [r.model_dump() for r in residual],
                    "cleared": len(residual) == 0,
                })
            else:
                bus.emit("repair_done", eid, {"note": note, "cleared": False})

        result.cost = meter.report()
        result.status = "complete"
        bus.emit("complete", eid, {"result": result.model_dump()})

    except BudgetExceeded as e:
        result.status = "error"
        result.cost = meter.report()
        bus.emit("error", eid, {
            "message": f"Engagement halted by cost governor: {e}",
            "cost": meter.report().model_dump(),
        })
    except Exception as e:  # noqa: BLE001
        result.status = "error"
        bus.emit("error", eid, {"message": f"{type(e).__name__}: {e}"})
        raise
