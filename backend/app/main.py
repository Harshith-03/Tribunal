"""FastAPI surface: start an engagement, stream live events, fetch the result."""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import config
from .data_loader import clients, register_custom_client, vendors
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


def _extract_text(filename: str, content: bytes) -> str:
    """Get plain text from an uploaded brief (.txt/.md decode, .pdf via pypdf)."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    return content.decode("utf-8", errors="ignore").strip()


@app.post("/engagement/custom")
async def start_custom_engagement(
    name: str = Form("Uploaded Client"),
    brief: str = Form(""),
    file: UploadFile | None = File(None),
):
    """Start an engagement from a user-supplied brief (pasted text or a file)."""
    text = brief.strip()
    if file is not None:
        text = _extract_text(file.filename or "brief.txt", await file.read()) or text
    if not text:
        raise HTTPException(400, "No brief text provided.")

    engagement_id = uuid.uuid4().hex[:12]
    custom_id = "custom-" + engagement_id
    # register a stub; the orchestrator extracts the full ground-truth profile
    register_custom_client({
        "id": custom_id,
        "name": name.strip() or "Uploaded Client",
        "industry": "Custom engagement",
        "size": "—",
        "raw_brief": text,
        "needs": [],
        "hard_constraints": [],
        "budget_usd": None,
        "required_stakeholders": [],
        "is_trap": False,
        "_custom": True,
        "_extracted": False,
    })
    registry.create(engagement_id)
    asyncio.create_task(orchestrate(engagement_id, custom_id))
    return {"engagement_id": engagement_id, "client_id": custom_id}


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
