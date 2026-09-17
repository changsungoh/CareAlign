"use client";

import { useEffect, useMemo, useState } from "react";

type DocumentInput = { document_id: string; document_type: string; document_date: string; raw_text: string };
type Instruction = {
  instruction_id: string; document_id: string;
  medication: { raw_name: string; normalized_id: string | null };
  dose: { raw_value: string | null; raw_unit: string | null } | null;
  frequency: { raw_expression: string; pattern_type: string } | null;
  timing: { raw_expression: string | null } | null;
  evidence_span: string; validation_status: string;
};
type Conflict = {
  conflict_id: string; conflict_type: string; medication_name: string;
  instruction_ids: string[]; summary: string; clarification_question: string;
  status: string; confidence: number; evidence_spans: string[];
};
type Analysis = {
  case_id: string; status: string; documents: DocumentInput[];
  instructions: Instruction[]; conflicts: Conflict[];
  safety_message: string; demo_mode: boolean;
  metadata: {
    app_version: string; release_sha: string; request_id: string;
    model_name: string; prompt_version: string; rules_version: string;
    provider_calls: number; input_tokens: number; output_tokens: number;
    analysis_duration_ms: number;
  };
};
type Resolution = { conflictId: string; response: string; recordedAt: string };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function responseBody(response: Response): Promise<Record<string, unknown>> {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return { detail: "The analysis service returned an invalid response. No safety conclusion was produced." };
  }
  try {
    return await response.json() as Record<string, unknown>;
  } catch {
    return { detail: "The analysis service returned malformed JSON. No safety conclusion was produced." };
  }
}

function requestId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
const demoDocuments: DocumentInput[] = [
  {
    document_id: "aug-discharge", document_type: "Discharge instructions",
    document_date: "2026-08-20",
    raw_text: "Continue metoprolol tartrate 25 mg by mouth twice a day.\nContinue atorvastatin 20 mg by mouth once a day at bedtime.\nContinue lisinopril 10 mg by mouth once a day in the morning.",
  },
  {
    document_id: "sep-prescription", document_type: "Prescription list",
    document_date: "2026-09-10",
    raw_text: "Continue metoprolol tartrate 25 mg by mouth once a day.\nContinue lisinopril 10 mg by mouth once a day in the morning.",
  },
];

export default function Home() {
  const [documents, setDocuments] = useState<DocumentInput[]>(demoDocuments);
  const [consent, setConsent] = useState(false);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [resolutions, setResolutions] = useState<Resolution[]>([]);
  const [teachBack, setTeachBack] = useState("");
  const [teachResult, setTeachResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [slowStart, setSlowStart] = useState(false);
  const [error, setError] = useState("");
  const [largeText, setLargeText] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem("carealign-resolutions");
    if (stored) setResolutions(JSON.parse(stored));
  }, []);
  const unresolvedIds = useMemo(
    () => analysis?.conflicts.flatMap((item) => item.instruction_ids) ?? [], [analysis],
  );
  const documentsValid = useMemo(() => {
    const dates = documents.map((item) => item.document_date);
    return documents.every((item) => item.document_type.trim() && item.document_date && item.raw_text.trim())
      && new Set(dates).size === dates.length
      && dates.every((value, index) => index === 0 || dates[index - 1] < value);
  }, [documents]);
  const recordedConflictIds = useMemo(
    () => new Set(resolutions.map((item) => item.conflictId)), [resolutions],
  );
  const pendingConflicts = useMemo(
    () => analysis?.conflicts.filter((item) => !recordedConflictIds.has(item.conflict_id)) ?? [],
    [analysis, recordedConflictIds],
  );
  const recordedConflicts = useMemo(
    () => analysis?.conflicts.filter((item) => recordedConflictIds.has(item.conflict_id)) ?? [],
    [analysis, recordedConflictIds],
  );

  function updateDocument(index: number, key: keyof DocumentInput, value: string) {
    setDocuments((current) => current.map((document, itemIndex) =>
      itemIndex === index ? { ...document, [key]: value } : document));
  }

  function addDocument() {
    if (documents.length >= 5) return;
    const next = documents.length + 1;
    setDocuments((current) => [...current, {
      document_id: `document-${next}`,
      document_type: "Additional care record",
      document_date: "",
      raw_text: "",
    }]);
  }

  function removeDocument(index: number) {
    if (documents.length <= 2) return;
    setDocuments((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  async function analyze() {
    setBusy(true); setSlowStart(false); setError(""); setTeachResult(null);
    const slowStartTimer = window.setTimeout(() => setSlowStart(true), 5000);
    try {
      const correlationId = requestId();
      const response = await fetch(`${API}/api/analyze`, {
        method: "POST", headers: {
          "Content-Type": "application/json",
          "X-Request-ID": correlationId,
        },
        body: JSON.stringify({ documents }),
      });
      const body = await responseBody(response);
      if (!response.ok) {
        const returnedId = response.headers.get("X-Request-ID") ?? correlationId;
        const detail = typeof body.detail === "string" ? body.detail : "Analysis failed safely.";
        throw new Error(`${detail} Request ID: ${returnedId}`);
      }
      setAnalysis(body as unknown as Analysis);
      requestAnimationFrame(() => document.querySelector("#results")?.scrollIntoView());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Analysis failed safely.");
    } finally {
      window.clearTimeout(slowStartTimer);
      setSlowStart(false);
      setBusy(false);
    }
  }

  function recordResolution(conflict: Conflict, response: string) {
    if (!response.trim()) return;
    const next = [...resolutions.filter((item) => item.conflictId !== conflict.conflict_id),
      { conflictId: conflict.conflict_id, response: response.trim(), recordedAt: new Date().toISOString() }];
    setResolutions(next);
    sessionStorage.setItem("carealign-resolutions", JSON.stringify(next));
  }

  async function submitTeachBack() {
    if (!analysis || !teachBack.trim()) return;
    setBusy(true); setError("");
    try {
      const correlationId = requestId();
      const response = await fetch(`${API}/api/teach-back`, {
        method: "POST", headers: {
          "Content-Type": "application/json",
          "X-Request-ID": correlationId,
        },
        body: JSON.stringify({ instructions: analysis.instructions,
          excluded_instruction_ids: unresolvedIds, patient_response: teachBack }),
      });
      const body = await responseBody(response);
      if (!response.ok) {
        const returnedId = response.headers.get("X-Request-ID") ?? correlationId;
        const detail = typeof body.detail === "string" ? body.detail : "Teach-back check failed safely.";
        throw new Error(`${detail} Request ID: ${returnedId}`);
      }
      setTeachResult(typeof body.message === "string" ? body.message : "Teach-back completed.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Teach-back check failed safely.");
    } finally { setBusy(false); }
  }

  async function copyQuestions() {
    if (!analysis) return;
    await navigator.clipboard.writeText(
      pendingConflicts.map((item) => `• ${item.clarification_question}`).join("\n"));
  }
  function downloadSummary() {
    if (!analysis) return;
    const content = ["CareAlign clarification summary — research prototype, not medical advice",
      ...analysis.conflicts.map((item) => `\n${item.medication_name}: ${item.summary}\nQuestion: ${item.clarification_question}`)].join("\n");
    const url = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
    const anchor = document.createElement("a"); anchor.href = url;
    anchor.download = "carealign-questions.txt"; anchor.click(); URL.revokeObjectURL(url);
  }
  function clearAll() {
    sessionStorage.removeItem("carealign-resolutions"); setAnalysis(null); setResolutions([]);
    setTeachBack(""); setTeachResult(null);
  }

  return <main className={largeText ? "large-text" : ""}>
    <header className="nav-wrap"><div className="nav"><a className="brand" href="#top"><span className="logo-mark" aria-hidden="true">+</span><span>CareAlign<small>Care transition intelligence</small></span></a><div className="nav-actions">
      <span className="live-status"><i />Live system</span>
      <button className="quiet text-toggle" onClick={() => setLargeText((value) => !value)}>{largeText ? "Standard text" : "Large text"}</button>
      <span className="prototype-badge">Research prototype</span></div></div></header>
    <section className="hero" id="top"><div className="hero-copy"><div className="hero-label"><span className="pulse-dot" />AI-powered safety layer</div>
      <h1>Catch the mismatch.<br /><span>Clarify care.</span></h1>
      <p className="lede">CareAlign compares instructions across a patient&apos;s care journey, traces every potential conflict to its source, and turns uncertainty into the exact question to ask.</p>
      <div className="hero-proof"><div><strong>2–5</strong><span>records compared</span></div><div><strong>Source-linked</strong><span>evidence for every flag</span></div><div><strong>Human-first</strong><span>resolution by care teams</span></div></div>
      <aside className="warning"><span className="warning-icon" aria-hidden="true">!</span><div><h2>Decision support, not medical advice</h2><p>Never start, stop, or change medication based on this tool. Confirm every flag with a qualified healthcare professional.</p></div></aside>
    </div><div className="hero-visual" aria-label="CareAlign comparison workflow preview"><div className="visual-header"><span>CARE TIMELINE</span><span className="secured">Source secured</span></div>
      <div className="visual-documents"><article><span className="doc-icon">01</span><div><small>20 AUG 2026</small><strong>Discharge instructions</strong><p>Metoprolol tartrate · twice daily</p></div></article><div className="flow-line"><i /><i /><i /></div><article><span className="doc-icon">02</span><div><small>10 SEP 2026</small><strong>Prescription list</strong><p>Metoprolol tartrate · once daily</p></div></article></div>
      <div className="visual-alert"><div className="alert-symbol">!</div><div><small>POTENTIAL DIFFERENCE</small><strong>Frequency needs confirmation</strong><p>CareAlign found a source-verifiable change and prepared a question for the care team.</p></div><span className="confidence-pill">96%</span></div>
      <div className="visual-footer"><span><i />AI extracts meaning</span><span><i />Rules verify differences</span></div>
    </div></section>
    <section className="workspace" aria-labelledby="workspace-title">
      <div className="section-heading"><div><span className="section-number">01</span><p className="eyebrow">COMPARE RECORDS</p><h2 id="workspace-title">Build the care timeline</h2><p className="section-copy">Add records from oldest to newest. CareAlign compares meaning while deterministic rules control every safety flag.</p></div><div className="result-actions"><button className="quiet" onClick={() => setDocuments(demoDocuments)}>Load safe demo</button><button className="quiet" disabled={documents.length >= 5} onClick={addDocument}>+ Add document</button></div></div>
      <div className="privacy-banner"><span className="privacy-icon" aria-hidden="true">◇</span><div><strong>Synthetic data only</strong><span>Do not enter real patient data. Input is processed without server-side storage.</span></div></div>
      <div className="document-grid">{documents.map((document, index) => <article className="document-card" key={document.document_id}>
        <div className="conflict-top"><span className="step">Document {index + 1}</span>{documents.length > 2 && <button className="remove" onClick={() => removeDocument(index)} aria-label={`Remove document ${index + 1}`}>Remove</button>}</div>
        <label>Document type<input value={document.document_type} onChange={(event) => updateDocument(index, "document_type", event.target.value)} /></label>
        <label>Date<input type="date" value={document.document_date} onChange={(event) => updateDocument(index, "document_date", event.target.value)} /></label>
        <label>Instruction text<textarea maxLength={4000} rows={8} value={document.raw_text} onChange={(event) => updateDocument(index, "raw_text", event.target.value)} /></label><small>{document.raw_text.length}/4,000 characters</small>
      </article>)}</div>
      <label className="consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>I confirm this is synthetic data and understand CareAlign does not provide medical advice.</span></label>
      {!documentsValid && <p className="validation-hint">Every record needs a unique date and must appear from oldest to newest.</p>}
      <button className="primary analyze-button" disabled={!consent || !documentsValid || busy} onClick={analyze}>{busy ? "Checking safely…" : <>Analyze care timeline <span aria-hidden="true">→</span></>}</button>
      {slowStart && <p className="slow-start" role="status">The secure analysis server is starting. After inactivity, the first request may take up to 60 seconds.</p>}
      {error && <div className="error" role="alert">{error}</div>}
    </section>
    {analysis && <section className="results" id="results" aria-labelledby="results-title" aria-live="polite">
      <div className="section-heading results-heading"><div><span className="section-number">02</span><p className="eyebrow">SOURCE-LINKED RESULTS</p><h2 id="results-title">{analysis.conflicts.length === 0 ? "No rule-verifiable differences found" : pendingConflicts.length === 0 ? "Responses recorded for every difference" : `${pendingConflicts.length} difference${pendingConflicts.length === 1 ? "" : "s"} still need${pendingConflicts.length === 1 ? "s" : ""} a response`}</h2><p className="section-copy">CareAlign never decides which instruction is correct. Recording a response completes the follow-up step without marking the clinical flag as resolved.</p></div>{analysis.demo_mode && <span className="demo-badge">Demo mode · transparent parser</span>}</div>
      <p className="safety-line">{analysis.safety_message}</p>
      <ol className="timeline" aria-label="Document chronology">{analysis.documents.map((document) => <li key={document.document_id}><time>{document.document_date}</time><strong>{document.document_type}</strong><span>{document.document_id}</span></li>)}</ol>
      <div className="result-actions"><button disabled={pendingConflicts.length === 0} onClick={copyQuestions}>Copy open questions</button><button onClick={() => window.print()}>Print</button><button onClick={downloadSummary}>Download</button></div>
      {analysis.conflicts.length === 0 ? <div className="empty">No rule-verifiable differences were found. This is not a guarantee that the records are correct or complete.</div> : <>
        {pendingConflicts.map((conflict) => <ConflictCard key={conflict.conflict_id} conflict={conflict} onResolve={recordResolution} />)}
        {recordedConflicts.length > 0 && <section className="recorded-section" aria-labelledby="recorded-title"><div className="recorded-heading"><div><p className="eyebrow">FOLLOW-UP CAPTURED</p><h3 id="recorded-title">{recordedConflicts.length} response{recordedConflicts.length === 1 ? "" : "s"} recorded</h3></div><span>Not verified by CareAlign</span></div>
          {recordedConflicts.map((conflict) => <ConflictCard key={conflict.conflict_id} conflict={conflict} resolution={resolutions.find((item) => item.conflictId === conflict.conflict_id)} onResolve={recordResolution} />)}
        </section>}
      </>}
      <section className="teachback" aria-labelledby="teach-title"><div className="teach-icon" aria-hidden="true">✓</div><p className="eyebrow">OPTIONAL TEACH-BACK</p><h2 id="teach-title">Explain the confirmed instructions in your own words</h2><p>Unresolved or uncertain instructions are excluded. This is a supportive review, not a test.</p>
        <textarea rows={4} value={teachBack} onChange={(event) => setTeachBack(event.target.value)} placeholder="Example: I will take lisinopril 10 mg once a day in the morning." />
        <div className="result-actions"><button className="primary" disabled={busy || !teachBack.trim()} onClick={submitTeachBack}>Check my explanation</button><button className="quiet" onClick={() => setTeachBack("")}>Skip teach-back</button></div>{teachResult && <div className="teach-result" role="status">{teachResult}</div>}
      </section><button className="danger-link" onClick={clearAll}>Clear all session data</button>
      <p className="metadata">App: {analysis.metadata.app_version} · Release: {analysis.metadata.release_sha.slice(0, 12)} · Model: {analysis.metadata.model_name} · Prompt: {analysis.metadata.prompt_version} · Rules: {analysis.metadata.rules_version}<br />Request: {analysis.metadata.request_id} · Provider calls: {analysis.metadata.provider_calls} · Tokens: {analysis.metadata.input_tokens.toLocaleString()} in / {analysis.metadata.output_tokens.toLocaleString()} out · {Math.round(analysis.metadata.analysis_duration_ms)} ms</p>
    </section>}
    <section className="principles"><div className="principles-heading"><p className="eyebrow">A DELIBERATE SAFETY ARCHITECTURE</p><h2>AI for meaning.<br /><span>Rules for safety.</span></h2><p>Intelligence where language is ambiguous. Determinism where patient safety demands consistency.</p></div><div className="principle-grid"><article><span>01</span><h3>Semantic extraction</h3><p>AI translates differently worded instructions into a strict, source-bound structure.</p></article><article><span>02</span><h3>Deterministic comparison</h3><p>Auditable code checks dose, frequency, route, action, and possible omissions.</p></article><article><span>03</span><h3>Human resolution</h3><p>CareAlign asks a question; only a person records the care team&apos;s answer.</p></article></div></section>
    <footer><div className="footer-brand"><span className="logo-mark" aria-hidden="true">+</span><div><strong>CareAlign</strong><span>Safer transitions through clearer instructions.</span></div></div><p><strong>Decision-support prototype only.</strong> Not clinically validated, HIPAA compliant, diagnostic, prescriptive, or cleared as a medical device.</p></footer>
  </main>;
}

function ConflictCard({ conflict, resolution, onResolve }: { conflict: Conflict; resolution?: Resolution; onResolve: (conflict: Conflict, response: string) => void }) {
  const [response, setResponse] = useState(resolution?.response ?? "");
  const [editing, setEditing] = useState(!resolution);
  function saveResponse() { onResolve(conflict, response); if (response.trim()) setEditing(false); }
  return <article className={`conflict-card${resolution && !editing ? " recorded-card" : ""}`}><div className="conflict-top"><span className="conflict-type">{conflict.conflict_type.replaceAll("_", " ")}</span>{resolution && !editing ? <span className="recorded-status">Response recorded</span> : <span className="confidence-score"><i><b style={{ width: `${Math.round(conflict.confidence * 100)}%` }} /></i>{Math.round(conflict.confidence * 100)}% rule confidence</span>}</div>
    <h3>{conflict.medication_name}</h3><p>{conflict.summary}</p>
    {resolution && !editing ? <div className="recorded-response"><strong>Recorded care-team response</strong><p>{resolution.response}</p><small>User-entered · not verified by CareAlign · {new Date(resolution.recordedAt).toLocaleString()}</small><button className="edit-response" onClick={() => setEditing(true)}>Edit response</button></div> : <>
      <blockquote>{conflict.evidence_spans.map((span) => <span key={span}>“{span}”</span>)}</blockquote>
      <div className="question"><strong>Ask your care team</strong><p>{conflict.clarification_question}</p></div>
      <label>Record care team response <span className="unverified">User-entered · not verified by CareAlign</span><textarea rows={2} value={response} onChange={(event) => setResponse(event.target.value)} /></label>
      <button disabled={!response.trim()} onClick={saveResponse}>{resolution ? "Update recorded response" : "Save to this browser session"}</button>
    </>}
  </article>;
}
