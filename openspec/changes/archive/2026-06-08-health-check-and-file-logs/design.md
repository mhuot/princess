## Context

Princess runs as a single FastAPI/uvicorn process behind nginx (set up by `deploy-via-nginx-director`). The deploy pipeline rebuilds and restarts the container on every push to main, in ~15s. Two operational consequences:

1. Nginx currently has no way to tell whether the upstream is actually serving — it relies on the docker socket being up. A booting process that has bound its port but hasn't finished setup will get traffic and 502 it.
2. The in-memory log buffer in `princess/logging_config.py` is the only durable history. Every deploy wipes it. By the time a user reports "something broke a minute ago", the relevant logs may already be gone.

Both fixes are small and orthogonal. Doing them together because they're the natural follow-up to the deploy change and they share zero risk surface.

## Goals / Non-Goals

**Goals:**
- A `GET /healthz` that nginx or an external monitor can probe cheaply, returning 200 on a basic liveness check with a small amount of diagnostic JSON.
- Persist log entries to a rotating file when configured, so a deploy doesn't take history with it. JSON lines so we can grep + jq.
- Keep the development experience unchanged — file logging is opt-in via env var.
- Keep the existing in-memory buffer + `/logs` viewer as the primary surface; the file is a backup for grepping past deploys.

**Non-Goals:**
- A deep health probe that exercises every subsystem. The Python process can answer = it can serve.
- Authentication on `/healthz`. It's deliberately public and cheap.
- Shipping a log aggregator client (Loki, CloudWatch, Datadog). File-on-disk is sufficient for the current scale.
- Reformatting stdout or the in-memory buffer to JSON. The human-readable single-line format is what the operator wants when tailing or reading `/logs`.
- Per-request access logging — uvicorn handles that and reformatting is a separate concern.

## Decisions

### `/healthz` returns JSON, not just an empty 200
**Choice:** `{"status": "ok", "uptime_seconds": <int>, "rooms": <int>, "log_buffer_size": <int>}`.
**Why:** The 200 itself is what nginx's `proxy_next_upstream` / external monitors care about, but the diagnostic payload is free to add and gives a human running `curl <host>/healthz` something useful. Three small counts cover the typical questions ("is the room registry populated?", "how much in-memory log history do I have?", "when was the last deploy?"). All three are O(1) — no iteration, no locking beyond what the existing buffer already does.

### Endpoint path is `/healthz`, not `/health` or `/api/health`
**Choice:** `/healthz`.
**Why:** Convention from Kubernetes / GCP / many load balancers. Operators recognize it instantly. Also avoids any chance of colliding with future `/api/...` resources or being mis-redirected to the mobile UI (the `/m` redirect rule only matches `/` and `/room/{code}`).

### Endpoint is unauthenticated
**Choice:** No host_pid, no header, no rate limit.
**Why:** Health probes need to be cheap and stateless. There's no information leaked (room count and uptime are public-ish facts). Rate limiting is nginx's job if it ever becomes a problem.

### File handler is opt-in via env var, defaults to off
**Choice:** `PRINCESS_LOG_PATH` env var. Set → install handler. Unset/empty → skip.
**Why:** Dev should not litter the working tree with log files. Prod sets the var (in docker-compose) and gets persistence. Tests can point it at a tmp path for assertion. Matches the existing `LOG_LEVEL` pattern.

### Use `RotatingFileHandler` (size-based), not `TimedRotatingFileHandler` (daily)
**Choice:** `RotatingFileHandler(maxBytes=10 MB, backupCount=5)` by default. Configurable via `PRINCESS_LOG_MAX_BYTES` and `PRINCESS_LOG_BACKUP_COUNT`.
**Why:** Size-based bounds the disk footprint predictably — 5 × 10 MB = 50 MB max regardless of traffic. A bursty deploy day on a daily rotation could fill the host. Daily windows are nice for grepping by date, but the JSON `ts` field gives us that for free.

### JSON line format, hand-formatted by a `logging.Formatter` subclass
**Choice:** Subclass `logging.Formatter`; emit `json.dumps({"ts": iso, "level": …, "logger": …, "message": …, "room": <code or null>})`. No new dependency on `python-json-logger`.
**Why:** Four fields plus optional room code is trivial to format ourselves. `python-json-logger` adds maintenance surface for ~20 lines of code we can write. The `room` field is extracted from the logger name (`princess.room.<code>`) so per-room grepping with `jq 'select(.room=="AB12")'` works without changing call sites.

### Stdout and the ring buffer keep the existing human-readable format
**Choice:** Only the new file handler emits JSON. Stdout + `RingBufferHandler` keep `LOG_FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"`.
**Why:** Operators tailing the container logs and the `/logs` viewer both want one-line readability. JSON is for the deploy-spanning grep use case.

### `setup_logging()` stays idempotent and central
**Choice:** All wiring lives in `princess/logging_config.py:setup_logging()`. The new handler is built and attached inside the existing "already configured?" guard.
**Why:** The current code already handles the multi-call case; piggybacking keeps the surface area small and makes test isolation easy (reset the `_princess_configured` flag, point env at tmp).

### `/healthz` payload includes `uptime_seconds` derived from a module-level start time captured at FastAPI startup
**Choice:** Capture `APP_STARTED_AT = time.monotonic()` in a FastAPI `@app.on_event("startup")` handler (or via a module-level constant set in `server.py` at import). `uptime_seconds = int(time.monotonic() - APP_STARTED_AT)`.
**Why:** Lets operators sanity-check "is this the freshly-deployed process?" without exec'ing into the container. Monotonic clock avoids skew if the host time changes.

### `log_buffer_size` is the *current* count, not the buffer capacity
**Choice:** Expose `len(LOG_BUFFER._buffer)`. Add a public `__len__` so we don't reach into a private attr.
**Why:** Capacity is fixed at 2000 (and documented in the logging spec); the live count is the actually-useful diagnostic ("how much history do I have left?").

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| `/healthz` payload leaks more state than intended (room count) | Room count is already implicit from public usage. No PII, no pids, no codes. |
| File handler fails to open the configured path (perm denied, dir missing) | `setup_logging()` catches `OSError` on handler construction, logs a single warning to stdout, continues without the file handler. Service stays up. |
| Disk fills despite rotation (e.g. backupCount misconfigured to 0) | The default of 5 backups × 10 MB caps at 50 MB. A misconfigured value affects only this host; documented in README. |
| JSON formatter breaks on a message containing non-serializable types (e.g. a logged exception's `args` tuple) | Format only the rendered message string (`record.getMessage()`), never the raw `args`. `json.dumps(..., default=str)` as a belt-and-braces. |
| Nginx active health checks aren't in the open-source nginx build | We don't *require* active health checks. `/healthz` is also useful for `proxy_next_upstream` retry logic and any external uptime monitor (Uptime Robot, etc.). The README notes both. |
| Test for file-handler emits leaves a file on disk if cleanup misses | Use `tmp_path` fixture (pytest); the directory is auto-cleaned. |

## Migration Plan

1. **`princess/logging_config.py`:** add `JsonLineFormatter`, add `__len__` to `RingBufferHandler`, extend `setup_logging()` to install the file handler when `PRINCESS_LOG_PATH` is set. Wrap in try/except to fail open.
2. **`princess/server.py`:** capture app start time; add `GET /healthz` returning the diagnostic JSON.
3. **Tests:** unit-test the `/healthz` shape and the JSON formatter; integration-test the opt-in file handler via `tmp_path` and env-var monkeypatching.
4. **`README.md`:** add an "Ops" subsection (or extend the existing deploy section) covering `/healthz`, the three `PRINCESS_LOG_*` env vars, and a small nginx snippet showing how to point a health check at the upstream.
5. **`CHANGELOG.md`** `[Unreleased]` `### Added`.
6. `black princess tests`, `pylint princess tests`, `pytest -q`, `openspec validate health-check-and-file-logs --strict`.
7. Commit, push, CI, merge — the auto-deploy picks it up.
8. Verify post-deploy: `curl https://princess.<host>/healthz`, `ls -la /var/log/princess.log` on the host.

Rollback: revert `princess/logging_config.py` and the `/healthz` route in `server.py`. No schema or persistent data change.

## Open Questions

- Should `/healthz` also surface `git_sha` (built into the image at CI time)? **Recommendation:** worth doing as a tiny follow-up — read from a `PRINCESS_GIT_SHA` env var injected by the CI build, default to `"unknown"`. Defer to a later change so this one stays minimal.
- Should the file format include the structured exception (stack, type) when `logger.exception(...)` is used? **Recommendation:** yes — populate an `exc_info` field when `record.exc_info` is present. Cheap, handled inside `JsonLineFormatter`. Included in the spec.
- Daily rotation as a future option (env var `PRINCESS_LOG_ROTATION=size|daily`)? **Recommendation:** not now. Add only if an operator asks. Size-based covers the deploy-spanning-history use case.
