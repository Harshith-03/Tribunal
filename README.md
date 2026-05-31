# ConsultIQ × Tribunal

**AI consulting you can _trust_ and _afford_.** A client answers a short intake;
an agent workforce produces a full consulting deliverable in minutes; and
**Tribunal** — the accountability layer — scores it, convicts the specific agent
behind any verifiable failure, attributes it to the *earliest* responsible
stage, fixes it at the source, and keeps the engagement under a hard budget.

Built for the **Multi-Agent Orchestration @ W&B / MIT** hackathon. Powered
end-to-end by **W&B Weave** (tracing/scorers/cost) and **W&B Inference** (6 models).

---

## The core idea: two separate credit-assignment engines

| Engine | For | How |
|---|---|---|
| **Conviction** (hard dims) | compliance, cost, internal-consistency | counterfactual replay: correct a suspect agent from ground truth, replay downstream, see if the violation clears → convict the **earliest** stage that clears it |
| **Scorecard** (soft dims) | relevance, risk | provenance-weighted LLM-judge: score each agent's own claims, build an agent × dimension matrix |

We **never** convict an agent of a soft dimension. The two engines live side by side.

---

## Architecture

```
Worker (ConsultIQ pipeline)            Tribunal (accountability harness)
  Intake        Llama-3.3-70B            hard scorers  -> Violations
  Vendor        gemma-4-31B-it           conviction    -> Qwen3-235B-Thinking (fires only on a violation)
  ROI/Cost      DeepSeek-V3.1            scorecard     -> Phi-4-mini judge
  Prioritizer   Llama-3.1-8B            cost governor -> token budget + Semaphore(4)
  Synthesis     Llama-3.3-70B            repair        -> DeepSeek-V3.1
        |                                       |
        +--- every agent is a @weave.op() ------+
```

- One global `asyncio.Semaphore(4)` + exponential backoff on 429/503 around
  every Inference call.
- Each claim in the deliverable carries an `origin_agent` provenance tag.
- `re_run_agent(name, upstream_inputs)` is the counterfactual-replay primitive.
- Full run streams over SSE: `stage_started`, `agent_done`, `violation_found`,
  `conviction`, `scorecard`, `cost_update`, `repair_done`, `complete`.

---

## The demo (Meridian Mutual — the trap)

A mid-size insurer, **on-prem only, $2M budget**. A *naive* Intake agent drops
the on-prem/HIPAA constraint → the Vendor recommendation lands on a cloud tool →
the deliverable looks great → **Tribunal flags a compliance violation** → the
conviction engine replays counterfactually and concludes:

> *"The compliance violation wasn't the Vendor agent — **Intake** never captured
> the on-prem constraint."*

…then repairs at the source (re-run from corrected requirements → on-prem
vendor), re-verifies the fix, holds the budget, and deep-links to the live Weave
trace as proof.

Three built-in scenarios:
- **Meridian** (trap) → compliance violation convicted to **Intake**, repaired.
- **Atlas** (trap) → cost violation; *no single agent clears it* → escalated as
  an infeasible-budget requirements problem.
- **Northwind** (control) → clean, no violations.

---

## Running it

### 1. Backend (FastAPI + Weave + Inference)

```bash
cd backend
pip install -r requirements.txt
# put your W&B key + entity in backend/.env  (copy from .env.example)
python -m uvicorn app.main:app --port 8000
```

Set `USE_MOCK_INFERENCE=1` in `.env` to run fully offline with a deterministic
mock LLM (no tokens spent) — the trap still fires.

Quick offline sanity check:
```bash
python smoke_test.py meridian-insurer
```

### 2. Frontend (React + TS + Tailwind + Framer Motion)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api -> :8000)
```

Pick a client, hit **Run engagement**, and watch the five animated stages drive
off the real SSE event stream.

---

## Configuration (`backend/.env`)

| Var | Meaning |
|---|---|
| `WANDB_API_KEY` | W&B key — used for both Weave and Inference |
| `WANDB_ENTITY` / `WANDB_PROJECT` | where traces + usage are recorded |
| `USE_MOCK_INFERENCE` | `1` = offline deterministic mock |
| `ENGAGEMENT_TOKEN_BUDGET` | hard per-engagement token budget |
| `INFERENCE_CONCURRENCY` | semaphore size (429 cap) |
| `INTAKE_NAIVE` | `1` = naive intake that drops constraints (fuels the trap) |

---

## Synthetic data (`/data`)

`clients.json` (profiles + trap cases) · `vendors.json` (catalog: price,
deployment, certs, availability) · `required_roles.json` · `risk_bank.json`.
