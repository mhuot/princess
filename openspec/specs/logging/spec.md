## Purpose

The `logging` capability provides Princess's operational observability: a single in-memory FIFO ring buffer mirrored to stdout, a standardised log line format, per-room logger names, instrumentation of every game/room/WebSocket event, and HTTP endpoints (read / download / clear) that back the in-browser live-tail viewer. No log files are written to disk — the buffer is the source of truth.

## Requirements

### Requirement: In-memory FIFO ring buffer

The server SHALL maintain a single in-process FIFO log buffer with a fixed maximum capacity (default 2000 entries). When the buffer is full and a new entry is appended, the oldest entry SHALL be dropped. No log entries SHALL be written to the local filesystem by the application.

#### Scenario: Buffer evicts oldest on overflow

- **WHEN** the buffer is at capacity N and another record is emitted
- **THEN** the entry with the lowest id is dropped and the new record is appended

#### Scenario: No filesystem writes

- **WHEN** the application runs normally for any duration
- **THEN** no `.log` files are created anywhere under the project working tree

### Requirement: stdout mirror

The logger SHALL also mirror every record at or above the configured threshold (`LOG_LEVEL` env var, default `INFO`) to standard output, so the operator can `tail -f` the server in a terminal.

#### Scenario: INFO and above print to stdout by default

- **WHEN** the server logs an `INFO` record
- **THEN** the same formatted line appears on stdout

#### Scenario: DEBUG always buffered, only printed when level allows

- **WHEN** a `DEBUG` record is emitted with `LOG_LEVEL=INFO`
- **THEN** the record is appended to the in-memory buffer but NOT printed to stdout

### Requirement: Standard format

Every log entry SHALL be formatted as `"<timestamp> [<LEVEL>] <logger-name>: <message>"` with timestamp in `YYYY-MM-DD HH:MM:SS` form. The LEVEL token SHALL be left-padded to 5 characters.

#### Scenario: Format matches the standard

- **WHEN** a log line is rendered
- **THEN** it matches the pattern `\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[(DEBUG|INFO |WARN |ERROR|CRITI)\] [^:]+: .+`

### Requirement: Per-room logger names

Logs about a specific room SHALL use a logger named `princess.room.<code>` so an operator can grep one game out of a busy buffer.

#### Scenario: Room code appears in the logger name

- **WHEN** a play happens in room `AB12`
- **THEN** the resulting log line includes the substring `princess.room.AB12`

### Requirement: Instrumented events

The server SHALL emit at least one log entry for each of: room creation, seat join, bot addition, config update, game start, swap-phase set_face_up, every play attempt (success and rejection), every pickup, bot decisions, bot action results, the bot-loop safety cap firing, abort, rematch, leave, WebSocket connect, WebSocket disconnect, and unhandled WebSocket handler exceptions.

#### Scenario: Successful play yields an INFO entry

- **WHEN** a human play succeeds
- **THEN** the per-room logger emits an `INFO` line beginning with `action ok kind=play …`

#### Scenario: Rejected play yields a WARN entry

- **WHEN** a human play is rejected by the engine
- **THEN** the per-room logger emits a `WARNING` line beginning with `action rejected pid=…`

### Requirement: Paginated read endpoint

The server SHALL expose `GET /api/logs?since=<int>&limit=<int>` returning `{"entries": [...], "last_id": <int>, "capacity": <int>}`. Each entry SHALL have `id` and `line`. Only entries with `id > since` SHALL be returned, capped at `limit` (default 500). The endpoint SHALL be safe to poll.

#### Scenario: Returns only new entries after a cursor

- **WHEN** the buffer contains entries with ids 100–110 and the client requests `since=105`
- **THEN** the response `entries` contains exactly ids 106–110

### Requirement: Download endpoint

The server SHALL expose `GET /api/logs/download` returning the full current buffer as a `text/plain` response with `Content-Disposition: attachment; filename="princess.log"`. An empty buffer SHALL return a single-line placeholder rather than an empty body.

#### Scenario: Browser downloads as attachment

- **WHEN** the client requests `/api/logs/download`
- **THEN** the response carries `Content-Type: text/plain` and `Content-Disposition: attachment; filename="princess.log"`

### Requirement: Clear endpoint

The server SHALL expose `DELETE /api/logs` that empties the buffer and emits a single `INFO` entry recording the clear action.

#### Scenario: Clear empties the buffer

- **WHEN** the client calls `DELETE /api/logs`
- **THEN** the immediately subsequent `GET /api/logs?since=0` returns at most a single entry (the clear acknowledgement)

### Requirement: Idempotent setup

`setup_logging()` SHALL be safe to call multiple times. Subsequent calls SHALL detect prior configuration and exit without adding duplicate handlers.

#### Scenario: Re-call is a no-op

- **WHEN** `setup_logging()` is called twice in the same process
- **THEN** the root logger has only one stdout handler and one buffer handler
