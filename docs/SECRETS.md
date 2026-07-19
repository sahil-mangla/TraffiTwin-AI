# Secrets & Configuration Policy

TraffiTwin AI's configuration is loaded through `backend/config.py`
(`pydantic-settings`), which reads from environment variables first and
falls back to a local `.env` file. This document defines where secrets are
allowed to live in each environment.

## The rule

**`.env` is a local-development convenience only. It must never exist, and
is never read from, in a production deployment.** Production secrets are
injected as real process environment variables by the hosting platform or
CI/CD system — `pydantic-settings` already prefers environment variables
over `.env` (see `SettingsConfigDict(env_file=".env", ...)` — `env_file` is
only a fallback source), so no code change is required to "not use .env in
prod"; it's an operational discipline: don't put a `.env` file in the
production container/Space at all.

## Where each secret actually lives

| Secret | Local dev | CI (GitHub Actions) | Production (Hugging Face Space) |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | `.env` (copy from `.env.example`) | not injected — Gemini-dependent tests use mocks, never the real API | HF Space → Settings → Repository secrets → exposed as an env var to the container |
| `HF_TOKEN`, `HF_USERNAME`, `HF_SPACE_NAME` | not needed | GitHub repo → Settings → Secrets and variables → Actions | N/A (used by CI to push to the Space, not read by the app itself) |
| `FIREBASE_SERVICE_ACCOUNT` | not needed | GitHub repo secrets | N/A (used by CI's Firebase deploy action) |
| `ALLOWED_ORIGINS`, `DATA_DIR`, `MODEL_PATH`, `ENVIRONMENT` | `.env` (non-secret, safe defaults) | not overridden — CI's defaults are fine for tests | HF Space repository secrets or Space "Variables" (non-secret ones can be plain Space variables rather than secrets) |

## `ENVIRONMENT` and stricter production validation

`backend/config.py` has an `environment: Literal["development", "test",
"production"]` field (`ENVIRONMENT` env var, defaults to `"development"`).
When set to `"production"`, `Settings` enforces at startup:

- `ALLOWED_ORIGINS` must include at least one non-localhost origin — a
  production deployment that only allows `localhost` is almost certainly a
  misconfiguration, and this fails fast instead of silently blocking all
  real traffic with CORS errors.
- `MODEL_PATH` must point at a file that actually exists — a production
  backend cannot usefully start without its reconstruction model.

`GEMINI_API_KEY` is intentionally **not** required in production: the app is
designed to run fully offline without it (see
`backend/services/rule_based_reporter.py`), degrading gracefully to
deterministic incident summaries. Treat it as an optional feature flag, not
a required secret.

Set `ENVIRONMENT=production` in the Hugging Face Space's repository
secrets/variables when deploying for real; leave it unset (defaults to
`development`) for local work and CI.

## Handling the API key value

`gemini_api_key` is typed as `pydantic.SecretStr`, not `str`. This means:

- `str(settings.gemini_api_key)` and `repr(settings)` never print the raw
  value — they print a masked placeholder. This prevents the key from
  leaking into logs, error tracebacks, or `print()`-based debugging.
- Any code that needs the actual key value must call
  `settings.gemini_api_key.get_secret_value()` explicitly (see
  `backend/services/gemini_service.py`). Never store the unwrapped value in
  a variable that might get logged.

## If this project ever needs a dedicated secrets manager

The current deployment targets (Hugging Face Spaces + Firebase Hosting)
don't map cleanly onto a cloud secrets manager (AWS Secrets Manager, GCP
Secret Manager, Vault) — there's no first-party integration point on either
platform, and adding one would mean running a sidecar or calling out to a
third service just to fetch env vars the platform already injects for free.
If the project later moves to a cloud platform with native secrets support
(e.g. Cloud Run + GCP Secret Manager), the natural extension point is
`Settings` in `backend/config.py`: add a `@model_validator` or a custom
settings source that fetches from the provider's SDK when a
`SECRETS_PROVIDER` env var is set, falling back to plain env vars/`.env`
otherwise — without changing how the rest of the codebase reads `settings`.
