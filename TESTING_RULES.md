# TESTING_RULES.md — Test Conventions & Commands

## Test commands

```bash
# Run all tests
cd backend
pytest

# Run a specific test file
pytest app/tests/test_phase15_subtitles.py

# Run a specific test function
pytest app/tests/test_phase15_subtitles.py::test_openai_transcription_model_seeded_disabled

# Run with verbose output
pytest -v

# Run with short traceback
pytest --tb=short

# Run only tests matching a pattern
pytest -k "phase14"
```

## What tests must pass before final report

**All 224 tests** must pass. Specifically:

| Test file | Tests | Covers |
|-----------|-------|--------|
| `test_health.py` | 1 | API health check |
| `test_projects.py` | 8 | Project CRUD |
| `test_scripts.py` | 6 | Script generation + approval |
| `test_scenes.py` | 6 | Scene planning + approval |
| `test_prompts.py` | 9 | Prompt generation + approval |
| `test_assets.py` | 12 | Image/clip generation, retry, approval |
| `test_audio_subtitles.py` | 10 | Voiceover + subtitle generation |
| `test_renders.py` | 8 | Final render generation |
| `test_openai_provider.py` | 4 | OpenAI LLM provider unit tests |
| `test_openai_integration.py` | 15 | OpenAI LLM integration + pipeline |
| `test_provider_base.py` | 5 | Mock provider unit tests |
| `test_providers_catalog.py` | 15 | Provider model CRUD + preflight + redaction |
| `test_preflight_blockers.py` | 6 | Disabling models blocks generation |
| `test_wavespeed.py` | 32 | WaveSpeed image provider + estimates |
| `test_wavespeed_video.py` | 30 | WaveSpeed video provider + estimates |
| `test_phase14_voiceover.py` | 25 | OpenAI TTS provider + estimates + safety |
| `test_phase15_subtitles.py` | 28 | OpenAI transcription + estimates + safety |

**Total: 224 tests**

## Test infrastructure

### Database isolation
Every test file uses an **in-memory SQLite database** with `StaticPool`:

```python
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
```

A `@pytest.fixture(autouse=True)` drops all tables, recreates them, and seeds
default mock models before each test. This ensures test isolation.

### Dependency override
Tests override FastAPI's `get_db` dependency to point to the in-memory DB:

```python
app.dependency_overrides[get_db] = override_get_db
```

### No real API calls — ever
Every test that exercises a real provider path uses `unittest.mock.patch`:

```python
with patch.object(OpenAITTSProvider, "generate_voiceover", return_value=mock_job):
    res = client.post(...)
```

For malformed/failure tests:
```python
with patch.object(OpenAITTSProvider, "generate_voiceover",
                  side_effect=Exception("Simulated failure")):
    res = client.post(...)
```

For API key preflight tests:
```python
with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
    res = client.post(...)

# Or for missing key:
with patch.dict(os.environ, {}, clear=True):
    os.environ.pop("OPENAI_API_KEY", None)
    res = client.post(...)
```

## Test patterns by phase

### Every phase test file must include

1. **Model seeded disabled** — query provider models, find the new one, assert `is_enabled == False`
2. **Not in enabled list** — query enabled models, assert new model absent
3. **Preflight disabled** — preflight with disabled model → `ok: false`
4. **Preflight no key** — enable model, clear env, preflight → `ok: false`, message contains key name
5. **Preflight with key** — enable model, mock key, preflight → `ok: true`
6. **Estimate defaults mock** — POST estimate with no body → mock provider, `requires_confirmation: false`
7. **Estimate paid disabled** — POST estimate with paid provider disabled → `ok: false`
8. **Estimate paid no key** — enable paid, clear key → `ok: false`, message contains key name
9. **Estimate paid with key** — enable paid, mock key → `ok: true`, `requires_confirmation: true`
10. **Estimate field correctness** — verify `script_id`, `character_count`, `estimated_jobs`, etc.
11. **Estimate missing prerequisite** — no approved script / no voiceover → `ok: false`
12. **Estimate before valid status** — project in wrong state → `ok: false`
13. **Mock generation no confirmation** — generate with mock → 200, data correct
14. **Paid generation without confirmation** — generate with paid, `confirmed: false` → 400
15. **Paid generation with confirmation** — mock provider, `confirmed: true` → 200, data correct
16. **Provider fields stored** — verify provider_name, model_name, provider_job_id in response
17. **Run logs created** — query `/provider-runs`, verify log exists with correct operation
18. **No key leakage** — use a unique fake key, verify it does not appear in any log
19. **Malformed response preserves old** — generate valid mock first, then try paid with bad response → 400, old data intact
20. **Failed provider logs failed run** — provider raises exception → FAILED log exists, no key leak
21. **Full mock pipeline** — run all steps with mock → project reaches `FINAL_RENDER_READY`
22. **Existing tests compatibility** — backward-compatible calls still work

### Safety tests (Phases 14+)

- **Failed DB create preserves old active voiceover** — mock successful provider, patch DB helper to raise, verify old voiceover still active
- **Failed DB replace preserves existing subtitles** — mock successful provider, patch replace helper to raise, verify original segments intact with same IDs/text

## Frontend build check

```bash
cd frontend
npm run build
```

Must produce `0 errors, 0 warnings`. This is required before every final report.

## Current known gaps

- **No frontend test framework.** `package.json` has no Jest, Vitest, or React
  Testing Library. The frontend build check (`npm run build`) is the only
  frontend validation.
- **No Alembic migrations.** Schema changes for new columns (e.g., the
  `provider_name`/`model_name` columns added to `voiceovers` in Phase 14) rely
  on SQLite's lax schema or table drops. The test suite drops and recreates
  tables each run, so this is not a test issue, but production DB migrations
  will need a strategy.
- **No CI/CD configuration.** No GitHub Actions, GitLab CI, or similar workflow
  files were found in the repository.
