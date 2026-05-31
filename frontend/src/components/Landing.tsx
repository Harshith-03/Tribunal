import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ClientSummary } from "../types";
import { fmtUsd } from "../theme";

export default function Landing({
  clients,
  selected,
  onSelect,
  onRun,
  onRunCustom,
  running,
}: {
  clients: ClientSummary[];
  selected?: string;
  onSelect: (id: string) => void;
  onRun: () => void;
  onRunCustom: (form: { name: string; brief: string; file?: File | null }) => void;
  running: boolean;
}) {
  const [mode, setMode] = useState<"preset" | "upload">("preset");
  const [name, setName] = useState("");
  const [brief, setBrief] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const onPick = (f: File | null) => {
    setFile(f);
    if (f && /\.(txt|md|markdown)$/i.test(f.name)) {
      f.text().then((t) => setBrief(t)); // show text inline for plain files
    }
  };

  const canUpload = !!(brief.trim() || file);

  return (
    <div className="mx-auto max-w-5xl px-6 pt-16">
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
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

      {/* mode switch */}
      <div className="mt-12 flex items-center gap-6">
        <Tab active={mode === "preset"} onClick={() => setMode("preset")}>
          Walk in as a client
        </Tab>
        <Tab active={mode === "upload"} onClick={() => setMode("upload")}>
          Bring your own brief
        </Tab>
      </div>

      <AnimatePresence mode="wait">
        {mode === "preset" ? (
          <motion.div
            key="preset"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-5"
          >
            <div className="grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-3">
              {clients.map((c, i) => {
                const active = c.id === selected;
                return (
                  <motion.button
                    key={c.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.05 + i * 0.06 }}
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

            <div className="mt-8">
              <BeginButton
                disabled={!selected || running}
                running={running}
                onClick={onRun}
              />
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-5 rounded-xl border border-line bg-paper/60 p-6"
          >
            <p className="max-w-xl text-sm leading-relaxed text-soft">
              Paste a client brief or drop a file. We’ll read it, extract the needs,
              budget, and constraints, then run the full engagement — Tribunal included.
            </p>

            <div className="mt-5 grid gap-4 md:grid-cols-[1fr_220px]">
              <div>
                <label className="kicker">Brief</label>
                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  rows={7}
                  placeholder="e.g. We're a mid-size logistics firm. We want AI for route optimization and demand forecasting. All data must stay in the EU. Budget is $900k…"
                  className="mt-1 w-full resize-none rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink outline-none focus:border-oxblood"
                />
              </div>

              <div className="space-y-4">
                <div>
                  <label className="kicker">Client name</label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Acme Corp"
                    className="mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink outline-none focus:border-oxblood"
                  />
                </div>
                <div>
                  <label className="kicker">Or a file</label>
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="mt-1 w-full rounded-lg border border-dashed border-line px-3 py-3 text-left text-sm text-muted transition hover:border-oxblood hover:text-ink"
                  >
                    {file ? `📄 ${file.name}` : "Choose .txt / .md / .pdf"}
                  </button>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.md,.markdown,.pdf"
                    className="hidden"
                    onChange={(e) => onPick(e.target.files?.[0] ?? null)}
                  />
                </div>
              </div>
            </div>

            <div className="mt-6">
              <BeginButton
                disabled={!canUpload || running}
                running={running}
                label="Run my brief"
                onClick={() =>
                  onRunCustom({
                    name: name || (file ? file.name.replace(/\.[^.]+$/, "") : "Uploaded Client"),
                    brief,
                    file: file && /\.pdf$/i.test(file.name) ? file : null,
                  })
                }
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Tab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative pb-1 font-mono text-[11px] uppercase tracking-kicker transition ${
        active ? "text-ink" : "text-muted hover:text-ink"
      }`}
    >
      {children}
      {active && (
        <motion.span layoutId="tab-underline" className="absolute -bottom-px left-0 h-0.5 w-full bg-oxblood" />
      )}
    </button>
  );
}

function BeginButton({
  disabled,
  running,
  onClick,
  label = "Begin engagement",
}: {
  disabled: boolean;
  running: boolean;
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={`group inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium transition ${
        disabled ? "cursor-not-allowed bg-line text-muted" : "bg-ink text-canvas hover:bg-oxblood"
      }`}
    >
      {running ? "Engaging…" : label}
      <span className="transition-transform group-hover:translate-x-0.5">→</span>
    </button>
  );
}
