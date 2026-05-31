import { motion } from "framer-motion";
import type { EngagementState } from "../../useEngagement";
import { fmtUsd } from "../../theme";
import { openIntakeDocument } from "../../report";
import StepHeader from "./StepHeader";
import Collapsible from "../Collapsible";

export default function IntakeStep({
  state,
  client,
}: {
  state: EngagementState;
  client?: any;
}) {
  const req = state.requirements;
  const doc = req?.document;
  const painCount = doc?.pain_points.length ?? req?.needs.length ?? 0;
  const constraintCount = req?.hard_constraints.length ?? 0;

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <StepHeader
          stage="Stage 01 · Intake"
          title="The situation"
          dek="A meeting with the client, captured as minutes and a structured intake form."
        />
        {doc && (
          <button
            onClick={() => openIntakeDocument(doc, client)}
            className="group inline-flex items-center gap-2 rounded-full border border-ink px-4 py-2 text-sm font-medium text-ink transition hover:bg-ink hover:text-canvas"
          >
            Intake record
            <span className="transition-transform group-hover:translate-y-0.5">↓</span>
          </button>
        )}
      </div>

      {!req ? (
        <Loading label="Reading the brief…" />
      ) : (
        <>
          {/* numeric stat strip */}
          <div className="mb-8 grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-line bg-line">
            <Stat n={painCount} label="pain points" />
            <Stat n={fmtUsd(req.budget_usd)} label="first-year budget" />
            <Stat
              n={constraintCount}
              label="hard constraints"
              alert={constraintCount === 0}
            />
          </div>

          <div className="grid gap-10 md:grid-cols-[1.4fr_1fr]">
            <div>
              <p className="font-display text-[1.3rem] leading-snug text-ink">{req.summary}</p>

              <div className="mt-7">
                <div className="kicker mb-3">Main pain points</div>
                <ul className="space-y-1.5">
                  {(doc?.pain_points ?? req.needs).map((n, i) => (
                    <motion.li
                      key={i}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="flex gap-3 text-[15px] text-ink"
                    >
                      <span className="font-mono text-xs text-oxblood">{String(i + 1).padStart(2, "0")}</span>
                      {n}
                    </motion.li>
                  ))}
                </ul>
              </div>

              {client?.raw_brief && (
                <div className="mt-7">
                  <Collapsible label="Original client brief">
                    <p className="text-sm italic leading-relaxed text-soft">“{client.raw_brief}”</p>
                  </Collapsible>
                  {doc && (
                    <Collapsible label="Meeting minutes">
                      <ol className="space-y-1.5">
                        {doc.meeting_minutes.map((m, i) => (
                          <li key={i} className="flex gap-2 text-sm text-soft">
                            <span className="font-mono text-xs text-muted">{i + 1}</span>
                            {m}
                          </li>
                        ))}
                      </ol>
                    </Collapsible>
                  )}
                </div>
              )}
            </div>

            {/* constraints rail */}
            <div className="md:border-l md:border-line md:pl-8">
              <div className="kicker mb-3">Hard constraints captured</div>
              {constraintCount === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-lg border border-oxblood/30 bg-oxblood/[0.04] p-4"
                >
                  <div className="font-display text-3xl text-oxblood">0</div>
                  <p className="mt-1 text-sm leading-relaxed text-soft">
                    None captured. If the brief contained any, the Tribunal will trace
                    the consequences back to <b>this</b> stage.
                  </p>
                </motion.div>
              ) : (
                <div className="space-y-2">
                  {req.hard_constraints.map((c, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="border-b border-line pb-2"
                    >
                      <div className="font-mono text-[10px] uppercase tracking-kicker text-muted">
                        {c.type}
                      </div>
                      <div className="font-medium text-ink">{c.value}</div>
                    </motion.div>
                  ))}
                </div>
              )}

              <div className="kicker mb-2 mt-7">Required reviewers</div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-soft">
                {req.required_stakeholders.map((s) => (
                  <span key={s}>{s}</span>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ n, label, alert }: { n: number | string; label: string; alert?: boolean }) {
  return (
    <div className="bg-canvas px-4 py-3">
      <div className={`font-display text-3xl ${alert ? "text-oxblood" : "text-ink"}`}>{n}</div>
      <div className="kicker mt-0.5">{label}</div>
    </div>
  );
}

function Loading({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-16 text-muted">
      <motion.span
        className="h-2 w-2 rounded-full bg-oxblood"
        animate={{ opacity: [1, 0.3, 1] }}
        transition={{ duration: 1, repeat: Infinity }}
      />
      <span className="font-mono text-sm">{label}</span>
    </div>
  );
}
