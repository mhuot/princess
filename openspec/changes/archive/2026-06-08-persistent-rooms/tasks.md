## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/persistent-rooms`.
- [x] 1.2 Confirm `python -m pytest -q` passes on a clean checkout (baseline before changes).

## 2. Engine serialization helpers

- [x] 2.1 In `princess/cards.py`, add `Card.to_dict() -> dict` returning `{"rank": <int>, "suit": <str>}` and `Card.from_dict(d) -> Card` reconstructing the dataclass. If `Card` is frozen, ensure `from_dict` uses the constructor (not field assignment).
- [x] 2.2 In `princess/game.py`, add `Player.to_dict() -> dict` and `Player.from_dict(d) -> Player`. Cover every field: `pid`, `name`, `hand`, `face_up`, `face_down`, `choose`, `ready`, `finished`. Use `Card.to_dict / from_dict` for card lists.
- [x] 2.3 In `princess/game.py`, add `Game.to_dict() -> dict` returning `{"players": [...], "config": <GameConfig.to_dict()>, "deck": [...], "pile": [...], "current_index": <int>, "phase": <str>, "swap_phase": <bool>, "game_over": <bool>, "last_actions": [...], "finished_order": [...]}`. Add `Game.from_dict(d) -> Game` using `object.__new__(Game)` to bypass `__init__` setup work, then assign every field directly.
- [x] 2.4 Confirm `princess/game.py` and `princess/cards.py` still have no `sqlite3` or `json` imports.

## 3. Room serialization

- [x] 3.1 In `princess/rooms.py`, add `Room.to_dict()` per the spec shape: `schema_version: 1`, `code`, `host_pid`, `seats` (drop `socket`), `config`, `game` (or `None`), `wall_last_activity_ts`.
- [x] 3.2 Add `Room.from_dict(d) -> Room`. Build the `Seat` list with `socket=None`. Construct a fresh `asyncio.Lock`. Parse `config` and `game`. Rebase `wall_last_activity_ts` onto `time.monotonic()`.
- [x] 3.3 Add a `_SCHEMA_VERSION = 1` module-level constant and use it in `to_dict`. Reject unknown versions in `from_dict` with a clear error message (logged and skipped at the loader level).

## 4. SQLite plumbing in `RoomRegistry`

- [x] 4.1 Add module-level constants: `DEFAULT_DB_PATH = "./princess.db"`, `CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_ts REAL NOT NULL)"`.
- [x] 4.2 Extend `RoomRegistry.__init__` to accept an optional `db_path: str | None`. Resolve at construction time (env-var fallback handled by the caller, see §5.1).
- [x] 4.3 Add `_open_db(path: str) -> sqlite3.Connection`: opens with `check_same_thread=False`, `isolation_level=None`, runs `PRAGMA journal_mode=WAL`, runs `CREATE_TABLE_SQL`.
- [x] 4.4 Add `async def persist(self, room: Room) -> None`. Body runs `await asyncio.to_thread(self._persist_sync, room.code, room.to_dict())`. The sync helper does `INSERT OR REPLACE INTO rooms VALUES (?, ?, ?)` with `json.dumps(payload)` and `time.time()`.
- [x] 4.5 Add `async def forget(self, code: str) -> None` that runs `DELETE FROM rooms WHERE code = ?` via `asyncio.to_thread`.
- [x] 4.6 Add `def restore_all(self) -> int` (sync, called from lifespan startup). Reads all rows, calls `Room.from_dict` for each, inserts into `self._rooms`, logs `info` per restored room. On `json.JSONDecodeError` / `KeyError` / `ValueError`, logs `error` with the code and continues. Returns the count of successfully restored rooms.
- [x] 4.7 Wire `persist` into `RoomRegistry.create` (after constructing the room).
- [x] 4.8 Wire `forget` into `RoomRegistry.remove`.
- [x] 4.9 Extend `evict_idle` to call a sync `_forget_sync` for each evicted code (eviction is itself sync; the registry's connection is shared).
- [x] 4.10 Wrap all `sqlite3` errors in handlers with `try/except sqlite3.Error` that log at error level and don't re-raise — the in-memory room stays the source of truth.

## 5. Server wiring

- [x] 5.1 In `princess/server.py`, add a FastAPI `lifespan` (or `@app.on_event("startup")`) that reads `PRINCESS_DB_PATH` from the environment (default `./princess.db`), opens the DB connection on `REGISTRY` (`REGISTRY._conn = REGISTRY._open_db(path)`), and calls `count = REGISTRY.restore_all()`. Log `info("restored %d rooms from %s", count, path)`.
- [x] 5.2 In each REST handler that mutates a room (`create_room`, `join_room`, `add_bot`, `remove_bot`, `update_config`, `start_game`, `abort_game`, `rematch`, `leave_room`, `rename_seat`, `end_round`), add `await REGISTRY.persist(room)` at the end of the critical section, inside the `room.lock` block, after the broadcast.
- [x] 5.3 In the WS message handler, add `await REGISTRY.persist(room)` after a successful `play` / `pickup` / `set_face_up` (after the broadcast, before `run_bots()`).
- [x] 5.4 In `Room.run_bots()`, add `await REGISTRY.persist(self)` after each successful broadcast. Use a deferred import inside the method to avoid a circular dependency between `rooms.py` and the registry singleton (or pass the persist callback in via a class-level reference).
- [x] 5.5 Confirm `REGISTRY.remove` and `REGISTRY.evict_idle` are still the only deletion paths, and both call `forget`.

## 6. Tests

- [x] 6.1 Add `tests/conftest.py` (or extend the existing one) with a `tmp_db` fixture that yields a fresh `RoomRegistry` bound to `tmp_path / "test.db"`. The fixture monkeypatches `princess.rooms.REGISTRY` for the duration of the test.
- [x] 6.2 Add `tests/test_persistence.py` with the following cases:
  - `test_card_round_trip` — every `Card` from a fresh deck round-trips through `Card.from_dict(Card.to_dict(c))` to an equal card.
  - `test_player_round_trip` — a `Player` with non-empty `hand`, `face_up`, `face_down`, `choose`, `ready=True`, `finished=False` round-trips.
  - `test_game_from_dict_skips_setup` — saved `Game` dict for a mid-round 3-player game restores with the exact `pile` / `deck` / hands, not re-dealt.
  - `test_room_to_from_dict_lobby` — a lobby room with 2 humans + 1 bot round-trips; sockets are `None` on restore.
  - `test_room_to_from_dict_in_progress` — a room with `room.game` mid-round round-trips; the restored game's state is identical.
  - `test_registry_persist_and_restore_lobby` — using `tmp_db`, create a room, persist it, instantiate a fresh registry against the same DB, call `restore_all()`, assert the room is back with the same seats/config.
  - `test_registry_persist_and_restore_mid_round` — same flow with `room.game` not None.
  - `test_registry_persist_after_join` — create + join + persist + restore; both seats are present.
  - `test_corrupt_row_is_skipped` — write a corrupt JSON row directly into the DB, plus a valid row; assert `restore_all()` returns 1, the valid room is loaded, and an error is logged for the corrupt code.
  - `test_evict_idle_deletes_row` — create a room, mark it idle, call `evict_idle`, assert the row is gone from SQLite.
  - `test_remove_deletes_row` — explicit `REGISTRY.remove(code)` removes the row.
  - `test_engine_modules_have_no_sqlite_import` — `import ast` walks `princess/game.py` and `princess/cards.py` and asserts no `sqlite3` import name appears.
  - `test_default_db_path` — with `PRINCESS_DB_PATH` unset, the lifespan startup creates `./princess.db` (use `tmp_path` as `cwd`).
  - `test_env_db_path_override` — with `PRINCESS_DB_PATH` set, the file is created at that path and the default is not touched.
  - `test_persist_error_is_logged_not_raised` — monkeypatch the registry's connection to raise `sqlite3.OperationalError` on write; trigger a mutating action; assert the handler completes and an error is logged.

## 7. Docs

- [x] 7.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Added`:
  - "Rooms now persist to a local SQLite store (default `./princess.db`, override via `PRINCESS_DB_PATH`). Server restart preserves seats, config, in-progress games, and `last_activity_ts`. Clients reconnect via the existing pid sentinel. [persistent-rooms]"
- [x] 7.2 In `README.md` (or the deploy section if it lives elsewhere), document the `PRINCESS_DB_PATH` env var and mention that the deploy unit should point it at a writable persistent path (e.g., `/var/lib/princess/rooms.db`).

## 8. Verify

- [x] 8.1 `black princess tests`.
- [x] 8.2 `pylint princess tests` → 10.00/10.
- [x] 8.3 `pytest -q` — expect green; the new persistence tests pass.
- [x] 8.4 `openspec validate persistent-rooms --strict`.
- [x] 8.5 Manual smoke: start the server, create a lobby in a browser, add a bot, start a game, play one round of cards, `kill -9` the server, restart, reload the browser tab — the game state and the player's hand SHALL be unchanged.

## 9. Ship

- [x] 9.1 Commit: `persistent-rooms: SQLite-backed registry; restart preserves rooms`.
- [x] 9.2 Push the branch; open a PR.
- [x] 9.3 Watch CI; merge once green.

## 10. Wrap up

- [x] 10.1 `openspec status --change persistent-rooms` → all done.
- [x] 10.2 `/opsx:archive persistent-rooms` after merge.
