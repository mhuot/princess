## MODIFIED Requirements

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

## ADDED Requirements

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
