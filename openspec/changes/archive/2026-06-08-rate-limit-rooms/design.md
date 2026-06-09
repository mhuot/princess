## Context

Princess runs as a single FastAPI process behind nginx (TLS termination, `X-Forwarded-For`). The room registry is in-memory and grows with every `POST /api/rooms`; rooms only get evicted after 5 minutes of idle (per the orphan-cleanup spec). That gap is enough for a script to allocate a lot of dead rooms before the registry sheds them. Similarly, `POST /api/rooms/{code}/join` can be hammered to enumerate the 4-char code namespace (~1.7M permutations).

We don't have user accounts, sessions, or any per-request authentication other than `host_pid` opaque tokens. The only stable identifier we can rate-limit on is the **client IP** as observed at the application after nginx forwarding.

## Goals / Non-Goals

**Goals:**
- Cap the four abusable mutating endpoints at per-IP quotas large enough that no real user notices.
- Use a library that's small, well-trodden, FastAPI-native, and doesn't pull in heavy deps (no Redis).
- Correctly extract the client IP behind the nginx reverse proxy.
- Make the limiter easy to disable locally (dev) and in CI (tests) via env var.
- Return a 429 whose body matches the existing `{"detail": ...}` shape so clients show it as-is.

**Non-Goals:**
- Distributed limiter (Redis / memcached). Single-process today.
- Limiting reads or WebSocket messages.
- Per-account quotas or any form of authentication.
- A CAPTCHA / proof-of-work step.
- Configurable quotas at runtime — the limits live as code constants.

## Decisions

### Library: `slowapi`
**Choice:** Use `slowapi` (PyPI, ~10k stars on the upstream Flask-Limiter, slowapi is the Starlette/FastAPI port). It registers as middleware-ish via decorators, returns 429 with a configurable JSON body, supports custom `key_func`, and uses an in-memory backend by default.
**Why:** It is the canonical answer for "rate limit a FastAPI app." Alternatives:
- `fastapi-limiter` requires Redis. Overkill here.
- Hand-rolled middleware + a `collections.Counter` window. Easy to get wrong (race conditions on async, no eviction). Not worth the savings.
- nginx `limit_req` zones. Works but couples the limit to ops config — harder to test in CI and harder to override per-env from app code.

### Key function: real client IP
**Choice:**

```python
def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # First IP in the list is the original client; subsequent are proxies.
        return xff.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
```

Pass this as `Limiter(key_func=_client_ip)`. slowapi default (`get_remote_address`) only looks at `request.client.host`, which behind nginx is `127.0.0.1` for everyone — that would lump all users into one bucket. The explicit XFF parse is required.

**Why:** nginx writes `X-Forwarded-For: <client>, <intermediate>` — first hop is the user. We trust the header because only our own nginx ever speaks to the app port; if someone sets XFF from the outside, nginx overwrites it. The `"unknown"` fallback degrades safely to a single bucket rather than crashing.

### Limit quotas
**Choice (per-IP):**

| Endpoint | Limit | Reasoning |
| --- | --- | --- |
| `POST /api/rooms` | 6/minute | A human creates maybe 1 room every few minutes. 6 absorbs double-clicks and accidental retries. A script trying to flood gets capped at 360/hr per IP — well below the rate that would matter for the in-memory registry. |
| `POST /api/rooms/{code}/join` | 30/minute | Humans retry on a wrong code maybe 2–3 times. 30 still blocks enumeration: covering 1.7M codes at 30/min/IP needs >1000 hours per IP. |
| `POST /api/rooms/{code}/bot` | 20/minute | Hosts add at most ~3 bots per game. 20 lets quick lobby tweaks through while killing rename-amp-style abuse. |
| `POST /api/rooms/{code}/rename` | 30/minute | Humans rename at most a handful of times. 30 blocks the WS-broadcast amplification vector. |

Limits live as module-level constants near the top of `server.py`:

```python
RATE_LIMIT_CREATE = "6/minute"
RATE_LIMIT_JOIN = "30/minute"
RATE_LIMIT_BOT = "20/minute"
RATE_LIMIT_RENAME = "30/minute"
```

so they're easy to spot and bump. slowapi accepts the human-readable string form.

**Why these numbers:** picked at the "obviously fine for humans, obviously slow for scripts" boundary. They are not a security guarantee — a determined attacker rotates IPs — but they raise the cost dramatically and protect the in-memory registry from the lazy-script case.

### Disable via env var
**Choice:** At startup:

```python
limiter = Limiter(key_func=_client_ip)
if os.environ.get("PRINCESS_RATE_LIMIT_DISABLED") == "1":
    limiter.enabled = False
```

`tests/conftest.py` sets `PRINCESS_RATE_LIMIT_DISABLED=1` for the default session so existing tests aren't affected. A single new test temporarily un-sets it (or builds a fresh app with the flag cleared) to verify enforcement.

**Why:** slowapi exposes `Limiter.enabled` as a documented kill switch. Cleaner than monkey-patching the decorator.

### 429 response shape
**Choice:** Register slowapi's default `_rate_limit_exceeded_handler` (which returns 429 with `{"detail": "...."}`) rather than wrapping it. The default detail string is `"Rate limit exceeded: <quota>"` — that's readable and surfaces fine through the existing `showError(detail)` helpers on both desktop and mobile clients.
**Why:** Don't reinvent. The client toast already prepends nothing — it just shows `detail`. Anything more elaborate is YAGNI.

### Apply via decorators, not a middleware
**Choice:** Decorate the four endpoints individually:

```python
@app.post("/api/rooms")
@limiter.limit(RATE_LIMIT_CREATE)
async def create_room(request: Request, body: CreateRoomBody): ...
```

The `request: Request` parameter is required by slowapi to wire the key extraction.
**Why:** Explicit; the limit is visible at the endpoint definition. A blanket middleware would either rate-limit everything (including reads and WebSocket upgrade requests, which we explicitly want unlimited) or need a path matcher inside it (worse than decorators).

### Don't rate-limit anything else
**Choice:** Read endpoints (`GET /api/rooms/{code}`, mobile static routes, `/healthz` if present), the WebSocket upgrade and message traffic, and the host-gated endpoints (`/config`, `/start`, `/abort`, `/rematch`, `/leave`, `/remove_bot`, `/end_round`) are NOT rate-limited.
**Why:**
- Reads don't allocate new registry state. Worst case is bandwidth, which nginx can shed if needed.
- WebSocket: per-message engine logic already rejects illegal moves; the bot loop has its own cap; broadcast volume scales with seats (≤8), not with attacker effort.
- Host-gated endpoints require a valid `host_pid`. To abuse them you must first hold a host pid, which means you already passed the create-room limit.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Shared NAT (university, coffee shop) — many real users behind one IP get throttled together. | Quotas are sized for the worst legit case (multi-tab user, double-clicks). 30/min/IP for join is still enough for ~30 distinct users to retry once each per minute from one NAT. If we see a real report, bump the quota or move to a sliding-window backend. |
| `X-Forwarded-For` spoofing. | Nginx overwrites the header for inbound traffic; the app only listens on the loopback / private port that nginx forwards to. If someone bypasses nginx (a misconfig), they could spoof. Documented as an ops invariant, not an in-app check. |
| In-memory limiter state is lost on restart — a single deploy resets all buckets and could allow a burst. | Acceptable. Deploys are infrequent and the burst is bounded by the limit itself (worst case: one full quota per IP right after restart). |
| slowapi's default storage is process-local — won't work if we ever go multi-process. | Out-of-scope flag in the proposal. If we move to multiple workers (uvicorn `--workers > 1`), switch slowapi to its `redis://` storage. |
| Tests that previously hammered the API (e.g. fuzzing) now hit 429. | `PRINCESS_RATE_LIMIT_DISABLED=1` set by `conftest.py` for the default session. Only the targeted limiter smoke test opts in. |
| 429 detail is in English only. | The desktop + mobile clients are English-only today. Out of scope. |
| `slowapi` adds a small dep tree (limits, deprecated). | Both are small, pure-Python, no native deps. Pinned via `pyproject.toml`. |

## Migration Plan

1. **Add `slowapi`** to `pyproject.toml` / `requirements.txt`. `pip install -e .` locally.
2. **`princess/server.py`:**
   - Import `Limiter`, `_rate_limit_exceeded_handler`, `RateLimitExceeded`.
   - Add `_client_ip(request)` and module-level limit constants.
   - Construct `limiter = Limiter(key_func=_client_ip)`; honor the `PRINCESS_RATE_LIMIT_DISABLED` env var.
   - `app.state.limiter = limiter` and `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`.
   - Add `request: Request` parameter and `@limiter.limit(...)` decorator to the four endpoints.
3. **`tests/conftest.py`:** ensure `PRINCESS_RATE_LIMIT_DISABLED=1` is set before `princess.server` is imported (so default test runs are unaffected).
4. **New tests** in `tests/test_server.py`:
   - `test_create_room_rate_limit_engages` — pop the env var, build a fresh app, fire 10 creates, assert ≥1 is 429.
   - `test_rate_limit_disabled_via_env` — default session, 10 creates all return 200.
5. `black princess tests`, `pylint princess tests`, `pytest -q`, `openspec validate rate-limit-rooms --strict`.
6. **CHANGELOG `### Added`** + `### Changed` entries.
7. Deploy: no nginx changes. Confirm via prod logs that observed client IPs after deploy are real (not `127.0.0.1`).

Rollback: revert `server.py`, `requirements.txt`, `conftest.py`, and the test additions. The library is a single-import drop; no schema changes.

## Open Questions

- Should `/api/rooms/{code}/leave` also be rate-limited? **Recommendation:** no for v1. Leave is host-gated for the host (must abort) and unauthenticated for non-hosts, but the worst it does is shrink a seat list and broadcast a lobby. Not a flooding vector. Revisit if we see abuse.
- Should we rate-limit by `(IP, path)` or globally per IP? slowapi's `@limiter.limit(...)` is per-decorator (per-endpoint) per-IP, which is what we want — a user spamming `/join` doesn't consume their `/rooms` create budget.
- Whitelist for internal monitoring? **Recommendation:** no. Healthchecks should hit unlimited read endpoints; nothing internal should be hammering the limited writes.
