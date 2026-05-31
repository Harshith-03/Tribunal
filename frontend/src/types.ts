export interface ClientSummary {
  id: string;
  name: string;
  industry: string;
  size?: string;
  budget_usd?: number;
  is_trap?: boolean;
}

export interface HardConstraint {
  type: string;
  value: string;
  description: string;
}

export interface IntakeDocument {
  client_name: string;
  date: string;
  attendees: string[];
  meeting_minutes: string[];
  pain_points: string[];
  current_state: string;
  desired_outcomes: string[];
  success_metrics: string[];
  constraints_noted: string[];
  budget_note: string;
  stakeholders: string[];
}

export interface RequirementsObject {
  client_id: string;
  client_name: string;
  industry: string;
  needs: string[];
  hard_constraints: HardConstraint[];
  budget_usd?: number;
  required_stakeholders: string[];
  summary: string;
  document?: IntakeDocument;
}

export interface Claim {
  id: string;
  section: string;
  text: string;
  origin_agent: string;
  data: Record<string, any>;
}

export interface Reference {
  category: string;
  title: string;
  url?: string | null;
  note: string;
}

export interface ProposalObject {
  engagement_id: string;
  client_id: string;
  title: string;
  executive_summary: string;
  sections: Record<string, string>;
  headlines: Record<string, string>;
  section_order: string[];
  claims: Claim[];
  references: Reference[];
  recommended_vendor_id?: string;
  assigned_stakeholders: string[];
  estimated_cost_usd?: number;
  budget_usd?: number;
  annual_savings_usd?: number;
  payback_months?: number;
}

export interface Violation {
  dimension: string;
  summary: string;
  detail: string;
  offending_claim_ids: string[];
  candidates: string[];
}

export interface Conviction {
  dimension: string;
  guilty_agent: string | null;
  stage: string | null;
  reasoning: string;
  evidence: string;
  cleared: boolean;
}

export interface CellScore {
  score: number;
  rationale: string;
}

export interface Scorecard {
  matrix: Record<string, Record<string, CellScore>>;
  dimensions: string[];
  agents: string[];
}

export interface CostReport {
  total_tokens: number;
  total_usd: number;
  budget_tokens: number;
  by_agent: Record<string, { tokens: number; usd: number; calls: number }>;
  over_budget: boolean;
}

export type StageId = "intake" | "fanout" | "synthesis" | "tribunal" | "report";

export interface SSEEvent {
  type: string;
  payload: any;
  ts: number;
}

export type AgentStatus = "idle" | "running" | "done";

export interface AgentState {
  name: string;
  status: AgentStatus;
  tokens: number;
  usd: number;
  result?: any;
}
