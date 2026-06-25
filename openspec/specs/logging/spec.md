## Purpose

The `logging` capability provides Princess's operational observability: a single in-memory FIFO ring buffer mirrored to stdout, a standardised log line format, per-room logger names, instrumentation of every game/room/WebSocket event, and HTTP endpoints (read / download / clear) that back the in-browser live-tail viewer. No log files are written to disk — the buffer is the source of truth.

## Requirements

### Requirement: In-memory FIFO ring buffer

The server SHALL maintain a single in-process FIFO log buffer with a fixed maximum capacity (default 2000 entries). When the buffer is full and a new entry is appended, the oldest entry SHALL be dropped. The buffer's current entry count SHALL be exposed via `len(LOG_BUFFER)` so callers (e.g., `/healthz`) can report it without reaching into private attributes.

The application SHALL NOT write log entries to the local filesystem **unless** the opt-in file handler is configured via `PRINCESS_LOG_PATH` (see "Optional rotating file handler"). With the env var unset or empty, no `.log` files are created anywhere.

#### Scenario: Buffer evicts oldest on overflow

- **WHEN** the buffer is at capacity N and another record is emitted
- **THEN** the entry with the lowest id is dropped and the new record is appended

#### Scenario: No filesystem writes when file logging is disabled

- **WHEN** the application runs with `PRINCESS_LOG_PATH` unset or empty
- **THEN** no `.log` files are created anywhere under the project working tree

#### Scenario: Buffer exposes a length

- **WHEN** the buffer holds N entries
- **THEN** `len(LOG_BUFFER) == N`

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

### Requirement: Instrumented events

The server SHALL emit at least one log entry for each of: room creation, seat join, bot addition, config update, game start, swap-phase set_face_up, every play attempt (success and rejection), every pickup, bot decisions, bot action results, the bot-loop safety cap firing, abort, rematch, leave, WebSocket connect, WebSocket disconnect, and unhandled WebSocket handler exceptions. Any session token (`pid`, `host_pid`, `bot_pid`) included in these entries SHALL be redacted per the "Session tokens are redacted in logs" requirement.

#### Scenario: Successful play yields an INFO entry

- **WHEN** a human play succeeds
- **THEN** the per-room logger emits an `INFO` line beginning with `action ok kind=play …`

#### Scenario: Rejected play yields a WARN entry

- **WHEN** a human play is rejected by the engine
- **THEN** the per-room logger emits a `WARNING` line beginning with `action rejected pid=…` and the value after `pid=` is the redacted token, not the raw `pid`

### Requirement: Paginated read endpoint

The server SHALL expose `GET /api/logs?since=<int>&limit=<int>` returning `{"entries": [...], "last_id": <int>, "capacity": <int>}`. Each entry SHALL have `id` and `line`. Only entries with `id > since` SHALL be returned, capped at `limit` (default 500). The endpoint SHALL be safe to poll. Access SHALL be restricted to loopback clients (source IP `127.0.0.1` or `::1`); requests from any other source IP SHALL receive `403 Forbidden`.

#### Scenario: Returns only new entries after a cursor

- **WHEN** the buffer contains entries with ids 100–110 and a loopback client requests `since=105`
- **THEN** the response `entries` contains exactly ids 106–110

#### Scenario: Non-loopback client is rejected

- **WHEN** a request arrives at `GET /api/logs` from a non-loopback source IP
- **THEN** the server responds with HTTP 403 Forbidden

### Requirement: Download endpoint

The server SHALL expose `GET /api/logs/download` returning the full current buffer as a `text/plain` response with `Content-Disposition: attachment; filename="princess.log"`. An empty buffer SHALL return a single-line placeholder rather than an empty body. Access SHALL be restricted to loopback clients (source IP `127.0.0.1` or `::1`); requests from any other source IP SHALL receive `403 Forbidden`.

#### Scenario: Browser downloads as attachment

- **WHEN** a loopback client requests `/api/logs/download`
- **THEN** the response carries `Content-Type: text/plain` and `Content-Disposition: attachment; filename="princess.log"`

#### Scenario: Non-loopback client is rejected

- **WHEN** a request arrives at `GET /api/logs/download` from a non-loopback source IP
- **THEN** the server responds with HTTP 403 Forbidden

### Requirement: Clear endpoint

The server SHALL expose `DELETE /api/logs` that empties the buffer and emits a single `INFO` entry recording the clear action. Access SHALL be restricted to loopback clients (source IP `127.0.0.1` or `::1`); requests from any other source IP SHALL receive `403 Forbidden`.

#### Scenario: Clear empties the buffer

- **WHEN** a loopback client calls `DELETE /api/logs`
- **THEN** the immediately subsequent `GET /api/logs?since=0` returns at most a single entry (the clear acknowledgement)

#### Scenario: Non-loopback client cannot clear logs

- **WHEN** a request arrives at `DELETE /api/logs` from a non-loopback source IP
- **THEN** the server responds with HTTP 403 Forbidden and the buffer is unchanged

### Requirement: Idempotent setup

`setup_logging()` SHALL be safe to call multiple times. Subsequent calls SHALL detect prior configuration and exit without adding duplicate handlers.

#### Scenario: Re-call is a no-op

- **WHEN** `setup_logging()` is called twice in the same process
- **THEN** the root logger has only one stdout handler and one buffer handler

### Requirement: Optional rotating file handler

When the env var `PRINCESS_LOG_PATH` is set to a non-empty string, `setup_logging()` SHALL attach a `logging.handlers.RotatingFileHandler` to the root logger that writes to that path. When the env var is unset or empty, no file handler SHALL be installed (development default).

The handler SHALL use size-based rotation with the following defaults, each overridable via env var:

- `PRINCESS_LOG_MAX_BYTES` — bytes per file before rotation, default `10_485_760` (10 MB).
- `PRINCESS_LOG_BACKUP_COUNT` — number of rotated backups to keep, default `5`.

The handler's level SHALL match the root logger's level (driven by `LOG_LEVEL`, default `INFO`). The handler SHALL use the JSON-line format (see "JSON-line file format").

If the configured path cannot be opened (permission denied, directory missing, etc.), `setup_logging()` SHALL log a single warning to stdout describing the failure and continue without the file handler — the process SHALL NOT exit and the in-memory + stdout handlers SHALL still be installed.

#### Scenario: File handler installed when env var is set

- **WHEN** the process starts with `PRINCESS_LOG_PATH=/tmp/princess.log` and the path is writable
- **THEN** a `RotatingFileHandler` is attached to the root logger and subsequent log records are written to that file

#### Scenario: No file handler when env var is unset

- **WHEN** the process starts with no `PRINCESS_LOG_PATH` env var
- **THEN** the root logger has only the stdout handler and the in-memory ring buffer handler — no file handler

#### Scenario: Empty env var is treated as unset

- **WHEN** the process starts with `PRINCESS_LOG_PATH=""`
- **THEN** no file handler is installed

#### Scenario: Unwritable path fails open

- **WHEN** `PRINCESS_LOG_PATH=/root/forbidden.log` (or any unwritable path) is set
- **THEN** a single warning is emitted to stdout describing the open failure, no file handler is installed, and the server continues to run normally

#### Scenario: Size rotation respects the configured cap

- **WHEN** the file reaches `PRINCESS_LOG_MAX_BYTES`
- **THEN** the handler rotates to `<path>.1` and continues writing to `<path>`, keeping at most `PRINCESS_LOG_BACKUP_COUNT` rotated backups on disk

### Requirement: JSON-line file format

The optional file handler SHALL format each record as a single JSON object terminated by a newline (JSONL). The object SHALL contain at least the following fields:

- `ts` — ISO-8601 timestamp string with seconds precision (e.g., `"2026-06-08T12:34:56"`).
- `level` — uppercase level name (e.g., `"INFO"`, `"WARNING"`, `"ERROR"`).
- `logger` — the logger name (e.g., `"princess.room.AB12"`).
- `message` — the rendered log message (`record.getMessage()`).
- `room` — the 4-character room code extracted from logger names of the form `princess.room.<code>`, or `null` when the logger name does not match that pattern.

When the record carries exception info (`logger.exception(...)` or `exc_info=True`), the formatter SHALL include an additional `exc_info` field with the formatted traceback string.

Non-JSON-serializable values in the rendered message string SHALL never appear (the message is always already a string); any incidental non-serializable values in extra fields SHALL be coerced via `default=str` to avoid breaking the log line.

The stdout handler and the in-memory ring buffer SHALL continue to use the existing human-readable single-line format (`"<timestamp> [<LEVEL>] <logger-name>: <message>"`) — only the file handler emits JSON.

#### Scenario: File line is valid JSON with required keys

- **WHEN** an `INFO` record is emitted by logger `princess.room.AB12` with message `"hello"`
- **THEN** the corresponding line in the file is valid JSON containing `ts`, `level == "INFO"`, `logger == "princess.room.AB12"`, `message == "hello"`, and `room == "AB12"`

#### Scenario: Non-room logger has null room field

- **WHEN** an `INFO` record is emitted by logger `princess` (not a per-room logger)
- **THEN** the JSON line has `room == null`

#### Scenario: Exception records include exc_info

- **WHEN** code calls `logger.exception("boom")` and the file handler is active
- **THEN** the JSON line includes an `exc_info` field containing the formatted traceback string

#### Scenario: Stdout format unchanged

- **WHEN** any record is emitted with both stdout and file handlers active
- **THEN** stdout receives the existing `"<timestamp> [<LEVEL>] <name>: <message>"` line, while the file receives the JSON line
