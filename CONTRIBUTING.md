# Contributing to TraffiTwin AI

Thanks for considering a contribution. This document covers the local setup and the testing/quality bar every change is expected to meet before it merges.

## Local setup

**Backend**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

**Frontend**
```bash
cd frontend
npm install
npx playwright install --with-deps chromium   # only needed for E2E tests
```

See the [README](README.md#getting-started) for full setup instructions, including environment variables and how to run the app locally.

## Before opening a pull request

CI (`.github/workflows/ci.yml`) runs the checks below on every push and PR. Run them locally first so you're not waiting on CI to find problems:

```bash
# Backend — from the repo root
ruff check . --select=F63,F7,F82        # blocking: correctness only
mypy backend --ignore-missing-imports   # blocking: must be error-free
pytest tests/ -v --cov=backend --cov-report=term-missing --cov-fail-under=85

# Frontend — from frontend/
npm run lint
npx tsc -b
npm run test
npm run test:e2e   # slower; run at least once before a PR touching UI behavior
```

`ruff check . --exit-zero --statistics` also runs in CI but is advisory only (style/complexity) — it won't block your PR, but please don't add to the count if you can avoid it.

## Testing expectations

- **New backend logic** (a service, a route, a data/ML pipeline function) needs tests in `tests/`. Follow the existing pattern: one test file per module, `pytest.fixture(scope="module")` for anything expensive to set up (loading the METR-LA dataset, the LightGBM checkpoint), and mock only genuinely external calls (Gemini) — not your own code.
- **New frontend logic** (a store action, a hook, a component with real interaction) needs a Vitest test alongside it. If the component uses `motion/react`, you don't need to do anything special — `src/test/setup.ts` already mocks it so `AnimatePresence` unmounts synchronously.
- **A new user-facing flow** (a new control, a new modal, a new page) is a candidate for a Playwright spec in `frontend/e2e/` — but keep these few and thin; they're the most expensive tests to run and maintain. Prefer covering logic at the unit/component level first.
- **A bug fix** should include a regression test that fails without the fix.
- Coverage must not regress below the CI gate (`--cov-fail-under=85` on the backend). If you're touching a file with low coverage, consider raising it while you're in there rather than leaving it as-is.

## Code style

- Backend: type-annotate new code so `mypy backend --ignore-missing-imports` stays clean — it's a blocking CI gate, not advisory.
- Don't suppress a Ruff or mypy finding with an inline ignore unless you've confirmed it's a false positive; fix the underlying issue first.
- Match the existing commit style: concise, present-tense, explains *why* over *what*.

## Commit / PR expectations

- Keep PRs scoped to one concern where practical — it makes review and `git bisect` easier.
- Don't skip CI checks (`--no-verify`, disabling a workflow step) to get a PR through; if a check is wrong, fix or discuss the check itself.
