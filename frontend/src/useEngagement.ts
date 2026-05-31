import { useCallback, useReducer } from "react";
import { startEngagement, streamEngagement } from "./api";
import type {
  AgentState,
  Conviction,
  CostReport,
  ProposalObject,
  RequirementsObject,
  Scorecard,
  SSEEvent,
  StageId,
  Violation,
} from "./types";

export const AGENT_ORDER = ["intake", "vendor", "roi", "prioritizer", "synthesis"];
export const AGENT_LABEL: Record<string, string> = {
  intake: "Intake",
  vendor: "Vendor / Compliance",
  roi: "ROI / Cost",
  prioritizer: "Use-case Prioritizer",
  synthesis: "Synthesis",
  judge: "Soft Judge",
  conviction: "Conviction Reasoner",
};

interface RepairInfo {
  note: string;
  cleared: boolean;
  residual: Violation[];
}

export interface EngagementState {
  engagementId?: string;
  stage?: StageId;
  running: boolean;
  done: boolean;
  requirements?: RequirementsObject;
  agents: Record<string, AgentState>;
  proposal?: ProposalObject;
  repairedProposal?: ProposalObject;
  violations: Violation[];
  convictions: Conviction[];
  scorecard?: Scorecard;
  cost?: CostReport;
  repairs: RepairInfo[];
  weaveUrl?: string;
  error?: string;
  events: SSEEvent[];
}

function initAgents(): Record<string, AgentState> {
  const a: Record<string, AgentState> = {};
  for (const n of AGENT_ORDER) a[n] = { name: n, status: "idle", tokens: 0, usd: 0 };
  return a;
}

function initialState(): EngagementState {
  return {
    running: false,
    done: false,
    agents: initAgents(),
    violations: [],
    convictions: [],
    repairs: [],
    events: [],
  };
}

type Action = { kind: "reset" } | { kind: "start"; id: string } | { kind: "event"; e: SSEEvent };

function reducer(state: EngagementState, action: Action): EngagementState {
  if (action.kind === "reset") return initialState();
  if (action.kind === "start")
    return { ...initialState(), engagementId: action.id, running: true };

  const e = action.e;
  const s = { ...state, events: [...state.events, e] };
  const p = e.payload || {};

  switch (e.type) {
    case "stage_started": {
      const stage = p.stage as StageId;
      s.stage = stage;
      const agents = { ...s.agents };
      if (stage === "intake") agents.intake = { ...agents.intake, status: "running" };
      if (stage === "fanout") {
        for (const n of ["vendor", "roi", "prioritizer"])
          agents[n] = { ...agents[n], status: "running" };
      }
      if (stage === "synthesis")
        agents.synthesis = { ...agents.synthesis, status: "running" };
      s.agents = agents;
      return s;
    }
    case "requirements_ready":
      s.requirements = p.requirements;
      return s;
    case "agent_done": {
      const agents = { ...s.agents };
      const a = agents[p.agent] || { name: p.agent, status: "idle", tokens: 0, usd: 0 };
      agents[p.agent] = {
        ...a,
        status: "done",
        tokens: p.tokens ?? a.tokens,
        usd: p.usd ?? a.usd,
        result: p.result ?? a.result,
      };
      s.agents = agents;
      return s;
    }
    case "proposal_ready":
      s.proposal = p.proposal;
      return s;
    case "violation_found":
      s.violations = [...s.violations, p.violation];
      return s;
    case "conviction":
      s.convictions = [...s.convictions, p.conviction];
      return s;
    case "scorecard":
      s.scorecard = p.scorecard as Scorecard;
      return s;
    case "cost_update":
      s.cost = p as CostReport;
      return s;
    case "repair_done":
      s.repairs = [
        ...s.repairs,
        {
          note: p.note,
          cleared: !!p.cleared,
          residual: p.residual_violations || [],
        },
      ];
      if (p.proposal) s.repairedProposal = p.proposal as ProposalObject;
      return s;
    case "complete": {
      const r = p.result || {};
      s.running = false;
      s.done = true;
      s.stage = "report";
      s.weaveUrl = r.weave_trace_url;
      if (r.cost) s.cost = r.cost;
      return s;
    }
    case "error":
      s.running = false;
      s.done = true;
      s.error = p.message || "unknown error";
      return s;
    default:
      return s;
  }
}

export function useEngagement() {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);

  const run = useCallback(async (clientId: string) => {
    dispatch({ kind: "reset" });
    const id = await startEngagement(clientId);
    dispatch({ kind: "start", id });
    streamEngagement(id, (e) => dispatch({ kind: "event", e }));
  }, []);

  const reset = useCallback(() => dispatch({ kind: "reset" }), []);

  return { state, run, reset };
}
