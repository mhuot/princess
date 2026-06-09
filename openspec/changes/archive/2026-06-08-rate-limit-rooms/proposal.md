## Why

Today every public mutation endpoint on Princess is unauthenticated and uncapped. Two specific endpoints are abusable:

- **`POST /api/rooms`** — a script can fire it in a tight loop and create thousands of rooms. Each room sits in process memory until the 5-minute idle eviction kicks in. With a few thousand requests/sec the registry balloons, GC churns, and the single-process FastAPI server starts dropping legit traffic.
- **`POST /api/rooms/{code}/join`** — room codes are 4 characters of `[A–Z0–9]`, ~1.7M permutations. A scripted enumerator at 1000 req/s sweeps the whole namespace in under 30 minutes and can join real lobbies as a spam seat. Worse, it's a way to *find* live rooms to grief.
- **`POST /api/rooms/{code}/bot`** and **`POST /api/rooms/{code}/rename`** — once an attacker is in a lobby, both endpoints mutate broadcast state. Rename in particular triggers a fresh state broadcast to every connected socket, so a tight loop amplifies traffic to all peers.

The fix is a small, well-known FastAPI-friendly rate limiter that caps requests **per client IP** on the mutating endpoints. Read endpoints (`GET /api/rooms/{code}`) and WebSocket message traffic stay unlimited — the abuse vector is HTTP-level scripting, not in-game play.

## What Changes

- **Add the `slowapi` dependency** (Flask-Limiter clone for Starlette/FastAPI). In-memory backend; no Redis. Works with a single-process FastAPI app, which is how Princess is deployed.
- **Wire up `Limiter` in `princess/server.py`** with a `key_func` that extracts the real client IP from `X-Forwarded-For` (set by nginx) and falls back to `request.client.host` if the header is absent.
- **Apply per-IP limits to four endpoints:**
  - `POST /api/rooms` — **6 / minute / IP** (allows accidental double-clicks; blocks scripted room flooding).
  - `POST /api/rooms/{code}/join` — **30 / minute / IP** (covers legit retry on the wrong code; blocks scripted code enumeration).
  - `POST /api/rooms/{code}/bot` — **20 / minute / IP** (a host normally adds 1–3 bots; 20 is plenty).
  - `POST /api/rooms/{code}/rename` — **30 / minute / IP** (humans never rename that fast; blocks broadcast-amp loops).
- **All other endpoints (read endpoints, config, start, abort, rematch, leave, remove_bot, end_round, mobile static, WebSocket lifecycle) remain unlimited.** They either don't allocate unbounded state or are gated by host authorization.
- **429 response shape:** when slowapi rejects, the response is `HTTP 429` with JSON body `{"detail": "rate limit exceeded: <limit>"}`. Existing client error helpers (`showError("lobby-error", e.detail)` desktop, `showError(e.detail)` mobile) already render `detail` so no UI change is required.
- **Dev/test override:** environment variable `PRINCESS_RATE_LIMIT_DISABLED=1` disables all limits at startup. Test suite sets it so existing tests aren't disturbed; a single new smoke test unsets it to verify the limiter actually engages.
- **Tests:** one smoke that fires 10 back-to-back `POST /api/rooms` requests and asserts at least one returns 429. Spot-check that the override env var disables enforcement.

## Capabilities

### Modified Capabilities

- `room-server`: `POST /api/rooms`, `/join`, `/bot`, `/rename` enforce per-IP rate limits with a documented quota; 429 is added to the set of possible responses.

### New Capabilities

(none — this is a hardening of existing endpoints.)

## Impact

- **Affected code:**
  - `pyproject.toml` / `requirements.txt`: add `slowapi`.
  - `princess/server.py`:
    - Build a `Limiter` instance with a custom `key_func` that prefers the first IP in `X-Forwarded-For` (nginx-trusted) and falls back to `request.client.host`.
    - Register `_rate_limit_exceeded_handler` on the FastAPI app for `RateLimitExceeded`.
    - Decorate the four endpoints with `@limiter.limit("…")`. Each handler signature gains a `request: Request` parameter (slowapi reads the key from `request.state`).
    - At startup, if `os.environ.get("PRINCESS_RATE_LIMIT_DISABLED") == "1"`, set `limiter.enabled = False`.
  - `tests/test_server.py`:
    - `test_create_room_rate_limit_engages` — temporarily clear `PRINCESS_RATE_LIMIT_DISABLED`, fire 10 creates, assert at least one is 429.
    - `test_rate_limit_disabled_via_env` — with `PRINCESS_RATE_LIMIT_DISABLED=1` (the test default), the same 10 creates all return 200.
  - `tests/conftest.py` (or equivalent): set `PRINCESS_RATE_LIMIT_DISABLED=1` for the default test session so other tests aren't affected by background limits.
- **Affected APIs:** four endpoints may now return **429** in addition to their existing responses.
- **Docs touched:** `CHANGELOG.md` `### Added` (per-IP rate limiting on create/join/bot/rename) and `### Changed` (the four endpoints can now return 429).
- **Deploy / ops:** no new infra; in-memory backend. The nginx config already forwards `X-Forwarded-For`, so the IP extractor works out of the box. If we ever scale to multi-process / multi-host, the limiter will need a shared backend (Redis) — flagged as out-of-scope.
- **Out of scope:**
  - Distributed limiter backend (Redis / memcached). Single-process FastAPI today.
  - Per-account / per-pid limits. We don't have accounts.
  - Limits on WebSocket messages. The engine itself rejects illegal actions and the bot loop is already capped.
  - Sliding-window vs fixed-window precision tuning. The default fixed-window is fine for these magnitudes.
  - CAPTCHA or proof-of-work. Out of proportion to the threat.
  - Per-endpoint admin-overridable limits. Constants in code; bump via PR if needed.
