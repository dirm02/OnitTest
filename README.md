# OnitTest: ABC Energy Lead Qualification PoC

Proof of concept for the ABC Energy Solutions technical challenge. The app helps internal sales, CRA, or business development users qualify commercial energy prospects from call notes, CRM records, spreadsheet rows, or research snippets. It collects the required lead variables, applies a deterministic Strategic Lead Matrix, and returns a structured tier recommendation for review.

## What This Builds

- Internal lead qualification workspace for ABC Energy staff reviewing prospects.
- ABC Energy branded React/TypeScript frontend.
- FastAPI backend with an unauthenticated MVP `POST /api/v1/lead/turn` endpoint.
- Explicit `LeadState` with unknown, inferred, and confirmed slots.
- PocketFlow orchestration for each qualification turn.
- Deterministic Python rule engine for tiering.
- Square-footage fallback when annual MWh is unknown.
- Focused pytest coverage for the matrix and fallback logic.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind |
| Backend | FastAPI, Pydantic v2 |
| Database target | PostgreSQL |
| Agent orchestration | PocketFlow |
| LLM provider target | Google Gemini through PydanticAI |
| Deployment | Netlify frontend, Azure VM backend |

The MVP keeps the final tier decision outside the LLM. The LLM can later improve extraction and wording, but the matrix logic is deterministic and testable.

## Local Development

### Backend

```bash
cd backend
uv run --extra dev pytest tests/test_lead_qualification.py
uv run uvicorn app.main:app --reload
```

Backend defaults to `http://localhost:8000`.

Required backend environment variables for LLM-backed extensions:

```bash
GOOGLE_API_KEY=...
AI_MODEL=gemini-2.5-flash
```

The current lead qualification tests do not require a Google API key.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:3000`.

Use this to point the frontend at a backend:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Lead API

```http
POST /api/v1/lead/turn
```

The MVP endpoint is open to keep the hiring-test demo simple. In production, it should sit behind staff authentication or an internal network boundary.

Example request:

```json
{
  "message": "CRM note: industrial plant, 650 MWh annually, provider in place, contract expires in 5 months.",
  "session_id": "optional-client-session-id",
  "state": null
}
```

Example response:

```json
{
  "session_id": "...",
  "response": "Tier 1: Industrial usage is above 500 MWh...",
  "state": {
    "business_segment": { "value": "industrial", "status": "confirmed" },
    "annual_usage_mwh": { "value": 650, "status": "confirmed" }
  },
  "missing_fields": [],
  "classification": {
    "tier": "Tier 1",
    "ready": true,
    "matched_rule": "industrial_high_usage_expiring_soon"
  },
  "trace": {
    "source": "pocketflow",
    "nodes": ["extract", "merge", "estimate_usage", "classify", "plan_next_question", "respond"]
  }
}
```

## Qualification Rules

- Industrial, usage greater than 500 MWh, expiring in less than 6 months: Tier 1.
- Industrial, usage 100-500 MWh, expiring in less than 12 months, building age under 5 years: Tier 2.
- Commercial, usage greater than 50 MWh, month-to-month: Tier 1.
- Commercial, usage 20-50 MWh, fixed term, building age under 2 years: Tier 3.
- Any segment with no current provider: Tier 1.
- Complete but unmatched leads are marked Manual Review.

## Verification

Commands run during Phase 1:

```bash
cd backend
uv run --extra dev pytest tests/test_lead_qualification.py
uv run --extra dev ruff check app\lead_qualification app\schemas\lead.py app\api\routes\v1\lead.py app\api\router.py app\api\routes\v1\__init__.py tests\test_lead_qualification.py

cd ../frontend
npm run type-check
npm run lint
npm run build
```

Current note: frontend lint/build pass with warnings inherited from the generated scaffold in unrelated authenticated dashboard/chat files.

## Deployment

Frontend deployment is configured in `netlify.toml` and builds from `frontend/`.

Backend deployment notes for Azure VM are in `docs/deployment-targets.md`.

Architecture and phase plan are in `docs/mvp-plan.md`.

## Future Extensions

- Add LLM structured extraction behind the existing deterministic extractor interface.
- Persist `LeadState` and qualification events to PostgreSQL.
- Add a saved-leads review page for sales managers or CRA reviewers.
- Add staff authentication when moving beyond the MVP demo.
- Add Langfuse or Phoenix tracing for LLM calls and per-node traces.
- Add a small RAG knowledge base for tariff PDFs, ABC FAQs, or contract education.
- Add CRM/calendar handoff for Tier 1 leads.
- Scale with stateless FastAPI replicas, PgBouncer, and LLM rate limiting.
