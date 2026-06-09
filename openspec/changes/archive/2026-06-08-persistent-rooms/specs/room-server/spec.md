## MODIFIED Requirements

### Requirement: Single-process state

The room registry SHALL live in process memory for runtime access and SHALL also be backed by an embedded SQLite store so that server restart preserves every active room. The DB file path SHALL be read once at startup from the env var `PRINCESS_DB_PATH`, defaulting to `./princess.db`.

WebSocket connections SHALL NOT be persisted; clients reconnect via the existing `WS /ws/{code}/{pid}` path after restart and the registry's room entry is found by code.

#### Scenario: Restart preserves a lobby room

- **WHEN** a room is created and seats are added, then the server process is restarted against the same `PRINCESS_DB_PATH`
- **THEN** the registry contains the same room with the same `code`, `host_pid`, and `seats[].{pid, name, is_bot}`; `seat.socket` is `None` on every seat until clients reconnect

#### Scenario: Restart preserves an in-progress game

- **WHEN** a room with `room.game` not None (mid-round, mid-swap, or game-over) is persisted and the server is restarted
- **THEN** the restored `room.game` has the same `phase`, `current_index`, `swap_phase`, `game_over`, `pile`, `deck`, `last_actions`, `finished_order`, and per-player `hand` / `face_up` / `face_down` / `choose` / `ready` / `finished` state

#### Scenario: Restart preserves room config

- **WHEN** the host has updated `room.config` (e.g., turned `seven_on_seven` off) and the server restarts
- **THEN** the restored room's `config.to_dict()` equals the pre-restart value

#### Scenario: Reconnect after restart restores the player's view

- **WHEN** after a restart a client redials `WS /ws/{code}/{pid}` using the pid it kept in `localStorage`
- **THEN** the WS handler attaches the new socket to the matching seat and sends an initial `lobby` or `state` message reflecting the restored room

#### Scenario: Unknown DB path creates a fresh empty store

- **WHEN** the server starts with `PRINCESS_DB_PATH` pointing at a path that does not exist
- **THEN** the server creates the file, runs `CREATE TABLE IF NOT EXISTS rooms (...)`, and starts with an empty registry without raising

## ADDED Requirements

### Requirement: Write-through persistence on state change

Every code path that mutates a room SHALL persist the room to the SQLite store before returning. Mutating paths include: room creation, join, leave (with or without bot conversion), add bot, remove bot, rename, config update, start, abort, rematch, end_round, every successful WebSocket action (`play`, `pickup`, `set_face_up`), and every successful bot loop iteration.

Persistence SHALL be a single upsert of the full room payload keyed by `code`. The write SHALL run on a worker thread (via `asyncio.to_thread` or equivalent) so the event loop is not blocked on disk I/O.

A persistence failure (disk full, file locked, etc.) SHALL be logged at error level and SHALL NOT raise out of the handler — the in-memory room remains the source of truth, the next mutation will retry the write.

#### Scenario: Persist runs after a successful play

- **WHEN** a client sends a `play` action that the engine accepts
- **THEN** after the state broadcast, the row for that room's code in the `rooms` table has a `payload` reflecting the new `pile`, the new `hand`, and the new `current_index`

#### Scenario: Persist runs after a bot action

- **WHEN** the bot loop executes one action successfully
- **THEN** the room row in SQLite reflects the post-action state before the loop sleeps for the next bot turn

#### Scenario: Disk failure is non-fatal

- **WHEN** the persist call raises (simulated `sqlite3.OperationalError`)
- **THEN** the handler completes normally, the client receives its broadcast, and an error is logged with the room code

### Requirement: Restore rooms on startup

The server's lifespan startup hook SHALL open the SQLite store at `PRINCESS_DB_PATH`, run `CREATE TABLE IF NOT EXISTS`, read every row, reconstruct each row's `Room` (and its `Game`, if any) via `Room.from_dict`, and insert the result into the registry under the room's `code`.

Each restored `Seat` SHALL have `socket = None`. Each restored `Room` SHALL have a fresh `asyncio.Lock` and a `last_activity_ts` rebased onto the new process's `time.monotonic()` clock so that idle eviction continues to behave correctly across restart.

If a row's payload is invalid (JSON parse failure, missing required field, `from_dict` raises), the loader SHALL log an error including the room code and SHALL skip that row. A bad row SHALL NOT prevent startup or block other rows from loading.

#### Scenario: Two valid rows and one corrupt row

- **WHEN** the `rooms` table has three rows where one row's payload is malformed JSON
- **THEN** startup completes, the registry holds the two valid rooms, and the malformed row is logged at error level with its code

#### Scenario: Restored seats start disconnected

- **WHEN** a room with two seats is restored
- **THEN** every restored `Seat.socket` is `None` regardless of whether the seat was connected before the restart

#### Scenario: Restored room participates in idle eviction

- **WHEN** a restored room sits with no sockets attached for longer than `ROOM_IDLE_TIMEOUT_SECONDS`
- **THEN** the next eviction sweep removes it from the registry and deletes its row from SQLite (per the eviction requirement)

### Requirement: Eviction deletes persisted rows

When `RoomRegistry.evict_idle(...)` removes a room from the in-memory registry, it SHALL also `DELETE FROM rooms WHERE code = ?` for that room. Similarly, `RoomRegistry.remove(code)` SHALL delete the corresponding row.

#### Scenario: Idle eviction deletes the row

- **WHEN** a room is evicted by `evict_idle` for being idle past the timeout
- **THEN** the next call to `restore_all()` against the same DB does not surface that room

#### Scenario: Explicit remove deletes the row

- **WHEN** `RoomRegistry.remove("ABCD")` is called
- **THEN** the row with `code = "ABCD"` is no longer present in the `rooms` table

### Requirement: Room serialization shape

`Room.to_dict()` SHALL produce a JSON-serializable dict containing:

- `schema_version: 1` (integer, reserved for forward-compatible schema evolution)
- `code: str`
- `host_pid: str`
- `seats: list[{"pid": str, "name": str, "is_bot": bool}]` (sockets omitted)
- `config: dict` (the result of `GameConfig.to_dict()`)
- `game: dict | None` (the result of `Game.to_dict()` when `room.game` is not None, else `null`)
- `wall_last_activity_ts: float` (room's `last_activity_ts` translated to wall-clock via `time.time() - (time.monotonic() - last_activity_ts)`)

`Room.from_dict(d)` SHALL reconstruct the dataclass, set every `Seat.socket` to `None`, construct a fresh `asyncio.Lock`, parse `config` via `GameConfig.from_dict`, parse `game` via `Game.from_dict` when present (else leave `None`), and rebase `wall_last_activity_ts` back onto `time.monotonic()`.

The serializer SHALL be round-trip stable: for any `Room` produced through normal lifecycle operations, `Room.from_dict(Room.to_dict(r)).to_dict()` SHALL equal `Room.to_dict(r)` modulo the rebased `last_activity_ts`.

#### Scenario: Round-trip a lobby room

- **WHEN** a lobby room with four seats and a customized config is round-tripped through `to_dict / from_dict / to_dict`
- **THEN** the two `to_dict` outputs are equal in all fields except `wall_last_activity_ts` (which may differ by the round-trip duration)

#### Scenario: Round-trip a mid-round game

- **WHEN** a 3-player game with non-empty `pile`, partially dealt hands, and a non-empty `last_actions` list is round-tripped
- **THEN** `room.game.to_dict()` matches before and after, including `current_index`, `phase`, `pile`, `deck`, `last_actions`, and every player's `hand` / `face_up` / `face_down` / `finished` state

### Requirement: Engine serialization helpers

The engine modules SHALL expose pure `to_dict / from_dict` helpers for `Card`, `Player`, and `Game`. These helpers SHALL NOT import or depend on `sqlite3`, the FastAPI app, or the `RoomRegistry`. They SHALL operate purely on dataclass fields and produce JSON-serializable dicts.

`GameConfig.to_dict / from_dict` already exist and SHALL continue to be the source of truth for config round-tripping.

`Card.from_dict` SHALL accept the dict produced by `Card.to_dict` and reconstruct an equal `Card`. Similarly for `Player` and `Game`. `Game.from_dict` SHALL produce a `Game` whose `__init__` is bypassed (e.g., via `object.__new__(Game)`) so that setup-time work (dealing, shuffling) is not re-run on restore.

#### Scenario: Card round-trip

- **WHEN** any `Card` instance `c` is fed through `Card.from_dict(c.to_dict())`
- **THEN** the result equals `c` (same rank, same suit)

#### Scenario: Game from_dict skips setup

- **WHEN** a saved `Game` dict for a partially-played round is passed to `Game.from_dict`
- **THEN** the restored game's `pile`, `deck`, and per-player `hand` are exactly as saved (not re-dealt)

#### Scenario: Engine module has no DB import

- **WHEN** `princess/game.py` and `princess/cards.py` are imported
- **THEN** neither module imports `sqlite3` (verifiable by `import ast` inspection in a unit test)

### Requirement: DB file path is configurable

The server SHALL read the SQLite file path from the env var `PRINCESS_DB_PATH` once during startup. When the env var is unset, the path SHALL default to `./princess.db` (relative to the process working directory).

The path SHALL be read at startup only; subsequent changes to the env var SHALL NOT affect the running server.

Test code SHALL be able to override the path via a fixture that sets the env var or directly injects a connection into the registry, enabling per-test isolation via `tmp_path`.

#### Scenario: Default path is used when env unset

- **WHEN** the server starts with `PRINCESS_DB_PATH` unset
- **THEN** the SQLite file is created at `./princess.db` relative to the process working directory

#### Scenario: Env var overrides the path

- **WHEN** the server starts with `PRINCESS_DB_PATH=/tmp/foo.db`
- **THEN** the SQLite file is created at `/tmp/foo.db` and `./princess.db` is not touched

#### Scenario: Tests use a tmp_path DB

- **WHEN** a test uses the `tmp_db` fixture
- **THEN** the registry under test reads/writes a DB file inside the test's `tmp_path` and other tests' rooms are not visible
