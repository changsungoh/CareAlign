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
  metadata: { model_name: string; prompt_version: string; rules_version: string };
};
type Resolution = { conflictId: string; response: string; recordedAt: string };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
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
    setBusy(true); setError(""); setTeachResult(null);
    try {
      const response = await fetch(`${API}/api/analyze`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ documents }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Analysis failed.");
      setAnalysis(body);
      requestAnimationFrame(() => document.querySelector("#results")?.scrollIntoView());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Analysis failed safely.");
    } finally { setBusy(false); }
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
      const response = await fetch(`${API}/api/teach-back`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instructions: analysis.instructions,
          excluded_instruction_ids: unresolvedIds, patient_response: teachBack }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Teach-back check failed.");
      setTeachResult(body.message);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Teach-back check failed safely.");
    } finally { setBusy(false); }
  }

  async function copyQuestions() {
    if (!analysis) return;
    await navigator.clipboard.writeText(
      analysis.conflicts.map((item) => `• ${item.clarification_question}`).join("\n"));
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
    <header className="nav"><a className="brand" href="#top">CareAlign</a><div className="nav-actions">
      <button className="quiet" onClick={() => setLargeText((value) => !value)}>{largeText ? "Standard text" : "Large text"}</button>
      <span className="prototype-badge">Research prototype</span></div></header>
    <section className="hero" id="top"><p className="eyebrow">AI FOR SAFER CARE TRANSITIONS</p>
      <h1>Find the mismatch before it becomes a medication mistake.</h1>
      <p className="lede">CareAlign reads differently worded care instructions, applies deterministic safety rules, traces every flag to its source, and prepares the exact question a patient should ask.</p>
      <aside className="warning"><h2>Research prototype — not medical advice</h2><p>Never start, stop, or change medication based on this tool. CareAlign cannot decide which instruction is correct. Confirm every flag with a qualified healthcare professional.</p></aside>
    </section>
    <section className="workspace" aria-labelledby="workspace-title">
      <div className="section-heading"><div><p className="eyebrow">SYNTHETIC DEMO · 2–5 RECORDS</p><h2 id="workspace-title">Compare a care timeline</h2></div><div className="result-actions"><button className="quiet" onClick={() => setDocuments(demoDocuments)}>Load safe demo</button><button className="quiet" disabled={documents.length >= 5} onClick={addDocument}>Add document</button></div></div>
      <div className="privacy-banner"><strong>Do not enter real patient data.</strong> Use synthetic, de-identified demonstration text only. Input is not stored by the server.</div>
      <div className="document-grid">{documents.map((document, index) => <article className="document-card" key={document.document_id}>
        <div className="conflict-top"><span className="step">Document {index + 1}</span>{documents.length > 2 && <button className="remove" onClick={() => removeDocument(index)} aria-label={`Remove document ${index + 1}`}>Remove</button>}</div>
        <label>Document type<input value={document.document_type} onChange={(event) => updateDocument(index, "document_type", event.target.value)} /></label>
        <label>Date<input type="date" value={document.document_date} onChange={(event) => updateDocument(index, "document_date", event.target.value)} /></label>
        <label>Instruction text<textarea maxLength={4000} rows={8} value={document.raw_text} onChange={(event) => updateDocument(index, "raw_text", event.target.value)} /></label><small>{document.raw_text.length}/4,000 characters</small>
      </article>)}</div>
      <label className="consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> I confirm this is synthetic data and understand CareAlign does not provide medical advice.</label>
      {!documentsValid && <p className="validation-hint">Every record needs a unique date and must appear from oldest to newest.</p>}
      <button className="primary" disabled={!consent || !documentsValid || busy} onClick={analyze}>{busy ? "Checking safely…" : "Compare instructions"}</button>
      {error && <div className="error" role="alert">{error}</div>}
    </section>
    {analysis && <section className="results" id="results" aria-labelledby="results-title" aria-live="polite">
      <div className="section-heading"><div><p className="eyebrow">SOURCE-LINKED RESULTS</p><h2 id="results-title">{analysis.conflicts.length} potential difference{analysis.conflicts.length === 1 ? "" : "s"} to confirm</h2></div>{analysis.demo_mode && <span className="demo-badge">Demo mode · transparent parser</span>}</div>
      <p className="safety-line">{analysis.safety_message}</p>
      <ol className="timeline" aria-label="Document chronology">{analysis.documents.map((document) => <li key={document.document_id}><time>{document.document_date}</time><strong>{document.document_type}</strong><span>{document.document_id}</span></li>)}</ol>
      <div className="result-actions"><button onClick={copyQuestions}>Copy questions</button><button onClick={() => window.print()}>Print</button><button onClick={downloadSummary}>Download</button></div>
      {analysis.conflicts.length === 0 ? <div className="empty">No rule-verifiable differences were found. This is not a guarantee that the records are correct or complete.</div> : analysis.conflicts.map((conflict) => <ConflictCard key={conflict.conflict_id} conflict={conflict} resolution={resolutions.find((item) => item.conflictId === conflict.conflict_id)} onResolve={recordResolution} />)}
      <section className="teachback" aria-labelledby="teach-title"><p className="eyebrow">OPTIONAL TEACH-BACK</p><h2 id="teach-title">Explain the confirmed instructions in your own words</h2><p>Unresolved or uncertain instructions are excluded. This is a supportive review, not a test.</p>
        <textarea rows={4} value={teachBack} onChange={(event) => setTeachBack(event.target.value)} placeholder="Example: I will take lisinopril 10 mg once a day in the morning." />
        <div className="result-actions"><button className="primary" disabled={busy || !teachBack.trim()} onClick={submitTeachBack}>Check my explanation</button><button className="quiet" onClick={() => setTeachBack("")}>Skip teach-back</button></div>{teachResult && <div className="teach-result" role="status">{teachResult}</div>}
      </section><button className="danger-link" onClick={clearAll}>Clear all session data</button>
      <p className="metadata">Model: {analysis.metadata.model_name} · Prompt: {analysis.metadata.prompt_version} · Rules: {analysis.metadata.rules_version}</p>
    </section>}
    <section className="principles"><h2>AI for meaning. Rules for safety.</h2><div className="principle-grid"><article><h3>Semantic extraction</h3><p>AI translates differently worded instructions into a strict, source-bound structure.</p></article><article><h3>Deterministic comparison</h3><p>Auditable code checks dose, frequency, route, action, and possible omissions.</p></article><article><h3>Human resolution</h3><p>CareAlign asks a question; only a person records the care team&apos;s answer.</p></article></div></section>
    <footer><strong>Decision-support prototype only.</strong> Not clinically validated, HIPAA compliant, diagnostic, prescriptive, or cleared as a medical device.</footer>
  </main>;
}

function ConflictCard({ conflict, resolution, onResolve }: { conflict: Conflict; resolution?: Resolution; onResolve: (conflict: Conflict, response: string) => void }) {
  const [response, setResponse] = useState(resolution?.response ?? "");
  return <article className="conflict-card"><div className="conflict-top"><span className="conflict-type">{conflict.conflict_type.replaceAll("_", " ")}</span><span>{Math.round(conflict.confidence * 100)}% rule confidence</span></div>
    <h3>{conflict.medication_name}</h3><p>{conflict.summary}</p><blockquote>{conflict.evidence_spans.map((span) => <span key={span}>“{span}”</span>)}</blockquote>
    <div className="question"><strong>Ask your care team</strong><p>{conflict.clarification_question}</p></div>
    <label>Record care team response <span className="unverified">User-entered · not verified by CareAlign</span><textarea rows={2} value={response} onChange={(event) => setResponse(event.target.value)} /></label>
    <button onClick={() => onResolve(conflict, response)}>Save to this browser session</button>{resolution && <p className="saved">Response recorded by the user. CareAlign did not resolve this flag.</p>}
  </article>;
}
