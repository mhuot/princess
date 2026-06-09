## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/rate-limit-rooms`.

## 2. Dependency

- [x] 2.1 Add `slowapi` to `pyproject.toml` (and `requirements.txt` if present). Pin a recent minor (e.g. `slowapi>=0.1.9,<0.2`).
- [x] 2.2 `pip install -e .` (or `pip install -r requirements.txt`) and verify `python -c "import slowapi"` succeeds.

## 3. Server wiring

- [x] 3.1 In `princess/server.py`, add imports near the top:

  ```python
  import os
  from fastapi import Request
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.errors import RateLimitExceeded
  ```

- [x] 3.2 Define a `_client_ip(request: Request) -> str` helper that returns the first entry of `X-Forwarded-For` if present (stripped), otherwise `request.client.host`, otherwise the string `"unknown"`.
- [x] 3.3 Define module-level limit constants:

  ```python
  RATE_LIMIT_CREATE = "6/minute"
  RATE_LIMIT_JOIN = "30/minute"
  RATE_LIMIT_BOT = "20/minute"
  RATE_LIMIT_RENAME = "30/minute"
  ```

- [x] 3.4 Construct the limiter and disable it when the dev env var is set:

  ```python
  limiter = Limiter(key_func=_client_ip)
  if os.environ.get("PRINCESS_RATE_LIMIT_DISABLED") == "1":
      limiter.enabled = False
  ```

- [x] 3.5 After the `app = FastAPI(...)` line, wire the limiter into the app:

  ```python
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
  ```

## 4. Decorate the four endpoints

For each of the four endpoints below, add a `request: Request` parameter (positioned before the Pydantic body) and a `@limiter.limit(...)` decorator **between** the `@app.post(...)` route decorator and the function definition.

- [x] 4.1 `POST /api/rooms` (handler `create_room`) — `@limiter.limit(RATE_LIMIT_CREATE)`.
- [x] 4.2 `POST /api/rooms/{code}/join` (handler `join_room`) — `@limiter.limit(RATE_LIMIT_JOIN)`.
- [x] 4.3 `POST /api/rooms/{code}/bot` (handler `add_bot`) — `@limiter.limit(RATE_LIMIT_BOT)`.
- [x] 4.4 `POST /api/rooms/{code}/rename` (handler `rename_seat`) — `@limiter.limit(RATE_LIMIT_RENAME)`.

Confirm that none of the unmodified endpoints (`/config`, `/start`, `/abort`, `/rematch`, `/leave`, `/remove_bot`, `/end_round`, read endpoints, mobile static routes, WebSocket route) gained a `@limiter.limit` decorator.

## 5. Test scaffolding

- [x] 5.1 In `tests/conftest.py` (create if needed), set `PRINCESS_RATE_LIMIT_DISABLED=1` **before** the test client imports `princess.server`:

  ```python
  import os
  os.environ.setdefault("PRINCESS_RATE_LIMIT_DISABLED", "1")
  ```

## 6. Tests

- [x] 6.1 In `tests/test_server.py`, add:

  - `test_rate_limit_disabled_via_env` — with the default session env (`PRINCESS_RATE_LIMIT_DISABLED=1`), fire 10 sequential `POST /api/rooms` calls from the test client and assert every response is 200.
  - `test_create_room_rate_limit_engages` — temporarily clear `PRINCESS_RATE_LIMIT_DISABLED` (e.g. via `monkeypatch.delenv` plus a fresh app import using `importlib.reload`), then fire 10 sequential `POST /api/rooms` calls from a single client IP and assert at least one response is 429 with a `detail` field present in the JSON body. Restore env when done.

- [x] 6.2 (Optional spot-check, low priority) Add a quick assertion that the limiter's `key_func` returns the first XFF entry when the header is set, falls back to `request.client.host` otherwise. Can be a direct unit test against `_client_ip` with a stub `Request`.

## 7. Docs

- [x] 7.1 In `CHANGELOG.md` `## [Unreleased]` add under `### Added`:
  - "Per-IP rate limiting on the four room mutation endpoints — `POST /api/rooms` (6/min), `POST /api/rooms/<code>/join` (30/min), `POST /api/rooms/<code>/bot` (20/min), `POST /api/rooms/<code>/rename` (30/min). Limits are keyed by the first `X-Forwarded-For` entry (real client IP behind nginx). Set `PRINCESS_RATE_LIMIT_DISABLED=1` to bypass in dev/tests. [rate-limit-rooms]"
- [x] 7.2 In `CHANGELOG.md` under `### Changed` note that the four endpoints can now return **HTTP 429**.

## 8. Verify

- [x] 8.1 `black princess tests`.
- [x] 8.2 `pylint princess tests` → 10.00/10.
- [x] 8.3 `pytest -q` — expect green; the new tests pass and existing tests are unaffected (limiter disabled by default for the suite).
- [x] 8.4 `openspec validate --specs --strict` and `openspec validate rate-limit-rooms --strict`.
- [x] 8.5 Manual smoke: run the server locally with `PRINCESS_RATE_LIMIT_DISABLED` unset, `curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/api/rooms -H 'content-type: application/json' -d '{"name":"Mike"}'` ten times; expect a mix of 200 and 429 after the 6th call.
- [x] 8.6 Manual smoke (XFF): same command but with `-H 'X-Forwarded-For: 198.51.100.5'` from a second terminal — confirm the 198.51.100.5 bucket is independent of the local-IP bucket.

## 9. Ship

- [x] 9.1 Commit: `rate-limit-rooms: per-IP rate limits on create/join/bot/rename`.
- [x] 9.2 Push the branch; open a PR.
- [x] 9.3 Watch CI; auto-merge once green.

## 10. Wrap up

- [x] 10.1 `openspec status --change rate-limit-rooms` → all done.
- [x] 10.2 After deploy, tail nginx + app logs to confirm observed `X-Forwarded-For` values look like real public IPs, not `127.0.0.1`.
- [x] 10.3 `/opsx:archive rate-limit-rooms` after merge.
