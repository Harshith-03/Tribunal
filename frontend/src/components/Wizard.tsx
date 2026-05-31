import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { EngagementState } from "../useEngagement";
import { fmtTokens, fmtUsd } from "../theme";
import IntakeStep from "./steps/IntakeStep";
import FanoutStep from "./steps/FanoutStep";
import SynthesisStep from "./steps/SynthesisStep";
import TribunalStep from "./steps/TribunalStep";
import ReportStep from "./steps/ReportStep";

const STEPS = ["Intake", "Fan-out", "Synthesis", "Tribunal", "Report"];

export default function Wizard({
  state,
  clientName,
  client,
  vendors = {},
  weaveProject,
  onReset,
}: {
  state: EngagementState;
  clientName?: string;
  client?: any;
  vendors?: Record<string, any>;
  weaveProject?: string;
  onReset: () => void;
}) {
  const [view, setView] = useState(0);

  // which steps have enough data to advance past
  const ready = useMemo(
    () => [
      !!state.requirements,
      ["vendor", "roi", "prioritizer"].every((n) => state.agents[n]?.status === "done"),
      state.agents.synthesis?.status === "done" || !!state.proposal,
      state.done,
      state.done && !!state.proposal,
    ],
    [state]
  );

  // No auto-advance: the engagement streams in the background; the view only
  // changes when the user clicks Next/Back or a reachable progress dot.
  const go = (i: number) => setView(i);

  // Show the FINAL recommendation: repaired proposal wins over the original
  // (flawed) Vendor pick, so the context bar stays consistent with the report.
  const finalVendorId =
    state.repairedProposal?.recommended_vendor_id ||
    state.proposal?.recommended_vendor_id;
  const vendorLabel =
    (finalVendorId && vendors[finalVendorId]?.name) ||
    (state.agents.vendor?.result?.vendor_name as string | undefined);

  return (
    <div className="mx-auto max-w-5xl px-6 pb-24 pt-6">
      {/* context bar */}
      <div className="sticky top-0 z-20 -mx-6 mb-8 border-b border-line bg-canvas/85 px-6 py-3 backdrop-blur">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
          <button onClick={onReset} className="kicker hover:text-oxblood">
            ← New
          </button>
          <Ctx label="Client" value={state.requirements?.client_name || clientName} />
          <Ctx
            label="Budget"
            value={state.requirements?.budget_usd ? fmtUsd(state.requirements.budget_usd) : undefined}
          />
          {vendorLabel && <Ctx label="Recommendation" value={vendorLabel} />}
          <div className="ml-auto flex items-center gap-2 font-mono text-[12px] text-muted">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                state.cost?.over_budget ? "bg-bad" : "bg-good"
              }`}
            />
            {fmtTokens(state.cost?.total_tokens)} tok · {fmtUsd(state.cost?.total_usd)}
          </div>
        </div>
      </div>

      {/* progress dots */}
      <div className="mb-10 flex items-center gap-3">
        {STEPS.map((s, i) => {
          const reachable = i === 0 || ready[i - 1];
          return (
            <button
              key={s}
              disabled={!reachable}
              onClick={() => reachable && go(i)}
              className="group flex items-center gap-2"
            >
              <span
                className={`h-2 w-2 rounded-full transition ${
                  i === view
                    ? "scale-150 bg-oxblood"
                    : i < view || ready[i]
                    ? "bg-ink"
                    : "bg-line"
                }`}
              />
              <span
                className={`font-mono text-[11px] uppercase tracking-kicker transition ${
                  i === view ? "text-ink" : "text-muted"
                } ${reachable ? "group-hover:text-oxblood" : "opacity-40"}`}
              >
                {s}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-5 bg-line" />}
            </button>
          );
        })}
      </div>

      {state.error && (
        <div className="mb-6 rounded-lg border border-bad/40 bg-bad/5 px-4 py-3 text-sm text-bad">
          {state.error}
        </div>
      )}

      {/* current step */}
      <div className="min-h-[420px]">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, x: 18 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -18 }}
            transition={{ duration: 0.28 }}
          >
            {view === 0 && <IntakeStep state={state} client={client} />}
            {view === 1 && <FanoutStep state={state} />}
            {view === 2 && <SynthesisStep state={state} />}
            {view === 3 && <TribunalStep state={state} vendors={vendors} />}
            {view === 4 && (
              <ReportStep state={state} client={client} weaveProject={weaveProject} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* nav */}
      <div className="mt-12 flex items-center justify-between border-t border-line pt-6">
        <button
          disabled={view === 0}
          onClick={() => go(view - 1)}
          className={`text-sm transition ${
            view === 0 ? "invisible" : "text-muted hover:text-ink"
          }`}
        >
          ← Back
        </button>

        {view < STEPS.length - 1 ? (
          <NextButton ready={ready[view]} label={STEPS[view + 1]} onClick={() => go(view + 1)} />
        ) : (
          <span className="font-mono text-[11px] uppercase tracking-kicker text-muted">
            Engagement complete
          </span>
        )}
      </div>
    </div>
  );
}

function Ctx({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="flex items-baseline gap-2">
      <span className="font-mono text-[10px] uppercase tracking-kicker text-muted">{label}</span>
      <span className="font-medium text-ink">{value}</span>
    </div>
  );
}

function NextButton({
  ready,
  label,
  onClick,
}: {
  ready: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      disabled={!ready}
      onClick={onClick}
      className={`group inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition ${
        ready
          ? "bg-ink text-canvas hover:bg-oxblood"
          : "cursor-wait bg-line text-muted"
      }`}
    >
      {ready ? (
        <>
          Next · {label}
          <span className="transition-transform group-hover:translate-x-0.5">→</span>
        </>
      ) : (
        <>
          <motion.span
            className="h-1.5 w-1.5 rounded-full bg-muted"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
          working…
        </>
      )}
    </button>
  );
}
