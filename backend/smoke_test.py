"""Offline smoke test: run a full engagement in mock mode and print the flow.

Usage:  python smoke_test.py [client_id]
"""
import asyncio
import os
import sys

os.environ["USE_MOCK_INFERENCE"] = "1"  # force mock before importing app

from app.events import registry  # noqa: E402
from app.orchestrator import RESULTS, orchestrate  # noqa: E402


async def main(client_id: str):
    eid = "smoke-" + client_id
    registry.create(eid)
    await orchestrate(eid, client_id)
    bus = registry.get(eid)
    print(f"\n=== EVENT STREAM ({client_id}) ===")
    for e in bus.history:
        line = e.type
        p = e.payload
        if e.type == "agent_done":
            line += f"  agent={p.get('agent')} tokens={p.get('tokens')} usd={p.get('usd')}"
        elif e.type == "violation_found":
            line += f"  {p['violation']['dimension']}: {p['violation']['summary']}"
        elif e.type == "conviction":
            c = p["conviction"]
            line += f"  dim={c['dimension']} guilty={c['guilty_agent']} stage={c['stage']} cleared={c['cleared']}"
        elif e.type == "repair_done":
            line += f"  cleared={p.get('cleared')} note={p.get('note', '')[:80]}"
        elif e.type == "cost_update":
            line += f"  tokens={p.get('total_tokens')} usd={p.get('total_usd')}"
        elif e.type == "stage_started":
            line += f"  stage={p.get('stage')}"
        print(" ", line)

    r = RESULTS[eid]
    print(f"\n=== RESULT status={r.status} ===")
    print("recommended_vendor:", r.proposal.recommended_vendor_id if r.proposal else None)
    print("violations:", [v.dimension for v in r.violations])
    for c in r.convictions:
        print(f"  conviction[{c.dimension}] guilty={c.guilty_agent} stage={c.stage}")
        print(f"    verdict: {c.reasoning[:160]}")
    if r.repaired_proposal:
        print("repaired_vendor:", r.repaired_proposal.recommended_vendor_id)
    if r.scorecard:
        print("scorecard agents:", r.scorecard.agents, "dims:", r.scorecard.dimensions)
    print("cost:", r.cost.total_tokens, "tokens ~$", r.cost.total_usd)


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "meridian-insurer"
    asyncio.run(main(cid))
