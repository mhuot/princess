## Why

The log buffer exposes every player name, room code, game action, and — until the companion `redact-pids-in-logs` change lands — raw session tokens to anyone who can reach `GET /api/logs` or `/api/logs/download` on the public URL. Restricting those endpoints to requests arriving on the loopback interface (127.0.0.1 / ::1) ensures they are only reachable by an operator with shell access to the host, eliminating the unauthenticated external read surface entirely.

## What Changes

- `GET /api/logs`, `GET /api/logs/download`, and `DELETE /api/logs` will return **403 Forbidden** for any request whose source IP is not a loopback address.
- A lightweight FastAPI dependency `require_localhost` will be applied to those three routes; no other routes are affected.
- The restriction applies at the application layer (no nginx or firewall change required), so it works identically in local dev, Docker, and any future deployment topology.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `logging`: The read, download, and clear endpoints gain a localhost-only access requirement; their response contract is otherwise unchanged.

## Impact

- **Code**: `princess/server.py` — new `require_localhost` dependency added to the three `/api/logs*` route definitions.
- **Tests**: `tests/test_server.py` (or `tests/test_logging.py`) — assert 403 for non-loopback clients on all three endpoints; assert loopback clients still succeed.
- **Docs**: `README.md` and `CHANGELOG.md` `[Unreleased]` section updated to note that the log endpoints are now restricted to localhost.
- **No new dependencies** — uses only FastAPI's existing `Request` object and `HTTPException`.
- **No external surface change** for gameplay: all `/api/rooms*` and `/ws/*` routes are unaffected.
