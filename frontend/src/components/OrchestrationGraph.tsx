import type { AgentState } from "../types";
import { agentColor } from "../theme";

/** Static 2D diagram of the REAL orchestration:
 *   Intake feeds all three specialists; Vendor feeds ROI (ROI prices the chosen
 *   vendor); all three feed Synthesis. No animated particles — just structure. */
const N: Record<string, { x: number; y: number; label: string }> = {
  intake: { x: 180, y: 46, label: "Intake" },
  vendor: { x: 66, y: 170, label: "Vendor" },
  roi: { x: 180, y: 170, label: "ROI" },
  prioritizer: { x: 294, y: 170, label: "Priority" },
  synthesis: { x: 180, y: 296, label: "Synthesis" },
};

// directed edges that actually exist in the pipeline
const EDGES: [string, string][] = [
  ["intake", "vendor"],
  ["intake", "roi"],
  ["intake", "prioritizer"],
  ["vendor", "synthesis"],
  ["roi", "synthesis"],
  ["prioritizer", "synthesis"],
];

const R = 24;

export default function OrchestrationGraph({
  agents,
  synthesisActive,
}: {
  agents: Record<string, AgentState>;
  synthesisActive?: boolean;
}) {
  const status = (name: string) =>
    name === "intake"
      ? "done"
      : name === "synthesis"
      ? synthesisActive
        ? "running"
        : agents.synthesis?.status ?? "idle"
      : agents[name]?.status ?? "idle";

  return (
    <svg viewBox="0 0 360 340" className="w-full">
      {/* fan edges (top→bottom implies direction) */}
      {EDGES.map(([a, b], i) => (
        <line
          key={i}
          x1={N[a].x}
          y1={N[a].y}
          x2={N[b].x}
          y2={N[b].y}
          stroke="#D8D1C4"
          strokeWidth={1.5}
        />
      ))}

      {/* Vendor → ROI dependency, drawn between the two circles with an arrow */}
      <defs>
        <marker id="arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#A8584F" />
        </marker>
      </defs>
      <line
        x1={N.vendor.x + R + 2}
        y1={N.vendor.y}
        x2={N.roi.x - R - 6}
        y2={N.roi.y}
        stroke="#A8584F"
        strokeWidth={1.5}
        markerEnd="url(#arrow)"
      />

      {/* nodes */}
      {Object.entries(N).map(([name, n]) => {
        const st = status(name);
        const c = agentColor(name);
        const active = st === "done" || st === "running";
        return (
          <g key={name}>
            <circle
              cx={n.x}
              cy={n.y}
              r={R}
              fill={active ? c : "#FFFFFF"}
              stroke={c}
              strokeWidth={1.75}
              opacity={st === "idle" ? 0.5 : 1}
            />
            <text
              x={n.x}
              y={n.y + 3.5}
              textAnchor="middle"
              fontFamily="JetBrains Mono, monospace"
              fontSize="8.5"
              fill={active ? "#FFFFFF" : c}
            >
              {n.label.slice(0, 4).toUpperCase()}
            </text>
            <text
              x={n.x}
              y={n.y + R + 16}
              textAnchor="middle"
              fontFamily="Inter, sans-serif"
              fontSize="11"
              fill="#3D362F"
            >
              {n.label}
            </text>
          </g>
        );
      })}

      {/* tiny caption for the dependency */}
      <text
        x={123}
        y={150}
        textAnchor="middle"
        fontFamily="JetBrains Mono, monospace"
        fontSize="7.5"
        fill="#A8584F"
      >
        prices pick
      </text>
    </svg>
  );
}
