import { motion } from "framer-motion";
import type { ClientSummary } from "../types";
import { fmtUsd } from "../theme";

export default function Landing({
  clients,
  selected,
  onSelect,
  onRun,
  running,
}: {
  clients: ClientSummary[];
  selected?: string;
  onSelect: (id: string) => void;
  onRun: () => void;
  running: boolean;
}) {
  return (
    <div className="mx-auto max-w-5xl px-6 pt-16">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="kicker">AI consulting · accountable by design</div>
        <h1 className="display mt-4 text-5xl md:text-6xl">
          Consulting you can
          <br />
          <span className="italic text-oxblood">trust</span> and{" "}
          <span className="italic text-teal">afford</span>.
        </h1>
        <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-soft">
          An agent workforce drafts the deliverable in minutes. Then the{" "}
          <b className="font-semibold text-ink">Tribunal</b> convicts any verifiable
          failure, traces it to the earliest responsible stage, and fixes it at the
          source — all under a hard budget.
        </p>
      </motion.div>

      <div className="mt-12">
        <div className="kicker mb-4">Walk in as a client</div>
        <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-3">
          {clients.map((c, i) => {
            const active = c.id === selected;
            return (
              <motion.button
                key={c.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.07 }}
                onClick={() => onSelect(c.id)}
                className={`group relative bg-canvas p-6 text-left transition ${
                  active ? "bg-paper" : "hover:bg-paper"
                }`}
              >
                <div
                  className={`absolute left-0 top-0 h-full w-[3px] origin-top bg-oxblood transition-transform ${
                    active ? "scale-y-100" : "scale-y-0 group-hover:scale-y-100"
                  }`}
                />
                <div className="flex items-start justify-between">
                  <div className="kicker">{c.industry}</div>
                  {c.is_trap && (
                    <span className="font-mono text-[10px] uppercase tracking-widest text-oxblood">
                      trap
                    </span>
                  )}
                </div>
                <div className="display mt-3 text-xl">{c.name}</div>
                <div className="mt-4 flex items-baseline gap-2 text-sm text-muted">
                  <span className="font-mono text-ink">{fmtUsd(c.budget_usd)}</span>
                  <span>budget · {c.size}</span>
                </div>
              </motion.button>
            );
          })}
        </div>

        <div className="mt-8 flex items-center gap-4">
          <button
            disabled={!selected || running}
            onClick={onRun}
            className={`group inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium transition ${
              !selected || running
                ? "cursor-not-allowed bg-line text-muted"
                : "bg-ink text-canvas hover:bg-oxblood"
            }`}
          >
            {running ? "Engaging…" : "Begin engagement"}
            <span className="transition-transform group-hover:translate-x-0.5">→</span>
          </button>
          {selected && !running && (
            <span className="text-sm text-muted">
              You’ll see every stage, live.
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
