import type { ClientSummary, SSEEvent } from "./types";

// In dev, vite proxies /api -> http://localhost:8000
const API = "/api";

export async function fetchClients(): Promise<ClientSummary[]> {
  const r = await fetch(`${API}/clients`);
  return r.json();
}

export async function fetchClient(id: string): Promise<any> {
  const r = await fetch(`${API}/clients/${id}`);
  return r.json();
}

export async function fetchConfig(): Promise<any> {
  const r = await fetch(`${API}/config`);
  return r.json();
}

export async function fetchVendors(): Promise<any[]> {
  const r = await fetch(`${API}/vendors`);
  return r.json();
}

export async function startEngagement(clientId: string): Promise<string> {
  const r = await fetch(`${API}/engagement`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId }),
  });
  const data = await r.json();
  return data.engagement_id;
}

/** Open the SSE stream; calls onEvent for each event, onClose at the end. */
export function streamEngagement(
  engagementId: string,
  onEvent: (e: SSEEvent) => void,
  onClose?: () => void
): () => void {
  const es = new EventSource(`${API}/engagement/${engagementId}/stream`);
  es.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data) as SSEEvent;
      onEvent(data);
      if (data.type === "complete" || data.type === "error") {
        es.close();
        onClose?.();
      }
    } catch {
      /* ignore keep-alive comments */
    }
  };
  es.onerror = () => {
    es.close();
    onClose?.();
  };
  return () => es.close();
}
