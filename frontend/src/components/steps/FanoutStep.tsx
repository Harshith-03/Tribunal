import { motion } from "framer-motion";
import type { EngagementState } from "../../useEngagement";
import type { AgentState } from "../../types";
import { agentColor, fmtTokens, fmtUsd } from "../../theme";
import StepHeader from "./StepHeader";
import OrchestrationGraph from "../OrchestrationGraph";

const SPECIALISTS = [
  {
    id: "vendor",
    title: "Find the right vendor",
    does: "Searches the vendor catalog for the best-fit tool that meets the captured needs and constraints.",
    result: (r: any) => (r.vendor_name ? `${r.vendor_name} · ${r.deployment}` : null),
  },
  {
    id: "roi",
    title: "Cost & payback",
    does: "Builds the first-year cost model for the chosen vendor and estimates savings and payback.",
    result: (r: any) => (r.estimated_total_usd ? `${fmtUsd(r.estimated_total_usd)} year one` : null),
  },
  {
    id: "prioritizer",
    title: "What to do first",
    does: "Ranks the use cases so the highest-impact work is sequenced first.",
    result: (r: any) => r.ranked_use_cases?.[0]?.use_case ?? null,
  },
];

export default function FanoutStep({ state }: { state: EngagementState }) {
  return (
    <div>
      <StepHeader
        stage="Stage 02 · Specialists"
        title="Synchronized Orchestration"
        dek="Each specialist tackles one part of the problem on its own model, then hands its finding to Synthesis."
      />

      <div className="grid gap-8 md:grid-cols-[1fr_320px]">
        {/* the important part — what each agent is doing */}
        <div className="space-y-3">
          {SPECIALISTS.map((s, i) => (
            <AgentCard key={s.id} spec={s} agent={state.agents[s.id]} delay={i * 0.08} />
          ))}
        </div>

        {/* supporting diagram, to the side */}
        <aside className="rounded-xl border border-line bg-paper/60 p-4">
          <div className="kicker mb-1">How the work flows</div>
          <OrchestrationGraph agents={state.agents} />
          <p className="mt-1 text-center text-xs text-muted">
            Intake briefs all three; ROI prices the vendor’s pick; all feed Synthesis.
          </p>
        </aside>
      </div>
    </div>
  );
}

function AgentCard({
  spec,
  agent,
  delay,
}: {
  spec: { id: string; title: string; does: string; result: (r: any) => string | null };
  agent?: AgentState;
  delay: number;
}) {
  const color = agentColor(spec.id);
  const st = agent?.status ?? "idle";
  const result = agent?.result ? spec.result(agent.result) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-xl border border-line bg-paper/50 p-5"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="mt-1 h-8 w-1 rounded" style={{ background: color }} />
          <div>
            <div className="font-display text-xl text-ink">{spec.title}</div>
            <p className="mt-1 max-w-md text-sm leading-relaxed text-soft">{spec.does}</p>
          </div>
        </div>
        <Status st={st} color={color} />
      </div>

      <div className="mt-4 flex items-end justify-between border-t border-line pt-3">
        <div>
          <div className="kicker">{st === "done" ? "Finding" : "Working on it"}</div>
          <div className="font-display text-lg text-ink">{result || "—"}</div>
        </div>
        <div className="text-right font-mono text-[11px] text-muted">
          {fmtTokens(agent?.tokens)} tok · {fmtUsd(agent?.usd)}
        </div>
      </div>
    </motion.div>
  );
}

function Status({ st, color }: { st: string; color: string }) {
  if (st === "done")
    return (
      <span className="font-mono text-[10px] uppercase tracking-kicker" style={{ color }}>
        done
      </span>
    );
  if (st === "running")
    return (
      <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-kicker text-soft">
        <motion.span
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: color }}
          animate={{ opacity: [1, 0.25, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
        />
        working
      </span>
    );
  return <span className="font-mono text-[10px] uppercase tracking-kicker text-line">idle</span>;
}
