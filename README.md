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

## Working MVP

The repository now contains the end-to-end hackathon MVP:

- two-document synthetic comparison with required dates and input limits;
- structured LLM extraction with a prompt-injection boundary;
- exact/fuzzy evidence-span verification and strict schemas;
- curated medication identity, salt/form, route and mass-unit normalization;
- deterministic dose, frequency, route, action and possible-omission checks;
- source-linked clarification questions with copy, print and download actions;
- user-only resolution notes in browser `sessionStorage`;
- deterministic teach-back checklists that exclude unresolved instructions;
- a visibly labelled synthetic Demo Mode—never an invisible AI fallback;
- rate limits, daily budget guard, safe failure states, accessibility controls;
- 90 versioned synthetic evaluation cases, 17 backend tests and Playwright E2E.

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
deployment topology.

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
(15), and resilience (5). `evaluation/evaluate.py` verifies this contract. Release thresholds are
defined in [evaluation/RELEASE_GATES.md](evaluation/RELEASE_GATES.md); the evaluation is engineering
evidence, not clinical validation.

## Safety and limitations

- CareAlign never resolves a potential conflict autonomously.
- A failed or uncertain analysis must not be displayed as `no conflict`.
- Extracted evidence must be traceable to the supplied source text.
- Medication identity support will initially use a deliberately limited,
  curated alias, salt, and formulation map.
- Complex dosing patterns are preserved as source text and routed to review.
- The prototype is not configured or represented as HIPAA compliant.
- Demo medication aliases are deliberately limited; similar ingredients with different salts or
  formulations are not collapsed. RxNorm integration is the first post-hackathon clinical-data step.
- CareAlign is an experimental decision-support prototype. It is not a
  diagnostic or prescriptive medical device, has not been clinically
  validated, and has not been evaluated or cleared by a regulatory authority.

## Team

### OH CHANGSUNG - AI & Backend Development

Leads the system architecture, structured AI pipeline, deterministic conflict
engine, API development, evaluation framework, and deployment integration.

### JUNG WOOHYEOP - Research & Product Design

Leads the user experience, frontend workflow, healthcare problem research,
synthetic test scenarios, accessibility design, and demo presentation.

## Evidence

The project presentation cites a systematic review reporting a median 50%
rate of unintentional medication discrepancies among adults after hospital
discharge: Alqenae FA, Steinke D, Keers RN. *Drug Safety* (2020).
[PubMed 32125666](https://pubmed.ncbi.nlm.nih.gov/32125666/).

## AI use disclosure

CareAlign transparently uses an LLM for semantic extraction from synthetic text. All displayed
instructions must pass strict schema and source-evidence checks before deterministic comparison.
The repository, prompts, rules, synthetic fixtures and limitations are disclosed for judging.

## Deployment

- Frontend: deploy `frontend/` to Vercel and set `NEXT_PUBLIC_API_BASE_URL`.
- Backend: connect the repository to Render using `render.yaml`; set the production frontend origin
  and, for live extraction, the provider key and usage limit.
- Keep `DEBUG_LOG_RAW=false`. Use `DEMO_MODE=true` only when the UI visibly identifies cached/local
  synthetic behavior. CORS should contain the final production origin before submission.

## License

[MIT](LICENSE)
