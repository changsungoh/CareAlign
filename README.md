# CareAlign

**Aligning care instructions. Verifying patient understanding.**

CareAlign is an AI-powered care-transition safety prototype that detects
potential differences across care instructions, preserves the original source
text, prepares questions for a healthcare professional, and verifies patient
understanding through teach-back.

> [!WARNING]
> CareAlign is a research prototype, not medical advice. It does not diagnose
> conditions, determine which instruction is correct, or recommend starting,
> stopping, or changing medication. Always confirm potential conflicts with a
> qualified healthcare professional.

## Live deployment

- **Application:** [care-align-theta.vercel.app](https://care-align-theta.vercel.app)
- **API health:** [carealign-api.onrender.com/api/health](https://carealign-api.onrender.com/api/health)

The production frontend uses the Render API with an exact-origin CORS allowlist. Only synthetic,
de-identified demonstration text may be entered.

## Working MVP

The repository now contains the end-to-end hackathon MVP:

- two-to-five-document longitudinal comparison with required unique dates and input limits;
- structured LLM extraction with a prompt-injection boundary;
- exact/fuzzy evidence-span verification and strict schemas;
- curated medication identity plus optional exact-first RxNorm resolution with salt/form-safe review
  states, version provenance, route and mass-unit normalization;
- deterministic dose, frequency, route, action and possible-omission checks;
- source-linked clarification questions with copy, print and download actions;
- user-only resolution notes in browser `sessionStorage`;
- deterministic teach-back checklists that exclude unresolved instructions;
- a visibly labelled synthetic Demo Mode—never an invisible AI fallback;
- rate limits, daily budget guard, safe failure states, accessibility controls;
- 90 versioned synthetic evaluation cases, backend unit/integration tests and Playwright E2E.

## Privacy boundary

Use synthetic information only. Do not enter real patient names, medical
record numbers, contact details, prescriptions, or other identifiable health
information. This prototype is not configured for protected health
information.

User documents will be processed without database persistence. Raw document
logging is disabled by default through `DEBUG_LOG_RAW=false`. Future browser
session state will remain in the active tab and will not be stored by the
CareAlign backend.

## Architecture

See [Architecture](docs/ARCHITECTURE.md) for trust boundaries, data flow, failure modes and
deployment topology. Implementation and research extensions are specified in:

- [FHIR and RxNorm integration](docs/FHIR_RXNORM_INTEGRATION.md)
- [Clinical, privacy, and regulatory roadmap](docs/CLINICAL_REGULATORY_ROADMAP.md)
- [Validation program and execution artifacts](research/README.md)
- [Deployment runbook](docs/DEPLOYMENT_RUNBOOK.md)
- [Judge demo script](docs/DEMO_SCRIPT.md)
- [Devpost submission draft](docs/DEVPOST_SUBMISSION.md)
- [Solo release checklist](docs/SOLO_RELEASE_CHECKLIST.md)

## Local development

### Backend

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Check:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/version
```

Run tests:

```bash
cd backend
uv run pytest
```

To run the safe bundled demonstration without a provider key, set `DEMO_MODE=true`. It supports
only the explicit synthetic sample and is labelled in the UI. For live extraction, set
`ANTHROPIC_API_KEY`; provider failure returns an unavailable/uncertain response, never “no conflict.”

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:3000`.

Run the browser flow with `npm run test:e2e` after `npx playwright install chromium`.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Deployment health check |
| `GET /api/version` | Model/prompt/rules/dataset traceability |
| `POST /api/analyze` | Extract and deterministically compare 2–5 ordered documents |
| `POST /api/teach-back` | Compare a paraphrase to source-derived, non-conflicted checklist items |

The API is stateless. It does not offer a case retrieval endpoint and does not persist user input.

## Why this differs from existing reconciliation tools

Medication reconciliation inside an EHR is primarily clinician-facing and often bound to one
institution. CareAlign is a patient-facing safety layer for the gap between discharge notes,
prescription lists and pharmacy labels. It does not select a canonical order. Its output is a
source-linked uncertainty and a plain-language question for a human care professional. Semantic AI
is used only where wording differs; the safety decision remains inspectable rule code.

## Evaluation

`evaluation/cases/synthetic-v1.jsonl` contains exactly 90 synthetic cases split into conflict
detection (43), unsupported-pattern containment (5), teach-back (22), prompt-injection/security
(15), and resilience fault injection (5). Within conflict detection there are 15 frequency
differences, 14 possible omissions, and 14 no-conflict controls; formulation conversions are not in
the v1 scope.

`evaluation/evaluate.py` calls no LLM. It is a deterministic component regression for the bundled
parser, rule engine, and teach-back logic. Its perfect synthetic result must not be described as
live-AI performance. The report is published separately as
[demo-parser-v1.json](evaluation/results/demo-parser-v1.json).

A cost-confirmed live evaluation using `claude-haiku-4-5-20251001` completed all 85 functional
cases with 128 provider extractions and no failed cases. It used 103,389 input tokens and 13,479
output tokens, with an estimated total cost of $0.170784 ($0.002009 per completed case). On this
synthetic author-labelled dataset, conflict precision and recall, pattern containment, and security
containment were 1.00; teach-back false-missing rate was 0.00. These are engineering results on
synthetic cases—not independent review, clinical validation, or evidence of real-world safety. See
the immutable [live report](evaluation/results/live-llm-v1.json), the
[execution procedure](evaluation/LIVE_EVALUATION.md), and the
[release thresholds](evaluation/RELEASE_GATES.md).

For a delayed, shuffled solo second pass that does not expose the original labels:

```bash
python evaluation/blind_review.py prepare
# Complete evaluation/review/labels-v1.csv without opening the source dataset.
python evaluation/blind_review.py score
```

The review CSV includes a metric-specific label guide. Disagreements must be disclosed rather than
silently overwritten. The artifacts are prepared but the delayed review has not been completed;
this process can reduce recall bias but is not independent external review.

## Safety and limitations

- CareAlign never resolves a potential conflict autonomously.
- A failed or uncertain analysis must not be displayed as `no conflict`.
- Extracted evidence must be traceable to the supplied source text.
- Medication identity support will initially use a deliberately limited,
  curated alias, salt, and formulation map. Optional RxNorm lookup is exact-first, preserves source
  and canonical RxCUIs plus dataset/API versions, and never promotes a normalized-search candidate
  to a comparison identity. It remains a terminology aid rather than proof of clinical
  interchangeability.
- PRN, conditional, taper, range, and other complex dosing patterns are preserved as source text
  and routed to review. Future work may separately extract PRN maximum dose/frequency, conditional
  thresholds, and taper-phase context; the MVP does not compare them.
- The prototype is not configured or represented as HIPAA compliant.
- Demo medication aliases are deliberately limited; similar ingredients with different salts or
  formulations are not collapsed. RxNorm integration is the first post-hackathon clinical-data step.
- Formulation changes such as IR-to-ER conversions were considered as a distinct, lower-severity
  category but excluded from the MVP to avoid adding a clinical inference surface without adequate
  validation. CareAlign does not infer whether such a change was intentional.
- CareAlign is an experimental decision-support prototype. It is not a
  diagnostic or prescriptive medical device, has not been clinically
  validated, and has not been evaluated or cleared by a regulatory authority.

## Team

### OH CHANGSUNG — Solo Builder

Designed and implemented the product strategy, healthcare research, system architecture,
structured AI pipeline, deterministic conflict engine, frontend workflow, accessibility,
evaluation framework, documentation, and deployment integration.

## Validation program

The next phase is tracked as four evidence-producing workstreams: conservative RxNorm terminology,
US/Singapore clinical-regulatory review, synthetic-only formative usability testing, and independent
medical-expert review. Protocols, data forms, claims controls and the initial risk register are in
[`research/`](research/README.md). They are intentionally marked protocol-ready—not completed.
Recruitment is blocked pending the appropriate written ethics/privacy determination, and clinical or
regulatory claims are blocked pending qualified external review.

## Evidence

The project presentation cites a 2020 systematic review that included 54 studies overall. In its
adult unintentional medication-discrepancy analysis of 11 studies, the median rate after hospital
discharge was 50% (IQR 39–76%): Alqenae FA, Steinke D, Keers RN. *Drug Safety* (2020).
[PubMed 32125666](https://pubmed.ncbi.nlm.nih.gov/32125666/).

## AI use disclosure

CareAlign transparently uses an LLM for semantic extraction from synthetic text. All displayed
instructions must pass strict schema and source-evidence checks before deterministic comparison.
The repository, prompts, rules, synthetic fixtures and limitations are disclosed for judging.

## Deployment

- Frontend: [https://care-align-theta.vercel.app](https://care-align-theta.vercel.app)
- Backend: [https://carealign-api.onrender.com](https://carealign-api.onrender.com)
- Production uses `DEMO_MODE=false`, `DEBUG_LOG_RAW=false`, and the exact Vercel origin in CORS.
- The Anthropic key is stored only as a Render secret and is never exposed to the frontend.

After both URLs exist, run the fail-fast release check:

```bash
python scripts/preflight.py \
  --frontend-url https://YOUR-FRONTEND.example \
  --backend-url https://YOUR-BACKEND.example
```

## License

[MIT](LICENSE)
