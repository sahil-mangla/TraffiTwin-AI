# CORS Audit Report — TraffiTwin AI Backend

**Date:** 2026-07-01  
**Audited by:** Automated CORS Audit  
**Backend:** FastAPI · `backend/api/app.py`  
**Target deployment:** Hugging Face Spaces (Docker) + Firebase Hosting (CDN)

---

## 1. Current Configuration (Before Fix)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 2. Problems Found

### 🚨 Critical — `allow_origins=["*"]` + `allow_credentials=True` is spec-illegal

The [CORS specification (Fetch Standard § 3.2)](https://fetch.spec.whatwg.org/#cors-protocol) forbids a server from setting `Access-Control-Allow-Credentials: true` when the origin is `*`. Every modern browser enforces this:

> "If the `credentials` flag is set and `Access-Control-Allow-Origin` is `*`, return a network error."

**Practical consequence:** any cross-origin request that the browser sends with credentials (cookies, `Authorization` headers) would have been silently blocked, causing confusing failures in production.

### ⚠️  Medium — Wildcard methods/headers unnecessarily broad

`allow_methods=["*"]` exposes `DELETE`, `PUT`, `PATCH`, `HEAD`, and `CONNECT` — none of which are used by this API. This widens the attack surface for CSRF.

### ⚠️  Medium — No environment-variable–driven origin list

Hard-coding `"*"` means switching from development to production required a code change. There was no mechanism to restrict origins to known Firebase Hosting domains without editing source code.

### ℹ️  Low — `allow_headers=["*"]` broader than needed

Only `Content-Type`, `Accept`, and `Origin` are required by this API.

---

## 3. Changes Made

### `backend/api/app.py`

```python
# Build allowed-origins list from env var (comma-separated).
_DEFAULT_ORIGINS = ",".join([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])
_raw_origins = os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS)
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,          # explicit list, never "*"
    allow_credentials=False,                 # no cookies/auth used
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin"],
)
```

### `.env.example`

```env
# Comma-separated list of allowed CORS origins.
# Add your Firebase Hosting URLs here for production.
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 4. Final Allowed Origins

Configure in `ALLOWED_ORIGINS` environment variable.  
**Local development (default — no env var needed):**

| Origin | Allowed |
|--------|---------|
| `http://localhost:5173` | ✅ |
| `http://127.0.0.1:5173` | ✅ |
| `http://localhost:8000` | ✅ |
| `http://127.0.0.1:8000` | ✅ |

**Production — set in Hugging Face Space Secrets:**

```
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://traffitwin-ai.web.app,https://traffitwin-ai.firebaseapp.com
```

| Origin | Allowed |
|--------|---------|
| `https://traffitwin-ai.web.app` | ✅ (add to env var) |
| `https://traffitwin-ai.firebaseapp.com` | ✅ (add to env var) |
| `https://evil.example.com` | 🚫 Blocked |
| `null` (file://) | 🚫 Blocked |

> **Note:** Replace `traffitwin-ai` with your actual Firebase project ID if different.

---

## 5. `allow_credentials` Decision

**Set to `False`.**

This backend uses no cookies, no session tokens, and no `Authorization` headers. Setting `allow_credentials=True` would:

1. Violate the CORS spec when paired with wildcard origins.
2. Grant browsers permission to attach cookies (if any were ever set accidentally), opening a CSRF surface.

`False` is the correct and safest option for this project.

---

## 6. Endpoint Coverage

All frontend-facing endpoints are covered by the `CORSMiddleware` added globally via `app.add_middleware()`. FastAPI applies middleware to every route automatically.

| Endpoint | Method | CORS Status |
|----------|--------|-------------|
| `/health` | GET | ✅ |
| `/state` | GET | ✅ |
| `/graph` | GET | ✅ |
| `/metrics` | GET | ✅ |
| `/step` | POST | ✅ |
| `/simulate_failure` | POST | ✅ |
| `/analyze-current-state` | POST | ✅ |
| `/generate-incident-summary` | POST | ✅ |
| `/snapshot` | GET | ✅ |
| `/incident-summaries` | GET | ✅ |

---

## 7. Test Results

```
pytest tests/test_cors.py -v
```

```
55 passed in 5.12s
```

### Test matrix

| Test | Coverage |
|------|----------|
| `test_preflight_allowed_origins_get` | OPTIONS preflight for all 4 GET endpoints × 4 allowed origins = 16 |
| `test_preflight_allowed_origins_post` | OPTIONS preflight for all 3 POST endpoints × 4 allowed origins = 12 |
| `test_preflight_blocked_origins` | Confirms 3 attacker origins do NOT receive ACAO header |
| `test_get_endpoints_cors_header` | Actual GET requests return correct ACAO on all 4 endpoints × 4 origins = 16 |
| `test_post_endpoints_cors_header` | Actual POST requests return correct ACAO on 3 endpoints × 2 key origins = 6 |
| `test_credentials_header_not_present` | `Access-Control-Allow-Credentials` is not `"true"` |
| `test_health_check` | Basic smoke test |

### Key assertions verified

- ✅ `Access-Control-Allow-Origin` is present on all responses from allowed origins
- ✅ `Access-Control-Allow-Origin` matches the requesting origin exactly (not `*`)
- ✅ OPTIONS preflight returns 200/204 for all allowed origins
- ✅ OPTIONS preflight does NOT echo attacker origins back
- ✅ POST requests succeed with correct ACAO
- ✅ `Access-Control-Allow-Credentials` is **not** `"true"`

---

## 8. Production Deployment Checklist

### Hugging Face Space

Set the following **Space Secret** in your Space settings:

```
ALLOWED_ORIGINS=https://traffitwin-ai.web.app,https://traffitwin-ai.firebaseapp.com,http://localhost:5173
```

The Space URL (`https://sahilmangla-traffitwin-backend.hf.space`) does **not** need to be in `ALLOWED_ORIGINS` — it is the backend itself, not a frontend origin.

### Firebase Hosting

No CORS configuration is needed on the Firebase side. Firebase serves static files; CORS is only relevant on the backend (Hugging Face).

### Vite / Frontend (Local Dev)

The Vite dev server proxies `/api/*` → `http://localhost:8000`, so the browser never makes a cross-origin request during local development. CORS is only exercised in production when the built frontend (`https://traffitwin-ai.web.app`) calls the Hugging Face backend directly.

---

## 9. Production Readiness Verdict

| Check | Status |
|-------|--------|
| No `allow_origins=["*"]` in production | ✅ (env-var driven) |
| `allow_credentials=False` (correct for no-auth API) | ✅ |
| Minimal `allow_methods` (GET, POST, OPTIONS only) | ✅ |
| Minimal `allow_headers` | ✅ |
| Firebase origins explicitly allowed via env var | ✅ (configure at deploy time) |
| Local dev origins allowed | ✅ (default fallback) |
| Blocked origins do not receive ACAO | ✅ |
| 55/55 CORS tests pass | ✅ |

**The backend is production-ready for Firebase + Hugging Face Spaces deployment** provided the `ALLOWED_ORIGINS` secret is set in the Space with the correct Firebase Hosting URLs.
