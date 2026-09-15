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

## Current status

The repository contains the safety-first Day 1 foundation:

- stateless FastAPI backend;
- health and version endpoints;
- strict instruction and analysis schemas;
- normalized evidence-span validation;
- deterministic mass-unit and administration-route normalization;
- an English-only Next.js landing page with visible safety notices;
- backend tests and CI configuration.

The working comparison and teach-back flows are under active development.

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

```text
Next.js frontend
    -> FastAPI API
    -> structured AI extraction
    -> schema and evidence validation
    -> deterministic normalization and conflict rules
    -> source-linked clarification
    -> teach-back verification
```

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

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:3000`.

## Safety and limitations

- CareAlign never resolves a potential conflict autonomously.
- A failed or uncertain analysis must not be displayed as `no conflict`.
- Extracted evidence must be traceable to the supplied source text.
- Medication identity support will initially use a deliberately limited,
  curated alias, salt, and formulation map.
- Complex dosing patterns are preserved as source text and routed to review.
- The prototype is not configured or represented as HIPAA compliant.
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

## License

[MIT](LICENSE)
