## Why

After `deploy-via-nginx-director` landed, two operational gaps showed up. (1) Nginx has no real way to tell whether the Python upstream is alive — it just trusts the docker port. A misbehaving worker (deadlocked event loop, half-booted FastAPI) currently keeps serving 502s to users until somebody notices. (2) The in-memory FIFO log buffer is wiped on every deploy, which now happens automatically on each push to main. We can deploy a bug, lose the trail of what caused it, and have nothing to grep 10 minutes later.

Close both with one small change: an `/healthz` endpoint nginx (and any external uptime check) can probe, plus a rotating JSON-line file handler so a deploy doesn't take the history with it.

## What Changes

- **New `GET /healthz` endpoint** on the FastAPI app. Unauthenticated, cheap, no DB / engine work. Returns `200 {"status": "ok", "uptime_seconds": <int>, "rooms": <int>, "log_buffer_size": <int>}`. Intended for nginx upstream probes and external uptime monitors. Listed in the README ops section.
- **Optional rotating file handler** for the existing root logger. Activated when the env var `PRINCESS_LOG_PATH` is set to a writable path; otherwise skipped (so dev defaults are unchanged). Uses `logging.handlers.RotatingFileHandler` with size-based rotation (default 10 MB × 5 backups, configurable via `PRINCESS_LOG_MAX_BYTES` / `PRINCESS_LOG_BACKUP_COUNT`).
- **JSON-line format** for the file handler (`{"ts": …, "level": …, "logger": …, "message": …, "room": <code or null>}`). Hand-formatted via a `logging.Formatter` subclass — no new dependency. The stdout + in-memory handlers keep the existing human-readable format unchanged.
- **In-memory ring buffer + `/logs` viewer remain unchanged.** This change is purely additive; it does not move the source of truth.
- **README ops section** picks up `/healthz` and the two `PRINCESS_LOG_*` env vars. The production docker-compose / nginx example notes how to mount the host log directory and how to point nginx at `/healthz` for active health checks.

## Capabilities

### Modified Capabilities

- `room-server`: adds the unauthenticated `GET /healthz` endpoint.
- `logging`: relaxes the "no filesystem writes" rule to allow an **opt-in** rotating file handler controlled by `PRINCESS_LOG_PATH`, and adds a JSON-line format requirement scoped to that handler.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/server.py` — new `/healthz` route; track app start time at startup.
  - `princess/logging_config.py` — new `JsonLineFormatter`; opt-in `RotatingFileHandler` wired into `setup_logging()`; new env var reads.
  - `tests/test_server.py` — `/healthz` returns 200 with expected JSON shape.
  - `tests/test_logging_config.py` (or extend an existing logging test) — when `PRINCESS_LOG_PATH` is set to a tmp path, lines land in the file as JSON; when unset, no file handler is registered.
- **Affected APIs:** new `GET /healthz`. Existing endpoints unchanged.
- **Docs touched:** `README.md` (ops section — `/healthz`, env vars, nginx snippet), `CHANGELOG.md` `[Unreleased]` `### Added`.
- **Out of scope:**
  - Pushing logs to a remote aggregator (Loki, CloudWatch). File-on-disk is enough to grep through after a deploy.
  - A deep `/healthz` that pings external services — we have none.
  - Switching the in-memory format to JSON or replacing the `/logs` viewer.
  - Per-request access logs in JSON (uvicorn handles those; reformatting them is a separate concern).
