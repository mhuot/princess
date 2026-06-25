## 1. Redaction helper

- [x] 1.1 In `princess/logging_config.py`, add a module-level per-process salt `_PID_SALT = secrets.token_bytes(16)` (import `secrets`).
- [x] 1.2 Add `redact_pid(raw: str) -> str` returning `hashlib.sha256(_PID_SALT + raw.encode()).hexdigest()[:8]`; import `hashlib`. Document that it is non-reversible and stable only within a process run.
- [x] 1.3 Handle empty/`None` input defensively (return a fixed placeholder rather than raising) so log calls never crash.

## 2. Update call sites

- [x] 2.1 In `princess/server.py`, wrap every logged `pid` / `host_pid` / `bot_pid` value with `redact_pid(...)` — covers create_room, join_room, add_bot, remove_bot, rename_seat, end_round, abort, leave, rematch, start_game, the WS connect/disconnect lines, and `_handle_message` play/pickup/set_face_up/unknown/rejected lines.
- [x] 2.2 In `princess/rooms.py`, wrap every logged `pid` value with `redact_pid(...)` — covers start_game, `_auto_pick_bot_face_up`, and all `run_bots` step/decision/result/error lines.
- [x] 2.3 Grep the package for `pid=%s`, `pid=%r`, and direct `.pid`/`host_pid`/`bot_pid` interpolation in log calls to confirm no raw token remains; leave room `code` logging untouched.

## 3. Tests

- [x] 3.1 In `tests/test_logging.py`, add a unit test that `redact_pid` is stable for one input, not equal to the input, and differs for different inputs.
- [x] 3.2 Add an integration test that drives create-room → join → add-bot → start → play (via the FastAPI test client / existing helpers) and asserts none of the raw `pid`/`host_pid` values returned by the API appear in `LOG_BUFFER.dump_text()`.

## 4. Docs & quality gates

- [x] 4.1 Update `README.md` and the `CHANGELOG.md` `[Unreleased]` section to note that logs now redact session tokens.
- [x] 4.2 Run `black`, `pylint` (≥8.0), and `pytest`; fix any findings.
- [x] 4.3 Run `openspec validate redact-pids-in-logs` and confirm it passes.
