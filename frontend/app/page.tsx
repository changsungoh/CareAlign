const safetyNotices = [
  "CareAlign does not diagnose conditions or decide which instruction is correct.",
  "Never start, stop, or change medication based on this prototype.",
  "Confirm every potential conflict with a qualified healthcare professional.",
];

export default function Home() {
  return (
    <main>
      <header className="nav" aria-label="Primary navigation">
        <a className="brand" href="#top" aria-label="CareAlign home">
          CareAlign
        </a>
        <span className="prototype-badge">Research prototype</span>
      </header>

      <section className="hero" id="top" aria-labelledby="hero-title">
        <p className="eyebrow">AI FOR SAFER CARE TRANSITIONS</p>
        <h1 id="hero-title">When instructions change, patients should not have to reconcile them alone.</h1>
        <p className="lede">
          CareAlign finds potential differences across care documents, preserves the source,
          prepares clear questions for the care team, and verifies understanding through teach-back.
        </p>

        <aside className="warning" aria-labelledby="warning-title">
          <h2 id="warning-title">Research prototype — not medical advice</h2>
          <ul>
            {safetyNotices.map((notice) => (
              <li key={notice}>{notice}</li>
            ))}
          </ul>
        </aside>

        <div className="actions">
          <button disabled aria-describedby="build-status">
            Start a synthetic case
          </button>
          <p id="build-status">Interactive analysis is being built now.</p>
        </div>
      </section>

      <section className="principles" aria-labelledby="principles-title">
        <h2 id="principles-title">AI for meaning. Rules for safety.</h2>
        <div className="principle-grid">
          <article>
            <h3>Source linked</h3>
            <p>Every extracted instruction must point back to text that exists in the document.</p>
          </article>
          <article>
            <h3>Human confirmed</h3>
            <p>Only a person can record that a healthcare professional clarified an instruction.</p>
          </article>
          <article>
            <h3>Fail safe</h3>
            <p>When CareAlign cannot verify an instruction, it shows uncertainty—not reassurance.</p>
          </article>
        </div>
      </section>

      <footer>
        <strong>Use synthetic information only.</strong> Do not enter identifiable or real patient data.
      </footer>
    </main>
  );
}
