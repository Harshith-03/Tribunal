"""FastAPI surface: start an engagement, stream live events, fetch the result."""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import config
from .data_loader import clients, vendors
from .events import registry
from .orchestrator import RESULTS, orchestrate
from .weave_setup import init_weave, trace_url

app = FastAPI(title="ConsultIQ × Tribunal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    init_weave()
    print(f"[config] mock_inference={config.USE_MOCK_INFERENCE} "
          f"project={config.weave_project_name()} "
          f"token_budget={config.ENGAGEMENT_TOKEN_BUDGET}")


class StartRequest(BaseModel):
    client_id: str


@app.get("/clients")
async def list_clients():
    return [
        {k: c[k] for k in ("id", "name", "industry", "size", "budget_usd",
                           "is_trap") if k in c}
        for c in clients()
    ]


@app.get("/clients/{client_id}")
async def get_client(client_id: str):
    c = next((c for c in clients() if c["id"] == client_id), None)
    if not c:
        raise HTTPException(404, "unknown client")
    return c


@app.get("/vendors")
async def list_vendors():
    return vendors()


@app.get("/config")
async def get_config():
    return {
        "mock_inference": config.USE_MOCK_INFERENCE,
        "project": config.weave_project_name(),
        "token_budget": config.ENGAGEMENT_TOKEN_BUDGET,
        "weave_traces_url": trace_url(),
        "models": config.MODELS,
    }


@app.post("/engagement")
async def start_engagement(req: StartRequest):
    engagement_id = uuid.uuid4().hex[:12]
    registry.create(engagement_id)
    # fire-and-forget; events stream over SSE
    asyncio.create_task(orchestrate(engagement_id, req.client_id))
    return {"engagement_id": engagement_id}


@app.get("/engagement/{engagement_id}/stream")
async def stream(engagement_id: str):
    bus = registry.get(engagement_id)
    if bus is None:
        raise HTTPException(404, "unknown engagement")

    async def event_gen():
        idx = 0
        # SSE preamble to disable proxy buffering
        yield ": stream open\n\n"
        while True:
            while idx < len(bus.history):
                evt = bus.history[idx]
                idx += 1
                payload = json.dumps({
                    "type": evt.type,
                    "payload": evt.payload,
                    "ts": evt.ts,
                })
                yield f"data: {payload}\n\n"
            if bus.done and idx >= len(bus.history):
                break
            await asyncio.sleep(0.08)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"},
    )


@app.get("/engagement/{engagement_id}/result")
async def get_result(engagement_id: str):
    result = RESULTS.get(engagement_id)
    if result is None:
        raise HTTPException(404, "unknown engagement")
    return result.model_dump()
