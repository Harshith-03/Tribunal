import { motion } from "framer-motion";
import type { EngagementState } from "../../useEngagement";
import { agentColor } from "../../theme";
import StepHeader from "./StepHeader";

export default function SynthesisStep({ state }: { state: EngagementState }) {
  const done = state.agents.synthesis?.status === "done" || !!state.proposal;
  const p = state.proposal;

  return (
    <div>
      <StepHeader
        stage="Stage 03 · Synthesis"
        title="Resolving conflicts, assembling the deliverable"
        dek="A lead-consultant agent reconciles the specialists into one report — and tags every claim with the agent that produced it."
      />

      {!done ? (
        <div className="flex items-center gap-3 py-16 text-muted">
          <motion.span
            className="h-2 w-2 rounded-full bg-oxblood"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
          <span className="font-mono text-sm">Weaving sections together…</span>
        </div>
      ) : (
        <div className="grid gap-10 md:grid-cols-[1.3fr_1fr]">
          <div>
            <div className="kicker mb-3">Executive summary</div>
            <p className="font-display text-[1.4rem] leading-snug text-ink">
              {p?.executive_summary}
            </p>
          </div>
          <div className="md:border-l md:border-line md:pl-8">
            <div className="kicker mb-3">Sections drafted</div>
            <ol className="space-y-1.5">
              {(p?.section_order || Object.keys(p?.sections || {})).map((s, i) => (
                <motion.li
                  key={s}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-2 text-sm text-soft"
                >
                  <span className="text-good">✓</span> {s}
                </motion.li>
              ))}
            </ol>
            <div className="mt-6 flex flex-wrap gap-2">
              {[...new Set((p?.claims || []).map((c) => c.origin_agent))].map((a) => (
                <span
                  key={a}
                  className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-kicker text-muted"
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: agentColor(a) }} />
                  {a}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">Every claim is attributed to its author.</p>
          </div>
        </div>
      )}
    </div>
  );
}
