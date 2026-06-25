## Why

Player session tokens (`pid`) and the host token (`host_pid`) are the only credentials Princess uses for authorization: knowing a seat's `pid` lets you act as that seat, and knowing `host_pid` lets you control the room. Today these raw tokens are written verbatim into the log buffer (room creation, joins, plays, bot steps, etc.), and the log buffer is served to anyone via `GET /api/logs` and `/api/logs/download`. That turns an unauthenticated log read into a room/host takeover. Redacting the tokens at the point of logging removes the credential leak regardless of who can read the buffer.

## What Changes

- Stop writing raw `pid` / `host_pid` values to any log entry. Every log call that currently interpolates a token SHALL instead emit a stable, non-reversible redacted token derived from the raw `pid`.
- Add a redaction helper in `logging_config` that maps a raw token to a short, deterministic, per-process-salted hash (so the same `pid` reads consistently within a run for grep/correlation, but the raw value cannot be recovered or pre-computed from the log).
- Keep the existing `pid=<value>` field shape so operators' habits and the live-tail viewer are unaffected; only the value changes from the raw token to the redacted token.
- This redaction is independent of (and complementary to) any future endpoint auth — it ensures the buffer is safe to expose by construction.

This is a **log-format change** for the token fields only; no API request/response shapes change and no gameplay behavior changes.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `logging`: The "Instrumented events" guarantee is amended so that emitted entries SHALL carry a redacted token in place of any raw `pid`/`host_pid`, and a new requirement defines the redaction contract (stable within a process, non-reversible, never the raw value).

## Impact

- **Code**: `princess/logging_config.py` (new redaction helper); `princess/server.py` and `princess/rooms.py` (every `log`/`room_logger` call that interpolates `pid`/`host_pid`/`bot_pid` switches to the redacted value).
- **Tests**: `tests/test_logging.py` (assert raw tokens never appear in buffered lines; assert redaction is stable and non-raw).
- **Docs**: `README.md` and `CHANGELOG.md` `[Unreleased]` section updated to note that logs now redact session tokens.
- **No dependency changes** (uses the standard-library `hashlib`/`secrets`).
- **No external surface change**: WebSocket/REST clients still send and receive their own raw `pid` over the wire; only what gets logged changes.
