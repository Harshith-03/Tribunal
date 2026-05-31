import type { Conviction, IntakeDocument, ProposalObject } from "./types";

const AGENT_LABEL: Record<string, string> = {
  intake: "Intake",
  vendor: "Vendor / Compliance",
  roi: "ROI / Cost",
  prioritizer: "Use-case Prioritizer",
  synthesis: "Synthesis",
};

function esc(s: any): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function fmtUsd(n?: number): string {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString();
}

const DOC_CSS = `
  @page { margin: 22mm 20mm; }
  * { box-sizing: border-box; }
  body { font-family: "Inter", system-ui, sans-serif; color: #1A1714; line-height: 1.6; font-size: 11.5pt; margin: 0; }
  .kicker { font-family: "JetBrains Mono", monospace; font-size: 8.5pt; letter-spacing: .18em; text-transform: uppercase; color: #8A8174; }
  h1 { font-family: "Fraunces", serif; font-weight: 500; font-size: 28pt; line-height: 1.1; margin: 8px 0 0; }
  .cover { padding: 36px 0 24px; border-bottom: 2px solid #1A1714; margin-bottom: 24px; }
  .cover .meta { display:flex; gap:32px; margin-top: 20px; flex-wrap: wrap; }
  .cover .meta span { display:block; }
  .block-title { font-family:"JetBrains Mono",monospace; font-size:9pt; letter-spacing:.18em; text-transform:uppercase; color:#7B2D26; margin: 30px 0 10px; }
  ol, ul { margin: 0; padding-left: 20px; }
  li { margin: 4px 0; color:#3D362F; }
  .grid { display:grid; grid-template-columns: 150px 1fr; gap: 8px 16px; }
  .grid .k { font-family:"JetBrains Mono",monospace; font-size:8.5pt; text-transform:uppercase; letter-spacing:.08em; color:#8A8174; padding-top: 3px; }
  .grid .v { color:#3D362F; }
  .foot { margin-top: 32px; padding-top: 12px; border-top: 2px solid #1A1714; font-family:"JetBrains Mono",monospace; font-size: 8pt; letter-spacing:.12em; text-transform:uppercase; color:#8A8174; }
`;
const FONTS = `<link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />`;

function printWindow(html: string) {
  const w = window.open("", "_blank");
  if (!w) {
    alert("Please allow pop-ups to download the document.");
    return;
  }
  w.document.write(html);
  w.document.close();
  w.onload = () => setTimeout(() => w.print(), 400);
}

/** Intake record: meeting minutes + detailed intake form, as its own document. */
export function openIntakeDocument(doc: IntakeDocument, client: any) {
  const li = (arr: string[]) => arr.map((x) => `<li>${esc(x)}</li>`).join("");
  const html = `<!doctype html><html><head><meta charset="utf-8" />
  <title>Intake Record — ${esc(doc.client_name)}</title>${FONTS}
  <style>${DOC_CSS}</style></head><body>
    <div class="cover">
      <div class="kicker">ConsultIQ · Client Intake Record</div>
      <h1>${esc(doc.client_name)}</h1>
      <div class="meta">
        <div><span class="kicker">Date</span><b>${esc(doc.date)}</b></div>
        <div><span class="kicker">Industry</span><b>${esc(client?.industry || "")}</b></div>
        <div><span class="kicker">Attendees</span><b>${esc(doc.attendees.join(", "))}</b></div>
      </div>
    </div>

    <div class="block-title">Meeting minutes</div>
    <ol>${li(doc.meeting_minutes)}</ol>

    <div class="block-title">Intake form</div>
    <div class="grid">
      <div class="k">Main pain points</div><div class="v"><ul>${li(doc.pain_points)}</ul></div>
      <div class="k">Current state</div><div class="v">${esc(doc.current_state)}</div>
      <div class="k">Desired outcomes</div><div class="v"><ul>${li(doc.desired_outcomes)}</ul></div>
      <div class="k">Success metrics</div><div class="v"><ul>${li(doc.success_metrics)}</ul></div>
      <div class="k">Constraints noted</div><div class="v">${
        doc.constraints_noted.length ? `<ul>${li(doc.constraints_noted)}</ul>` : "<i>None formally logged this session.</i>"
      }</div>
      <div class="k">Budget</div><div class="v">${esc(doc.budget_note)}</div>
      <div class="k">Stakeholders</div><div class="v">${esc(doc.stakeholders.join(", ") || "TBD")}</div>
    </div>

    <div class="foot">ConsultIQ × Tribunal · Intake Record · Confidential</div>
  </body></html>`;
  printWindow(html);
}

/** Build a self-contained, print-optimized consulting report and open it for
 *  print-to-PDF in a new window. */
export function openReport(
  proposal: ProposalObject,
  client: any,
  convictions: Conviction[]
) {
  const today = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const order = proposal.section_order?.length
    ? proposal.section_order
    : Object.keys(proposal.sections || {});

  const sectionsHtml = order
    .map(
      (name, i) => `
      <section class="sec">
        <div class="sec-num">${String(i + 1).padStart(2, "0")}</div>
        <div>
          <h2>${esc(name)}</h2>
          <p>${esc(proposal.sections[name])}</p>
        </div>
      </section>`
    )
    .join("");

  const refsHtml = (proposal.references || [])
    .map(
      (r) => `
      <div class="ref">
        <div class="ref-cat">${esc(r.category)}</div>
        <div class="ref-body">
          <div class="ref-title">${
            r.url ? `<a href="${esc(r.url)}">${esc(r.title)}</a>` : esc(r.title)
          }</div>
          <div class="ref-note">${esc(r.note)}</div>
        </div>
      </div>`
    )
    .join("");

  const convHtml = convictions.length
    ? convictions
        .map(
          (c) => `
        <div class="conv">
          <div class="conv-dim">${esc(c.dimension)} — attributed to ${esc(c.stage)}</div>
          <p>${esc(c.reasoning)}</p>
        </div>`
        )
        .join("")
    : `<p class="muted">No verifiable failures: this deliverable passed every hard check on first pass.</p>`;

  const provHtml = (proposal.claims || [])
    .map(
      (cl) => `
      <tr>
        <td class="prov-agent">${esc(AGENT_LABEL[cl.origin_agent] || cl.origin_agent)}</td>
        <td>${esc(cl.text)}</td>
      </tr>`
    )
    .join("");

  const html = `<!doctype html><html><head><meta charset="utf-8" />
  <title>${esc(proposal.title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    @page { margin: 22mm 20mm; }
    * { box-sizing: border-box; }
    body { font-family: "Inter", system-ui, sans-serif; color: #1A1714; line-height: 1.6; font-size: 11.5pt; margin: 0; }
    .kicker { font-family: "JetBrains Mono", monospace; font-size: 8.5pt; letter-spacing: .18em; text-transform: uppercase; color: #8A8174; }
    h1 { font-family: "Fraunces", serif; font-weight: 500; font-size: 30pt; line-height: 1.1; margin: 8px 0 0; }
    h2 { font-family: "Fraunces", serif; font-weight: 500; font-size: 16pt; margin: 0 0 6px; }
    .cover { padding: 40px 0 28px; border-bottom: 2px solid #1A1714; margin-bottom: 28px; }
    .cover .meta { display:flex; gap:32px; margin-top: 22px; }
    .cover .meta div span { display:block; }
    .lead { font-family: "Fraunces", serif; font-size: 14pt; line-height: 1.45; }
    .sec { display: grid; grid-template-columns: 44px 1fr; gap: 14px; padding: 16px 0; border-top: 1px solid #E2DCD1; break-inside: avoid; }
    .sec-num { font-family: "JetBrains Mono", monospace; color: #7B2D26; font-size: 12pt; }
    .sec p { margin: 0; color: #3D362F; }
    .block-title { font-family:"JetBrains Mono",monospace; font-size:9pt; letter-spacing:.18em; text-transform:uppercase; color:#8A8174; margin: 34px 0 10px; }
    .ref { display:grid; grid-template-columns: 130px 1fr; gap: 12px; padding: 9px 0; border-top: 1px solid #E2DCD1; break-inside: avoid; }
    .ref-cat { font-family:"JetBrains Mono",monospace; font-size:8.5pt; text-transform:uppercase; letter-spacing:.1em; color:#8A8174; }
    .ref-title { font-weight: 600; }
    .ref-title a { color: #7B2D26; }
    .ref-note { color:#3D362F; font-size: 10.5pt; }
    .conv { border-left: 2px solid #7B2D26; padding-left: 12px; margin: 10px 0; break-inside: avoid; }
    .conv-dim { font-family:"JetBrains Mono",monospace; font-size:9pt; text-transform:uppercase; letter-spacing:.1em; color:#7B2D26; }
    .conv p { margin: 4px 0 0; color:#3D362F; font-size: 10.5pt; }
    table { width:100%; border-collapse: collapse; font-size: 10pt; }
    td { padding: 7px 8px; border-top: 1px solid #E2DCD1; vertical-align: top; color:#3D362F; }
    .prov-agent { font-family:"JetBrains Mono",monospace; font-size:8.5pt; text-transform:uppercase; letter-spacing:.08em; color:#1A1714; white-space:nowrap; width: 150px; }
    .muted { color:#8A8174; }
    .foot { margin-top: 34px; padding-top: 12px; border-top: 2px solid #1A1714; font-family:"JetBrains Mono",monospace; font-size: 8pt; letter-spacing:.12em; text-transform:uppercase; color:#8A8174; display:flex; justify-content:space-between; }
  </style></head>
  <body>
    <div class="cover">
      <div class="kicker">ConsultIQ × Tribunal · AI Strategy Engagement</div>
      <h1>${esc(proposal.title)}</h1>
      <div class="meta">
        <div><span class="kicker">Prepared for</span><b>${esc(client?.name || proposal.client_id)}</b></div>
        <div><span class="kicker">Date</span><b>${esc(today)}</b></div>
        <div><span class="kicker">Year-one investment</span><b>${fmtUsd(proposal.estimated_cost_usd)}</b></div>
      </div>
    </div>

    <div class="block-title">Executive summary</div>
    <p class="lead">${esc(proposal.executive_summary)}</p>

    ${sectionsHtml}

    <div class="block-title">References &amp; compliance</div>
    ${refsHtml || '<p class="muted">No external references cited.</p>'}

    <div class="block-title">Accountability appendix — Tribunal findings</div>
    ${convHtml}

    <div class="block-title">Provenance — every claim, by author</div>
    <table><tbody>${provHtml}</tbody></table>

    <div class="foot"><span>ConsultIQ × Tribunal</span><span>Confidential — prepared for ${esc(client?.name || "")}</span></div>
  </body></html>`;

  printWindow(html);
}
