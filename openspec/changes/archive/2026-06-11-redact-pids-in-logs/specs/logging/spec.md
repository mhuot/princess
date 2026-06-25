## ADDED Requirements

### Requirement: Session tokens are redacted in logs

No log entry — whether buffered in memory or mirrored to stdout — SHALL contain a raw session token. Wherever a `pid`, `host_pid`, or `bot_pid` value would be logged, the server SHALL emit a redacted token in its place. The redaction SHALL be:

- **Non-reversible**: the raw token MUST NOT be recoverable from the log contents.
- **Non-pre-computable**: the mapping MUST be salted with a value generated fresh per process run, so a reader cannot confirm or rainbow-table a guessed token.
- **Stable within a process run**: the same raw token MUST map to the same redacted value for the lifetime of the process, so a single seat can be correlated across multiple log lines.

The redacted value SHALL NOT equal the raw token. The `pid=<value>` field shape SHALL be preserved (only the value changes), and room `code` values — which are not credentials — SHALL continue to be logged in clear text.

#### Scenario: Raw tokens never reach the buffer

- **WHEN** a room is created, a seat joins, a bot is added, and a play is made
- **THEN** none of the raw `pid` / `host_pid` values returned to those clients appears anywhere in `GET /api/logs` output or the downloaded buffer

#### Scenario: Redacted token is stable and non-raw

- **WHEN** the same raw `pid` is logged on two separate lines within one process run
- **THEN** both lines carry the identical redacted value, and that value is not equal to the raw `pid`

#### Scenario: Redaction is salted per run

- **WHEN** the server process restarts and the same raw `pid` is logged again
- **THEN** the redacted value differs from the value produced before the restart

## MODIFIED Requirements

### Requirement: Instrumented events

The server SHALL emit at least one log entry for each of: room creation, seat join, bot addition, config update, game start, swap-phase set_face_up, every play attempt (success and rejection), every pickup, bot decisions, bot action results, the bot-loop safety cap firing, abort, rematch, leave, WebSocket connect, WebSocket disconnect, and unhandled WebSocket handler exceptions. Any session token (`pid`, `host_pid`, `bot_pid`) included in these entries SHALL be redacted per the "Session tokens are redacted in logs" requirement.

#### Scenario: Successful play yields an INFO entry

- **WHEN** a human play succeeds
- **THEN** the per-room logger emits an `INFO` line beginning with `action ok kind=play …`

#### Scenario: Rejected play yields a WARN entry

- **WHEN** a human play is rejected by the engine
- **THEN** the per-room logger emits a `WARNING` line beginning with `action rejected pid=…` and the value after `pid=` is the redacted token, not the raw `pid`
