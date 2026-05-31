import { motion } from "framer-motion";
import type { EngagementState } from "../../useEngagement";
import { AGENT_LABEL } from "../../useEngagement";
import type { Scorecard } from "../../types";
import { scoreColor } from "../../theme";
import StepHeader from "./StepHeader";
import Collapsible from "../Collapsible";

export default function TribunalStep({
  state,
  vendors = {},
}: {
  state: EngagementState;
  vendors?: Record<string, any>;
}) {
  const { violations, convictions, scorecard, repairs } = state;
  const conv = convictions[0];
  const viol = violations[0];
  const beforeV = vendors[state.proposal?.recommended_vendor_id || ""];
  const afterV = vendors[state.repairedProposal?.recommended_vendor_id || ""];
  const repaired = repairs.find((r) => r.cleared);

  return (
    <div>
      <StepHeader stage="Stage 04 · Tribunal" title="What we caught" />

      {violations.length === 0 ? (
        <div className="border-l-2 border-good pl-5">
          <div className="font-display text-2xl text-ink">Nothing to convict.</div>
          <p className="mt-1 text-sm text-soft">
            The proposal passes every checkable constraint on first pass.
          </p>
        </div>
      ) : (
        <>
          {/* CAUGHT → DECISION hero */}
          <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-2">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="bg-canvas p-6"
            >
              <div className="kicker text-oxblood">Caught</div>
              <div className="mt-2 font-display text-2xl leading-tight text-ink">
                {conv?.dimension} violation
              </div>
              <p className="mt-2 text-sm leading-relaxed text-soft">{viol?.summary}</p>
              {beforeV && afterV && (
                <BeforeAfter before={beforeV} after={afterV} />
              )}
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-canvas p-6"
            >
              <div className="kicker">Decision</div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-display text-3xl text-ink">{conv?.stage}</span>
              </div>
              <p className="mt-1 text-sm text-soft">earliest responsible stage</p>
              {repaired && (
                <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-good/10 px-3 py-1.5 text-sm text-good">
                  ✓ repaired at source & re-verified
                </div>
              )}
            </motion.div>
          </div>

          {conv?.reasoning && (
            <div className="mt-5">
              <div className="kicker mb-2 text-oxblood">The verdict</div>
              <div className="rounded-xl border-l-2 border-oxblood bg-oxblood/[0.04] p-5">
                <p className="whitespace-pre-line font-display text-[1.05rem] leading-relaxed text-ink">
                  {conv.reasoning}
                </p>
              </div>
              {conv.evidence && (
                <Collapsible label="Counterfactual replay trail">
                  <p className="whitespace-pre-line font-mono text-[12px] leading-relaxed text-soft">
                    {conv.evidence}
                  </p>
                </Collapsible>
              )}
            </div>
          )}
        </>
      )}

      {/* soft scorecard */}
      <div className="mt-10">
        <div className="kicker mb-3">Soft scorecard · quality by author</div>
        <ScorecardTable scorecard={scorecard} />
      </div>
    </div>
  );
}

function BeforeAfter({ before, after }: { before: any; after: any }) {
  return (
    <div className="mt-5 flex items-center gap-3">
      <VendorChip v={before} bad />
      <span className="text-muted">→</span>
      <VendorChip v={after} />
    </div>
  );
}

function VendorChip({ v, bad }: { v: any; bad?: boolean }) {
  return (
    <div
      className={`flex-1 rounded-lg border p-3 ${
        bad ? "border-bad/30 bg-bad/[0.04]" : "border-good/30 bg-good/[0.05]"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-kicker text-muted">
          {v.deployment}
        </span>
        <span className={bad ? "text-bad" : "text-good"}>{bad ? "✗" : "✓"}</span>
      </div>
      <div className="mt-1 truncate text-sm font-medium text-ink" title={v.name}>
        {v.name}
      </div>
    </div>
  );
}

function ScorecardTable({ scorecard }: { scorecard?: Scorecard }) {
  if (!scorecard) return <div className="font-mono text-sm text-muted">awaiting judges…</div>;
  return (
    <table className="w-full">
      <thead>
        <tr>
          <th />
          {scorecard.dimensions.map((d) => (
            <th
              key={d}
              className="pb-2 text-center font-mono text-[10px] uppercase tracking-kicker text-muted"
            >
              {d}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {scorecard.agents.map((a) => (
          <tr key={a} className="border-t border-line">
            <td className="py-1.5 pr-3 text-sm text-soft">{AGENT_LABEL[a] || a}</td>
            {scorecard.dimensions.map((d) => {
              const cell = scorecard.matrix[a]?.[d];
              const score = cell?.score ?? 0;
              return (
                <td key={d} className="py-1.5 text-center">
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    title={cell?.rationale}
                    className="mx-auto flex h-7 w-11 items-center justify-center rounded font-mono text-[11px] text-white"
                    style={{ background: scoreColor(score) }}
                  >
                    {score.toFixed(2)}
                  </motion.div>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
