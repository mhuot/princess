## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/health-check-and-file-logs`.

## 2. App startup time

- [x] 2.1 In `princess/server.py`, capture `APP_STARTED_AT = time.monotonic()` at module import (top-level) so it's set as soon as the app is loaded. No FastAPI event handler is required.

## 3. `/healthz` endpoint

- [x] 3.1 In `princess/server.py`, add `GET /healthz` returning JSON:

  ```python
  @app.get("/healthz")
  def healthz():
      return {
          "status": "ok",
          "uptime_seconds": int(time.monotonic() - APP_STARTED_AT),
          "rooms": len(REGISTRY),
          "log_buffer_size": len(LOG_BUFFER),
      }
  ```

  Verify `REGISTRY` already supports `len()`; if not, add `__len__` to its class. Same for `LOG_BUFFER` (see task 4.1).

- [x] 3.2 Confirm the route is NOT swept up by the mobile-UA `/` redirect (it's `/healthz`, not `/`, so it should be fine — verify with a manual test in task 7).

## 4. `RingBufferHandler.__len__`

- [x] 4.1 In `princess/logging_config.py`, add `__len__` to `RingBufferHandler` returning `len(self._buffer)` under the lock. This is what `/healthz` calls.

## 5. JSON-line formatter

- [x] 5.1 In `princess/logging_config.py`, add a `JsonLineFormatter(logging.Formatter)` class:

  ```python
  class JsonLineFormatter(logging.Formatter):
      """Format log records as one JSON object per line (JSONL)."""

      def format(self, record: logging.LogRecord) -> str:
          payload = {
              "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
              "level": record.levelname,
              "logger": record.name,
              "message": record.getMessage(),
              "room": _room_code_from_logger(record.name),
          }
          if record.exc_info:
              payload["exc_info"] = self.formatException(record.exc_info)
          return json.dumps(payload, default=str)
  ```

  with a tiny helper:

  ```python
  _ROOM_LOGGER_PREFIX = "princess.room."

  def _room_code_from_logger(name: str) -> str | None:
      if name.startswith(_ROOM_LOGGER_PREFIX):
          return name[len(_ROOM_LOGGER_PREFIX):] or None
      return None
  ```

## 6. Opt-in rotating file handler

- [x] 6.1 In `setup_logging()`, after the stdout + ring buffer handlers are attached, read:
  - `PRINCESS_LOG_PATH` (string, default `""`)
  - `PRINCESS_LOG_MAX_BYTES` (int, default `10_485_760`)
  - `PRINCESS_LOG_BACKUP_COUNT` (int, default `5`)
- [x] 6.2 If `PRINCESS_LOG_PATH` is a non-empty string, attempt to construct a `RotatingFileHandler(path, maxBytes=…, backupCount=…)`. On success: set the resolved level, set formatter to `JsonLineFormatter()`, attach to root. On `OSError`: log a warning via the (already-attached) stdout handler and continue without the file handler. **Do not crash startup.**
- [x] 6.3 Include the file path in the existing "logging initialized" line when the file handler is active.

## 7. Tests

- [x] 7.1 In `tests/test_server.py`, add `test_healthz_returns_ok` — issue `GET /healthz`, assert status 200, assert body has `status == "ok"`, `uptime_seconds` is `int >= 0`, `rooms` is `int >= 0`, `log_buffer_size` is `int >= 0`.
- [x] 7.2 Add `test_healthz_reports_room_count` — create two rooms, hit `/healthz`, assert `rooms == 2`.
- [x] 7.3 Add `test_healthz_unaffected_by_mobile_ua` — issue `GET /healthz` with a mobile UA, assert 200 JSON (no 302).
- [x] 7.4 In `tests/test_logging_config.py` (create if it doesn't exist; otherwise extend the existing logging test file):
  - `test_no_file_handler_when_env_var_unset` — monkeypatch `PRINCESS_LOG_PATH` to be unset, reset `_princess_configured`, call `setup_logging()`, assert no `RotatingFileHandler` is on the root.
  - `test_file_handler_attached_when_env_var_set` — using `tmp_path`, set `PRINCESS_LOG_PATH=<tmp>/princess.log`, call `setup_logging()`, emit one INFO record, assert the file exists, read the line, `json.loads(line)`, assert required fields.
  - `test_file_handler_records_room_code` — emit a record from `logging.getLogger("princess.room.AB12")`, assert the JSON line has `"room": "AB12"`.
  - `test_file_handler_records_null_room_for_non_room_logger` — emit from `logging.getLogger("princess")`, assert `"room": null` (Python `None`).
  - `test_file_handler_includes_exc_info` — call `logger.exception("boom")`, assert the JSON line contains `"exc_info"` with `"Traceback"` in it.
  - `test_unwritable_path_fails_open` — set `PRINCESS_LOG_PATH` to a path under a non-existent directory, call `setup_logging()`, assert no exception is raised and no file handler is on the root.

  Each test that calls `setup_logging()` SHALL first clear `_princess_configured` and remove any handlers added by prior tests, to keep state isolated.

## 8. Docs

- [x] 8.1 In `README.md`, add (or extend an existing Ops section with) a `### Health check and logs` subsection covering:
  - `GET /healthz` shape and intended use (nginx upstream health, external monitors).
  - `PRINCESS_LOG_PATH`, `PRINCESS_LOG_MAX_BYTES`, `PRINCESS_LOG_BACKUP_COUNT` env vars and defaults.
  - A nginx snippet showing how to point a health check at `/healthz` (and a note that active health checks require nginx-plus; OSS nginx can still use `proxy_next_upstream`).
  - A docker-compose snippet showing the env var and a host-path mount for the log file.
- [x] 8.2 In `CHANGELOG.md` under `## [Unreleased]` `### Added`, append:
  - "`GET /healthz` endpoint returning `{status, uptime_seconds, rooms, log_buffer_size}` for nginx upstream health checks and external monitors. [health-check-and-file-logs]"
  - "Optional rotating JSON-line file logging via `PRINCESS_LOG_PATH` env var (default 10 MB × 5 backups, configurable via `PRINCESS_LOG_MAX_BYTES` and `PRINCESS_LOG_BACKUP_COUNT`). Stdout and the in-memory `/logs` viewer continue to use the human-readable format. [health-check-and-file-logs]"

## 9. Verify

- [x] 9.1 `black princess tests`.
- [x] 9.2 `pylint princess tests` → 10.00/10.
- [x] 9.3 `pytest -q` — all new tests pass.
- [x] 9.4 `openspec validate health-check-and-file-logs --strict`.
- [x] 9.5 Manual smoke (local): `curl http://localhost:8000/healthz` returns 200 JSON with sensible values.
- [x] 9.6 Manual smoke (local file logging): `PRINCESS_LOG_PATH=/tmp/princess.log uvicorn princess.server:app --reload`; create a room; `tail -f /tmp/princess.log` shows JSON lines with `"room"` populated.

## 10. Ship

- [x] 10.1 Commit: `health-check-and-file-logs: /healthz endpoint + opt-in JSONL file handler`.
- [x] 10.2 Push the branch; open a PR.
- [x] 10.3 Watch CI; auto-merge once green. Auto-deploy picks it up.
- [x] 10.4 Post-deploy verification: `curl https://<prod-host>/healthz`; on the host, confirm `/var/log/princess.log` is being written (assuming docker-compose sets `PRINCESS_LOG_PATH` and mounts the path).

## 11. Wrap up

- [x] 11.1 `openspec status --change health-check-and-file-logs` → all artifacts done.
- [x] 11.2 `/opsx:archive health-check-and-file-logs` after merge.
