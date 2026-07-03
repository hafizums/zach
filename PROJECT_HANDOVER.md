# PROJECT_HANDOVER.md — Zach Project Handover

## Project goal

**AI 3D Explainer Shorts Generator** — a web application that automates the
creation of short educational videos. The user provides a topic; the system
generates a script, plans scenes, creates image and video prompts, generates
visual assets via AI providers, produces voiceover audio, times subtitles, and
assembles a final 3D explainer render.

The system supports both **mock** (deterministic, free, local) and **real**
(OpenAI, WaveSpeed) providers behind a common interface, gated by an
estimate→confirm→generate flow for any paid provider call.

## Current state (Phase 15 complete)

All 15 phases are implemented. The full mock pipeline works end-to-end from
`DRAFT_CREATED` to `FINAL_RENDER_READY`. Real provider integrations exist for:

| Modality | Provider | Model | Status |
|----------|----------|-------|--------|
| LLM (text) | OpenAI | gpt-4o-mini | Disabled by default |
| Image | WaveSpeed | flux-schnell | Disabled by default |
| Video | WaveSpeed | wan-2.1-1.3b | Disabled by default |
| Audio (TTS) | OpenAI | gpt-4o-mini-tts | Disabled by default |
| Transcription | OpenAI | whisper-1 | Disabled by default |

All real providers are disabled by default. Mock providers remain the default
for every modality.

## Architecture overview

```
frontend (React + Vite + Tailwind, port 5173)
    │
    │ axios → /api/*
    ▼
backend (FastAPI + SQLAlchemy + SQLite, port 8000)
    │
    ├── app/api/          — 10 route modules
    ├── app/services/     — 20 service modules (CRUD + generation + provider mgmt)
    ├── app/providers/    — mock, openai, wavespeed adapters
    ├── app/models/       — 10 SQLAlchemy models
    ├── app/schemas/      — Pydantic request/response schemas
    └── app/pipeline/     — PipelineState enum
```

### Database (SQLite, file-based)

11 tables:

| Table | Key fields |
|-------|-----------|
| `video_projects` | title, topic, language, duration_target, aspect_ratio, visual_style, status |
| `scripts` | project_id, version, script_text, hook, payoff, status |
| `scenes` | project_id, script_id, scene_number, narration_text, visual_summary, camera_direction, motion_direction |
| `image_prompts` | scene_id, prompt_text, negative_prompt, style_lock, status |
| `video_prompts` | scene_id, prompt_text, negative_prompt, motion_strength, camera_lock, status |
| `generated_images` | scene_id, file_url, provider_name, model_name, provider_job_id, is_active, status |
| `generated_clips` | scene_id, file_url, provider_name, model_name, duration_seconds, fps, is_active, status |
| `voiceovers` | project_id, script_id, provider_name, model_name, voice_id, file_url, duration_seconds, is_active, status |
| `subtitle_segments` | project_id, voiceover_id, index, start_time, end_time, text, style, status |
| `final_renders` | project_id, title, manifest_json, render_job_id, is_active, status |
| `provider_models` | provider_name, model_name, display_name, modality, is_enabled, is_mock, cost_hint, default_params_json |
| `provider_run_logs` | project_id, scene_id, provider_name, model_name, modality, operation, provider_job_id, status, request_json, response_json, error_message |

### Pipeline states (ordered progression)

```
DRAFT_CREATED → TOPIC_ANALYZED → RESEARCH_NOTES_READY → SCRIPT_READY →
SCENE_PLAN_READY → IMAGE_PROMPTS_READY → VIDEO_PROMPTS_READY →
IMAGES_GENERATED → CLIPS_GENERATED → VOICEOVER_READY → SUBTITLES_READY →
FINAL_RENDER_READY
```
Plus `FAILED` as an off-ramp.

### Provider architecture

Every external service is behind an abstract base class in `app/providers/base.py`:

- `LLMProvider` — `generate_text()`, `generate_structured_json()`
- `ImageProvider` — `generate_image()`
- `VideoProvider` — `generate_video()`
- `AudioProvider` — `generate_voiceover()`
- `TranscriptionProvider` — `transcribe()`, `transcribe_audio()`

Concrete adapters:
- `MockLLMProvider`, `MockImageProvider`, `MockVideoProvider`, `MockAudioProvider`, `MockTranscriptionProvider`
- `OpenAILLMProvider`, `OpenAITTSProvider`, `OpenAITranscriptionProvider`
- `WavespeedImageProvider`, `WavespeedVideoProvider`

The `ProviderRegistry` maps `(provider_name, modality)` → instance. Models in
`provider_models` table gate enablement. `provider_preflight_service` checks:
model exists, model enabled, adapter registered, API key present.

### Generation flow (every modality)

```
User clicks "Generate X"
  → POST /estimate  (checks preflight, returns cost_hint + requires_confirmation)
  → if paid: show confirmation modal (provider, cost, job count)
  → user confirms (confirmed=true)
  → POST /generate   (preflight → provider call → save asset → deactivate old)
```

## Key modules

### Backend services

| Service | Purpose |
|---------|---------|
| `script_generation_service` | Script generation (mock LLM or OpenAI) |
| `scene_planner_service` | Scene planning from script |
| `prompt_generation_service` | Image/video prompt generation |
| `asset_generation_service` | Image + clip generation (mock or WaveSpeed), estimate endpoints |
| `audio_generation_service` | Voiceover generation (mock or OpenAI TTS), estimate |
| `subtitle_generation_service` | Subtitle generation (mock or OpenAI Whisper), segment normalization, estimate |
| `render_generation_service` | Final render manifest assembly |
| `provider_preflight_service` | Model availability + API key checks |
| `provider_run_service` | Provider run log creation with secret redaction |
| `model_catalog_service` | ProviderModel CRUD + default seeding |

### Frontend pages

| Page | Route | Purpose |
|------|-------|---------|
| Dashboard | `/` | Project list, create new |
| CreateProject | `/projects/new` | New project form |
| ProjectDetail | `/projects/:id` | Pipeline progress, navigation |
| ScriptReview | `/projects/:id/script` | Generate/review/approve script |
| ScenePlanner | `/projects/:id/scenes` | Generate/review/approve scenes |
| PromptReview | `/projects/:id/prompts` | Generate/review/approve prompts |
| AssetGeneration | `/projects/:id/assets` | Generate images + clips, retry, approve |
| AudioSubtitles | `/projects/:id/audio-subtitles` | Generate voiceover + subtitles, edit, approve |
| FinalRender | `/projects/:id/final-render` | Generate final render |
| ProviderSettings | `/provider-settings` | Enable/disable provider models |

## Commands

```bash
# Backend dev server
cd backend && uvicorn app.main:app --reload

# Backend tests (224 tests, ~2 min)
cd backend && pytest

# Frontend dev server
cd frontend && npm run dev

# Frontend production build check
cd frontend && npm run build
```

## Next recommended work

1. **Real final rendering** — the render pipeline is currently mock-only. A real
   render would combine clips + voiceover + subtitles using FFmpeg or a cloud
   rendering service.

2. **Music/SFX generation** — background music and sound effects generation.

3. **Billing wallet/ledger** — track provider usage costs per project/user.

4. **User authentication** — currently no auth; all projects are global.

5. **Automatic paid provider calls** — currently each paid call requires manual
   confirmation. A wallet/credit system could enable automatic billing.

## Unknowns / needs verification

- The `TOPIC_ANALYZED` and `RESEARCH_NOTES_READY` pipeline states exist in the
  enum but appear unused in current route handlers. Needs verification whether
  they are future states or vestigial.
- No database migration system (Alembic) is configured. Schema changes require
  manual handling or table drops. The test suite drops and recreates tables
  each run.
- Frontend has no test framework configured (no Jest, Vitest, or React Testing
  Library in package.json).
