// shared agent colors + helpers used across panels (editorial palette)

export const AGENT_COLOR: Record<string, string> = {
  intake: "#7B2D26", // oxblood
  vendor: "#0F6E63", // teal
  roi: "#B7791F", // gold
  prioritizer: "#5A6B3B", // olive
  synthesis: "#6B4E71", // plum
  judge: "#2D5566", // slate-teal
  conviction: "#A1322B", // signal red
};

export function agentColor(name: string): string {
  return AGENT_COLOR[name] || "#8A8174";
}

export function fmtUsd(n?: number): string {
  if (n == null) return "$0";
  if (n >= 1000) return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (n >= 1) return "$" + n.toFixed(2);
  return "$" + n.toFixed(4);
}

export function fmtTokens(n?: number): string {
  if (n == null) return "0";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

// heatmap color on a light canvas: 0 (clay) -> 1 (green), white text reads on both
export function scoreColor(score: number): string {
  const s = Math.max(0, Math.min(1, score));
  const hue = 12 + s * 138; // 12=clay-red, 150=green
  const sat = 42 - s * 6;
  const light = 46 - s * 6;
  return `hsl(${hue}, ${sat}%, ${light}%)`;
}
