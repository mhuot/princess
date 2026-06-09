## Why

Server restart wipes every active room and every in-progress round. The CI pipeline (`deploy-via-nginx-director`) ships every push to `main`, and each ship is an unconditional eviction: lobbies vanish, mid-round games drop their pile / hands / face-up assignments, finished games lose their `finished_order`, and every connected player gets a `1006` socket close they have no way to recover from. The deep-link auto-join sentinel (`pid` in `localStorage`) is useless — even if the client reconnects, the room is gone and `/join` 404s.

Today this is tolerated because the rooms are friend-group ephemeral. As soon as a single round runs longer than the deploy window — or a contributor wants to ship a fix *while* a game is live — restart-equals-wipe becomes the binding constraint on iteration speed. Persist the room state so a restart is invisible to players.

## What Changes

- **Embedded SQLite store** (stdlib `sqlite3`, sync, used from FastAPI via `asyncio.to_thread`) keyed by room code. Single table `rooms(code TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_ts REAL NOT NULL)` with the entire room serialized as a JSON blob in `payload`.
- **Write-through, not write-behind.** Every room-mutating path (REST + WS action + bot loop iteration + idle eviction) calls `REGISTRY.persist(room)` (insert/update) or `REGISTRY.forget(code)` (delete). Latency budget: a few ms per write on local disk; serialization stays a sync `json.dumps` of a dict tree. Write-behind is rejected — it adds a moving part (background flusher), risks losing the last N seconds on crash, and the disk cost of write-through is negligible for 4-player rooms.
- **Serialization helpers** added to engine classes: `Card.to_dict / from_dict`, `Player.to_dict / from_dict`, `Game.to_dict / from_dict`. The engine remains pure — these are mechanical mappings on `dataclass.asdict` plus enum-to-string round-trips. `GameConfig` already has `to_dict / from_dict`.
- **Room serialization** lives in `princess/rooms.py`: `Room.to_dict()` captures `code`, `host_pid`, `seats[].{pid,name,is_bot}` (socket is dropped — sockets are per-process), `config`, `game` (or `None`), and `last_activity_ts` translated to wall-clock via `time.time()` so it survives a restart. `Room.from_dict()` reconstructs the dataclass, sets `socket = None` on every seat, and rebases `last_activity_ts` onto the new process's `time.monotonic()` clock.
- **Restore on startup.** The FastAPI lifespan handler opens the DB, runs `CREATE TABLE IF NOT EXISTS`, reads every row, instantiates `Room` via `Room.from_dict`, and inserts into `REGISTRY._rooms`. Corrupt rows (JSON parse failure or schema mismatch) are logged and skipped — they don't block startup.
- **Reconnect flow is unchanged.** Clients hold their pid in `localStorage` (already shipped by `deep-link-auto-join`). After restart they redial `WS /ws/{code}/{pid}` — the room is back, the pid still matches a seat, and the existing connect path sends an initial `lobby` or `state` message just like a fresh load.
- **Idle eviction now persists.** `RoomRegistry.evict_idle()` already drops rooms from memory; extend it to also `DELETE FROM rooms WHERE code = ?` for each evicted code. `RoomRegistry.remove(code)` does the same.
- **DB file path** is configurable via the env var `PRINCESS_DB_PATH`, default `./princess.db`. Tests inject a temp path via a pytest fixture that swaps the registry's DB connection.
- **No migration story for v1.** There is no production data. If the schema changes after this ships, the deploy SHALL drop and recreate the `rooms` table. (Documented in `design.md` Open Questions for a follow-up if/when this matters.)

## Capabilities

### Modified Capabilities

- `room-server`: the single-process / restart-forgets-everything requirement is replaced with restart-survives-everything. New requirements cover the persistence write-through, restore-on-startup, idle-eviction-deletes, and DB path env var.

### New Capabilities

(none — this stays inside `room-server`; engine serialization helpers are an implementation detail, not a separately specced capability)

## Impact

- **Affected code:**
  - `princess/cards.py`: add `Card.to_dict() / Card.from_dict()` (or module-level helpers if `Card` is a frozen dataclass).
  - `princess/game.py`: add `Player.to_dict / from_dict`, `Game.to_dict / from_dict`. `Source` enum already round-trips through `Source(value)`. `GameConfig.to_dict / from_dict` exists.
  - `princess/rooms.py`:
    - `Room.to_dict() / from_dict()`.
    - `RoomRegistry` gains `_db_path: str | None`, `_conn: sqlite3.Connection | None`, `_open_db(path)`, `_init_schema()`, `persist(room)`, `forget(code)`, `restore_all() -> int`.
    - `create`, `remove`, and `evict_idle` call `persist` / `forget`.
  - `princess/server.py`:
    - FastAPI `lifespan` (or `@app.on_event("startup")`) opens the DB at `os.getenv("PRINCESS_DB_PATH", "./princess.db")` and calls `REGISTRY.restore_all()`.
    - Every REST handler and WS action that already mutates room state calls `REGISTRY.persist(room)` at the end (one line, inside the existing `room.lock` block).
    - The bot loop calls `persist` after each successful action broadcast.
  - `tests/conftest.py` (or local fixture): a `tmp_db` fixture that points `PRINCESS_DB_PATH` at `tmp_path / "test.db"` for each test, and a helper that resets `REGISTRY` to a clean state between tests.
  - `tests/test_persistence.py` (new): cases listed in tasks.md §6.
- **Affected APIs:** none in shape. New side effect on every write path. No new endpoints.
- **Docs touched:**
  - `CHANGELOG.md` `## [Unreleased]` `### Added`: rooms persist across restart.
  - `README.md` deploy / config notes: mention `PRINCESS_DB_PATH`.
- **Out of scope:**
  - Multi-process / multi-host registry. A single uvicorn worker continues to be the deployment topology; SQLite-on-one-host is the right level for now.
  - Player session reauthentication. Pid is still the only identity, still lives in client `localStorage`.
  - Migrations / Alembic. v1 schema is one table with a JSON blob; future schema changes drop-and-recreate until there's user data worth preserving.
  - Persisting WebSocket connection state. Clients reconnect — sockets are per-process and per-TCP.
  - Encryption at rest. The DB file holds room codes, names, and card state — nothing sensitive.
