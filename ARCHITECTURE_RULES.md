# ARCHITECTURE_RULES.md — Architecture Boundaries

## Layer diagram

```
┌──────────────────────────────────────────────────┐
│  Frontend (React 19, Vite, Tailwind 4, React     │
│  Router 7)                                        │
│  src/api/     ← axios HTTP clients                │
│  src/pages/   ← page components                   │
│  src/components/ ← shared UI (AppShell)           │
└──────────────┬───────────────────────────────────┘
               │ HTTP (localhost:5173 → localhost:8000)
               │ CORS: 5173, 127.0.0.1:5173
               ▼
┌──────────────────────────────────────────────────┐
│  FastAPI (Python 3.12)                            │
│                                                   │
│  app/api/         ← Route handlers (thin)         │
│       │                                           │
│  app/schemas/     ← Pydantic request/response     │
│       │                                           │
│  app/services/    ← Business logic (thick)        │
│       │              • CRUD services              │
│       │              • Generation dispatchers     │
│       │              • Provider management        │
│       │              • Preflight checks           │
│       │                                           │
│  app/providers/   ← External API adapters         │
│       │              • mock_provider              │
│       │              • openai_provider            │
│       │              • wavespeed_provider         │
│       │                                           │
│  app/models/      ← SQLAlchemy ORM models         │
│       │                                           │
│  app/pipeline/    ← PipelineState enum            │
│       │                                           │
│  app/core/        ← DB config, storage, settings  │
└──────┬───────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│  SQLite (file-based, test.sqlite)                 │
│  11 tables (see PROJECT_HANDOVER.md)              │
│  Storage: local ./storage/ directory              │
└──────────────────────────────────────────────────┘
```

## Hard boundaries (do not cross)

### 1. Provider boundary
- **Route handlers** must NOT import `openai`, `httpx`, or any provider SDK.
- **Services** may call `provider_registry.get_provider()` and invoke provider
  methods, but must NOT construct provider instances directly.
- **Providers** are the ONLY layer that touches external APIs. They return
  normalized `ProviderJob` results.

### 2. Frontend-backend boundary
- Frontend MUST NOT call OpenAI, WaveSpeed, or any external API directly.
- All external API calls go through `backend → provider`.
- Frontend communicates only with the FastAPI backend via `axios` on `/api/*`.

### 3. API key boundary
- `OPENAI_API_KEY` and `WAVESPEED_API_KEY` exist ONLY in backend environment.
- Never returned in any API response.
- Never logged in `ProviderRunLog` (redaction in `provider_run_service.py`).
- Frontend must never access or display API keys.

### 4. Database boundary
- Only `app/services/` modules access `db.query()`.
- Route handlers receive `db: Session = Depends(get_db)` and pass it to services.
- No raw SQL in route handlers or providers.
- No cross-schema coupling — schemas in `app/schemas/` are independent.

### 5. Mock vs real boundary
- Mock providers are ALWAYS enabled. Real providers are ALWAYS disabled on seed.
- `is_mock=True` → `cost_hint="mock-free"` → no confirmation required.
- `is_mock=False` → `cost_hint="paid"` → confirmation required.
- The `confirmed` field gates paid calls. Never call a paid provider without
  checking it first.

### 6. Pipeline state boundary
- Each pipeline step validates the project is in a valid prior state.
- State transitions happen only after successful asset creation.
- Valid statuses for each step are defined in the route handler.
- Never skip a pipeline state check.

## Modality registration pattern

When adding a new provider for a modality:

```
1. app/providers/<name>_provider.py   — implement base class interface
2. app/services/provider_registry.py  — register(provider_name, modality, instance)
3. app/services/model_catalog_service.py — seed model (disabled, paid)
4. app/services/provider_preflight_service.py — add API key check
5. app/schemas/provider_schema.py     — add request/estimate schemas
6. app/services/<modality>_generation_service.py — add estimate + generate dispatchers
7. app/api/<modality>.py              — add estimate + generate endpoints
8. frontend/src/api/<modality>.js     — add estimate + generate API functions
9. frontend/src/pages/<Page>.jsx      — add provider dropdown + estimate→confirm flow
10. app/tests/test_phase<N>_<name>.py — comprehensive tests
```

## Route prefix conventions

All API routes are mounted in `app/main.py`:

| Prefix | Router | Tag |
|--------|--------|-----|
| `/api` | health.router | health |
| `/api/projects` | projects.router | projects |
| `/api` | scripts.router | scripts |
| `/api` | scenes.router | scenes |
| `/api` | prompts.router | prompts |
| `/api` | assets.router | assets |
| `/api` | audio.router | audio |
| `/api` | subtitles.router | subtitles |
| `/api` | renders.router | renders |
| `/api` | providers.router | providers |

## Storage conventions

- All generated files go under `./storage/` (configurable via `STORAGE_DIR`).
- Path pattern: `storage/projects/{project_id}/{type}/filename.ext`
- Audio: `storage/projects/{id}/audio/voiceover_{job_id}.mp3`
- The storage directory is created at startup by `init_storage()`.
- File URLs in API responses use the format `/storage/projects/...`.
