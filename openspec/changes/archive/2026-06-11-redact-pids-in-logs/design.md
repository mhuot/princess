## Context

Authorization in Princess is bearer-token style: a seat is identified solely by its `pid` (`secrets.token_urlsafe(8)`), and the room host by `host_pid`. There is no separate session/cookie layer. These tokens are interpolated into log lines across `server.py` and `rooms.py` (room creation, joins, bot add/remove, rename, plays, pickups, bot steps, etc.), and the in-memory log buffer is exposed verbatim through `GET /api/logs` and `/api/logs/download`. The result: anyone who can read the buffer can lift live tokens and take over a seat or the room.

This change makes the buffer safe *by construction* — the raw tokens never enter it — rather than relying solely on locking down the endpoints. The two mitigations are complementary; this one is the durable floor.

Constraints: in-memory logging only (no DB), standard library only (no new deps), the `pid=<value>` field shape and per-room logger names must stay grep-friendly, and the live-tail viewer (`logs.html`) must keep working unchanged.

## Goals / Non-Goals

**Goals:**
- No raw `pid` / `host_pid` / `bot_pid` value ever appears in a buffered or stdout log line.
- The redacted token is **stable within a process run** so a single seat can still be followed across many lines (correlation/grep).
- The redacted token is **non-reversible** and **non-pre-computable** from log contents alone.
- One small, reusable helper; mechanical call-site updates; no behavior change to gameplay or HTTP/WS contracts.

**Non-Goals:**
- Adding authentication/authorization to the `/api/logs*` endpoints (tracked separately).
- Changing the token scheme itself, or how clients send/receive their own `pid`.
- Cross-process or cross-restart token stability (the buffer is ephemeral and in-memory; per-run stability is sufficient).
- Redacting room codes — a room `code` is not a credential and stays in clear text for operability.

## Decisions

**Decision: per-process-salted truncated SHA-256, emitted as `pid=<8 hex>`.**
A module-level helper `redact_pid(raw: str) -> str` returns `hashlib.sha256(_SALT + raw.encode()).hexdigest()[:8]`, where `_SALT` is a process-lifetime random value generated once at import via `secrets.token_bytes(16)`. Call sites keep the literal `pid=` prefix and pass `redact_pid(pid)` as the value (e.g. `"... pid=%s", redact_pid(seat.pid)`).

- *Why a hash over a per-room sequence index?* A sequence index requires per-room mutable state mapping `pid → n`, threaded through both `server.py` (which logs before/around a room exists, e.g. room creation) and `rooms.py`, plus eviction cleanup. A stateless pure function needs none of that and works identically everywhere, including server-level (non-room) log lines. The proposal allowed either; the hash is the lower-complexity, lower-risk choice.
- *Why salted?* The raw `pid` is only ~64 bits of entropy. Without a salt, an attacker who reads the log could pre-compute the hash of a guessed/known token and confirm correlations, or rainbow-table the space offline. A per-process random salt makes the digest meaningless outside the running process while preserving within-run stability.
- *Why 8 hex chars?* Enough to keep collisions negligible for the handful of concurrent seats (≤4 per room) while staying short and readable in the tail viewer. Collisions, if any, only blur correlation — they never expose a token.

**Decision: redact `bot_pid` and any other token-shaped field too.**
`bot_pid` (remove-bot), `host_pid` (every host-gated endpoint), and the seat `pid` in WS connect/disconnect all go through the same helper. The rule is "any value that is a `pid`," not "fields literally named pid."

**Decision: enforce with a test that scans the buffer.**
`tests/test_logging.py` gains a test that exercises representative flows (create room, join, add bot, play) and asserts no raw token returned by the API appears anywhere in `LOG_BUFFER.dump_text()`, plus a unit test that `redact_pid` is stable, non-raw, and differs from the input.

## Risks / Trade-offs

- [Correlation lost across restarts] The salt rotates each process start, so a `pid` logged before a restart won't match its post-restart digest. → Acceptable: the buffer is in-memory and cleared on restart anyway, so there is nothing to correlate across the boundary.
- [Missed call site leaks a token] A future `log(... pid=%s, raw_pid)` could reintroduce a leak. → The buffer-scanning test acts as a regression guard; reviewers also have the explicit spec requirement to point to.
- [Operator debugging friction] Support can no longer copy a `pid` out of the logs to reproduce as that user. → Intended; that capability *was* the vulnerability. Operators can still correlate by the stable redacted token and by room code.
- [Spec scenario wording] The existing logging spec scenario references `action rejected pid=…`; the prefix is unchanged (only the value is redacted), so that scenario still holds.

## Migration Plan

Pure code change, no data migration. Deploy is the standard container rebuild on push to `main`. Rollback is reverting the commit — there is no persisted state and no schema. The only externally observable difference is the value after `pid=` in logs, which no automated consumer depends on.

## Open Questions

None.
