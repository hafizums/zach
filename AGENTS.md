# AGENTS.md — Coding Agent Instructions for Zach

## What this project is

Zach is an **AI 3D Explainer Shorts Generator** — a pipeline that takes a topic and
produces a short educational video with script, scenes, images, video clips,
voiceover, subtitles, and a final render. It has a FastAPI backend and a React
(Vite + Tailwind) frontend.

The project is built in numbered phases (currently through Phase 15). Each phase
adds one piece of the pipeline or a real provider integration behind an existing
mock.

## Core rules for any agent working here

### 1. Never call real provider APIs from tests
Every test file uses `unittest.mock.patch` on the provider class method. No test
ever sets a real API key or makes an outbound HTTP call.

### 2. Mock pipeline is always the default
Every new provider model is seeded with `is_enabled = False`. Mock models stay
enabled. The user must explicitly enable paid models via the admin/provider
settings UI before they are selectable.

### 3. Paid providers require explicit confirmation
Any non-mock (`cost_hint == "paid"` or `is_mock == False`) generation must check
a `confirmed: bool` field on the request body. If `confirmed` is `False`, return
HTTP 400 with the message `"Paid provider generation requires explicit confirmation."`

### 4. Safe replace-before-delete for generated assets
When regenerating voiceovers or subtitles, the new asset must be **fully created
and committed** before the old asset is deactivated or deleted. Use atomic
helpers like `create_voiceover_and_deactivate_old()` or
`replace_subtitle_segments_for_voiceover()`. Never delete-then-create.

### 5. API key isolation
- `OPENAI_API_KEY` lives in backend env only.
- Never return it in any JSON response.
- Never log it in `ProviderRunLog.request_json` or `response_json`.
- The `provider_run_service.redact_payload()` function strips it, but each new
  log site must still be careful.
- Frontend never calls OpenAI directly.

### 6. No provider calls in route handlers
Route handlers (`app/api/*.py`) call service functions. Service functions call
providers. Providers are the only place that imports `openai` or `httpx` for
external APIs.

### 7. Every new modality follows the same pattern
When adding a provider for a new modality:
1. Add the provider class in `app/providers/<provider>_provider.py`
2. Register it in `app/services/provider_registry.py`
3. Seed a model in `app/services/model_catalog_service.py` (disabled, paid)
4. Add preflight key check in `app/services/provider_preflight_service.py`
5. Add request/estimate schemas in `app/schemas/provider_schema.py`
6. Add estimate + generate endpoints following the estimate→confirm→generate flow
7. Add a service dispatcher that switches on `provider_name`
8. Add tests — see testing rules below

### 8. Test requirements per phase
Every phase must add deterministic tests covering at minimum:
- Model seeded disabled by default
- Model not in enabled list by default
- Preflight fails when disabled
- Preflight fails when enabled but API key missing
- Preflight passes when enabled + key mocked
- Estimate defaults to mock, requires no confirmation
- Estimate for paid provider returns `ok=false` when disabled
- Estimate for paid provider returns `ok=false` when key missing
- Estimate for paid provider returns `ok=true` when key mocked
- Paid generation without confirmation returns 400
- Paid generation with confirmation + mocked provider succeeds
- Provider run logs created
- Provider run logs contain no API keys
- Malformed provider response returns 400 and preserves old data
- Failed provider call logs a FAILED run without leaking secrets
- Full mock pipeline still reaches `FINAL_RENDER_READY`
- Existing tests from prior phases still pass

### 9. Frontend patterns
- API calls go through `frontend/src/api/<domain>.js` modules
- Pages fetch enabled models from `GET /api/providers/models/enabled` and filter
  by modality
- Estimate → confirmation modal → generate flow for all paid providers
- Provider selection via dropdown populated from enabled models
- Errors shown inline (never `window.alert`)
- Buttons disabled during loading

### 10. Final report format
After every phase implementation, return:
```
1. Files changed
2. Backend pytest exact result: "xxx passed in xx.xxs"
3. Frontend build exact result: "npm run build passed / 0 errors / 0 warnings"
4. Manual smoke checklist
5. Warnings/errors
```

## Project commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload      # dev server
pytest                              # all tests
pytest app/tests/test_phase<N>*.py # specific phase tests

# Frontend
cd frontend
npm install
npm run dev         # dev server (port 5173)
npm run build       # production build check
```

## Key files to know

| File | Purpose |
|------|---------|
| `backend/app/main.py` | App bootstrap, router registration, CORS, DB init |
| `backend/app/core/database.py` | SQLAlchemy engine + session |
| `backend/app/core/config.py` | Pydantic settings (DB URL, storage dir) |
| `backend/app/pipeline/pipeline_states.py` | PipelineState enum |
| `backend/app/providers/base.py` | Abstract provider interfaces |
| `backend/app/services/provider_registry.py` | Provider instance registry |
| `backend/app/services/model_catalog_service.py` | ProviderModel CRUD + seeding |
| `backend/app/services/provider_preflight_service.py` | Preflight checks |
| `frontend/src/App.jsx` | React Router route definitions |
