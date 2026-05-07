# ABC Energy Lead Qualification MVP

## Product Goal

Build a proof of concept for ABC Energy Solutions that helps internal sales, CRA, or business development users qualify commercial energy prospects through a guided chat experience. The user pastes or enters prospect information from calls, CRM records, spreadsheets, emails, or research notes. The tool extracts the required variables, asks for missing fields, and returns structured lead data plus a tier recommendation.

## MVP Scope

- Internal lead qualification workspace for staff, no login required for the MVP demo.
- Guided quick starts plus free-form chat.
- Explicit lead state with unknown, inferred, and confirmed slots.
- Deterministic Strategic Lead Matrix rule engine.
- Square-footage fallback when annual usage is unknown.
- PostgreSQL conversation and qualification persistence.
- Lightweight orchestration with PocketFlow.
- React/TypeScript frontend deployed to Netlify.
- FastAPI backend deployed to an Azure VM.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind.
- Backend: FastAPI, Pydantic v2, SQLAlchemy async.
- Database: PostgreSQL.
- LLM provider: Google Gemini through PydanticAI.
- Orchestration: PocketFlow for a small per-turn graph.
- Evaluation: pytest scenarios for matrix rules and fallback behavior.

## Lead Workflow

Each internal reviewer turn runs through a controlled flow:

1. Load or initialize `LeadState`.
2. Extract facts from the latest pasted note or reviewer message.
3. Merge extracted facts into state.
4. Estimate annual usage from square footage if usage is unknown.
5. Apply deterministic qualification rules.
6. Ask the next missing-field question or finalize the tier.
7. Return the assistant response, state, missing fields, and trace.

Gemini can assist with structured extraction, while deterministic extraction remains available as a reliability fallback. The tier decision remains deterministic Python logic.

## Phases

### Phase 0: Scaffold and Configuration

- Generate the lean FastAPI + Next.js + PostgreSQL app.
- Configure Google/Gemini provider.
- Add Netlify root configuration.
- Attach GitHub remote.

### Phase 1: Backend Core

- Add lead state models.
- Add rule engine.
- Add fallback estimator.
- Add PocketFlow orchestration.
- Add MVP lead turn endpoint.
- Add pytest coverage.

### Phase 2: Frontend Product Surface

- Replace generic landing page with ABC Energy qualification tool.
- Add quick-start choices.
- Add chat UI for internal prospect review.
- Add lead summary/progress panel.

### Phase 3: End-to-End Wiring

- Connect frontend to backend lead endpoint.
- Verify local backend/frontend flow.
- Keep the MVP route simple while documenting future staff authentication.

### Phase 4: Delivery Notes

- Rewrite README for the hiring challenge.
- Document Netlify frontend deployment.
- Document Azure VM backend deployment.
- Document performance, concurrency, observability, and future RAG/eval extensions.

### Phase 5: PoC Bonus Coverage

- Add Gemini extraction behind the deterministic fallback.
- Persist lead sessions and turn history in PostgreSQL.
- Add a saved-leads review panel for the internal team.
- Add evaluation cases for the Strategic Lead Matrix.
- Keep RAG, full admin, authentication, and advanced observability documented as production follow-ups.

## Deployment Shape

Netlify builds from `frontend/` using `netlify.toml`. The frontend reads the backend URL from `NEXT_PUBLIC_API_URL`.

The Azure VM hosts the FastAPI backend and PostgreSQL, preferably behind Nginx/Caddy with TLS. For a demo VM, Docker Compose is enough.
