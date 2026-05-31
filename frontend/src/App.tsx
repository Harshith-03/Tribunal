import { useEffect, useState } from "react";
import { fetchClient, fetchClients, fetchConfig, fetchVendors } from "./api";
import { useEngagement } from "./useEngagement";
import type { ClientSummary } from "./types";
import Landing from "./components/Landing";
import Wizard from "./components/Wizard";

export default function App() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [selected, setSelected] = useState<string>();
  const [client, setClient] = useState<any>();
  const [cfg, setCfg] = useState<any>();
  const [vendors, setVendors] = useState<Record<string, any>>({});
  const { state, run, reset } = useEngagement();

  useEffect(() => {
    fetchClients().then(setClients).catch(() => {});
    fetchConfig().then(setCfg).catch(() => {});
    fetchVendors()
      .then((vs) => setVendors(Object.fromEntries(vs.map((v) => [v.id, v]))))
      .catch(() => {});
  }, []);

  const started = !!state.engagementId;

  const begin = async () => {
    if (!selected) return;
    fetchClient(selected).then(setClient).catch(() => {});
    run(selected);
  };

  return (
    <div className="min-h-full">
      {/* top brand strip */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="font-mono text-[12px] uppercase tracking-kicker text-ink">
          ConsultIQ <span className="text-muted">×</span>{" "}
          <span className="text-oxblood">Tribunal</span>
        </div>
        {cfg && (
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-kicker text-muted">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                cfg.mock_inference ? "bg-warn" : "bg-good"
              }`}
            />
            {cfg.mock_inference ? "mock" : "live"} · W&B
          </div>
        )}
      </div>

      {!started ? (
        <Landing
          clients={clients}
          selected={selected}
          onSelect={setSelected}
          onRun={begin}
          running={state.running}
        />
      ) : (
        <Wizard
          state={state}
          clientName={client?.name || clients.find((c) => c.id === selected)?.name}
          client={client}
          vendors={vendors}
          weaveProject={cfg?.project}
          onReset={() => {
            reset();
            setClient(undefined);
          }}
        />
      )}
    </div>
  );
}
