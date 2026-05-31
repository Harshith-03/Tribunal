import { motion } from "framer-motion";
import type { EngagementState } from "../../useEngagement";
import { AGENT_LABEL } from "../../useEngagement";
import { agentColor } from "../../theme";
import { openReport } from "../../report";
import StepHeader from "./StepHeader";
import Collapsible from "../Collapsible";

function usdShort(n?: number): string {
  if (n == null) return "—";
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(2).replace(/\.00$/, "") + "M";
  if (n >= 1e3) return "$" + Math.round(n / 1e3) + "K";
  return "$" + n;
}

export default function ReportStep({
  state,
  client,
}: {
  state: EngagementState;
  client?: any;
  weaveProject?: string;
}) {
  const p = state.repairedProposal || state.proposal;
  if (!p) return null;
  const order = p.section_order?.length ? p.section_order : Object.keys(p.sections || {});

  const budget = p.budget_usd ?? state.requirements?.budget_usd ?? 0;
  const invested = p.estimated_cost_usd ?? 0;
  const saved = Math.max(0, budget - invested);
  const investedPct = budget ? Math.min(100, (invested / budget) * 100) : 0;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <StepHeader
          stage={`Stage 05 · Deliverable${state.repairedProposal ? " · repaired" : ""}`}
          title={p.title}
        />
        <div className="flex items-center gap-3">
          {state.weaveUrl && (
            <a href={state.weaveUrl} target="_blank" rel="noreferrer" className="link text-sm">
              ↗ Weave trace
            </a>
          )}
          <button
            onClick={() => openReport(p, client, state.convictions)}
            className="group inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 text-sm font-medium text-canvas transition hover:bg-oxblood"
          >
            Full report
            <span className="transition-transform group-hover:translate-y-0.5">↓</span>
          </button>
        </div>
      </div>

      {/* SAVINGS / BUDGET — top, most evident */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-line bg-paper/60 p-6"
      >
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="kicker text-teal">Under budget</div>
            <div className="font-display text-5xl text-ink">{usdShort(saved)}</div>
            <div className="mt-1 text-sm text-muted">
              saved vs the {usdShort(budget)} budget
            </div>
          </div>
          <div className="flex gap-8">
            <Metric label="Invested" value={usdShort(invested)} />
            <Metric label="Savings / yr" value={usdShort(p.annual_savings_usd)} accent />
            <Metric label="Payback" value={p.payback_months ? `${p.payback_months} mo` : "—"} />
          </div>
        </div>
        {/* comparison bar */}
        <div className="mt-5">
          <div className="flex h-3 overflow-hidden rounded-full bg-line">
            <motion.div
              className="h-full bg-ink"
              initial={{ width: 0 }}
              animate={{ width: `${investedPct}%` }}
              transition={{ type: "spring", stiffness: 120, damping: 22 }}
            />
            <div className="h-full flex-1 bg-teal/40" />
          </div>
          <div className="mt-1.5 flex justify-between font-mono text-[10px] uppercase tracking-kicker text-muted">
            <span>● invested {usdShort(invested)}</span>
            <span>budget {usdShort(budget)}</span>
          </div>
        </div>
      </motion.div>

      {/* brief + one-liners */}
      <p className="mt-8 font-display text-[1.3rem] leading-snug text-ink">
        {p.executive_summary}
      </p>

      <div className="mt-8">
        <div className="kicker mb-2">At a glance</div>
        <div className="divide-y divide-line border-y border-line">
          {order.map((name, i) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="grid grid-cols-[32px_180px_1fr] items-baseline gap-3 py-3"
            >
              <span className="font-mono text-xs text-oxblood">{String(i + 1).padStart(2, "0")}</span>
              <span className="font-display text-[15px] text-ink">{name}</span>
              <span className="text-sm text-soft">{p.headlines?.[name] || p.sections[name]}</span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* details on demand */}
      <div className="mt-6">
        <Collapsible label="Full narrative">
          <div className="space-y-5">
            {order.map((name) => (
              <div key={name}>
                <div className="font-display text-lg text-ink">{name}</div>
                <p className="mt-1 text-[15px] leading-relaxed text-soft">{p.sections[name]}</p>
              </div>
            ))}
          </div>
        </Collapsible>

        {(p.references?.length ?? 0) > 0 && (
          <Collapsible label="References & compliance — verify it yourself" defaultOpen>
            <div className="space-y-3">
              {p.references.map((r, i) => (
                <div key={i} className="grid grid-cols-[120px_1fr] gap-3">
                  <div className="font-mono text-[10px] uppercase tracking-kicker text-muted">
                    {r.category}
                  </div>
                  <div>
                    <div className="text-[15px] font-medium text-ink">
                      {r.url ? (
                        <a href={r.url} target="_blank" rel="noreferrer" className="link">
                          {r.title} ↗
                        </a>
                      ) : (
                        r.title
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-soft">{r.note}</p>
                  </div>
                </div>
              ))}
            </div>
          </Collapsible>
        )}

        <Collapsible label="Provenance — every claim, by author">
          <div className="space-y-1.5">
            {p.claims.map((c) => (
              <div key={c.id} className="grid grid-cols-[150px_1fr] gap-3 py-1 text-sm">
                <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-kicker text-muted">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: agentColor(c.origin_agent) }} />
                  {AGENT_LABEL[c.origin_agent] || c.origin_agent}
                </span>
                <span className="text-soft">{c.text}</span>
              </div>
            ))}
          </div>
        </Collapsible>
      </div>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className={`font-display text-2xl ${accent ? "text-teal" : "text-ink"}`}>{value}</div>
      <div className="kicker mt-0.5">{label}</div>
    </div>
  );
}
