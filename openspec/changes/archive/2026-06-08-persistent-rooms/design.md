## Context

`RoomRegistry` is an in-memory `dict[str, Room]`. Every restart drops the dict, every active room with it. The `room-server` spec today even codifies this:

> ### Requirement: Single-process state
> The room registry SHALL live entirely in process memory; no persistent store is required. Server restart SHALL forget all rooms.

That requirement was honest about the tradeoff but it's now the binding constraint on shipping. `deploy-via-nginx-director` runs on every push to `main` — the same loop the contributor uses to iterate. So the question stops being "should we persist?" and becomes "where in the stack, and how invasive is it?"

Engine state is the substantive part. A `Room` carries seats (trivial — three strings and a bool each), a `GameConfig` (already has `to_dict`), and an optional `Game`. `Game` is the deep tree: a `deck` (list of `Card`), a `pile` (list of `Card`), a `last_actions` list, and `players[].{hand, face_up, face_down, choose, ready, finished}`. None of these are circular; all are dataclasses of primitive fields plus `Card` (rank: int, suit: str-enum-ish). Round-tripping them through `dict ↔ json` is mechanical.

WebSocket sockets are explicitly not persistable. They live in the TCP stack of the old process. Clients already hold their pid in `localStorage` and the existing connect handler treats a redial as "send me current lobby/state" — that path becomes the reconnect path after restart with zero new code.

## Goals / Non-Goals

**Goals:**
- A `kill -9 $(pgrep -f princess)` followed by `python -m princess` leaves every active room intact: seats, host_pid, config, in-progress `Game` (deck, pile, hands, face_up, face_down, choose, ready, finished_pid list, swap_phase, game_over, last_actions, current player), and `last_activity_ts` (relative to wall-clock).
- The DB file is configurable and defaults to a sensible local path.
- Tests can run in parallel without sharing a DB.
- Engine module stays pure — no `sqlite3` imports inside `princess/game.py` or `princess/cards.py`.
- Idle eviction continues to work and now cleans up the DB.

**Non-Goals:**
- Multi-process / multi-host registry. One uvicorn worker per host stays the topology.
- Replay/replay-log style event sourcing. Snapshot of current state is enough.
- Schema migrations. v1 is one table; drop-and-recreate is the migration story until user data exists.
- Encryption / signed payloads. Local file; not a security boundary.
- Restoring WebSocket connections. Clients reconnect on their own; that's already specced.
- Persisting transient bot-loop in-flight state (the `asyncio.sleep(AI_THINK_SECONDS)` between decisions). If the server dies mid-bot-think, the room reloads, the next `run_bots()` (kicked by the first reconnecting client's action or a fresh `/start`-equivalent path) picks up where it left off — the engine state itself is durable; the loop wrapper is not.

## Decisions

### Embedded SQLite via stdlib `sqlite3`, called from a thread

**Choice:** `sqlite3` from the standard library. One connection opened at startup, passed into `RoomRegistry`. All calls wrapped in `await asyncio.to_thread(...)` to keep the event loop unblocked.

**Why:** Zero new dependencies. SQLite at single-writer scale (a 4-player room, a few writes per second per active room, never more than a handful of active rooms) is comfortably under its capacity. `aiosqlite` was considered and rejected — it adds a dependency for marginal benefit when each write is sub-millisecond and `asyncio.to_thread` is already idiomatic for "occasional sync I/O from async."

The connection uses `isolation_level=None` (autocommit) plus `PRAGMA journal_mode=WAL` so a writer doesn't block readers if/when we ever read concurrently. `check_same_thread=False` because the thread pool can hand the connection to any worker; safety is ensured by writes only happening under the per-room `asyncio.Lock`.

### Schema: one table, JSON blob payload

```sql
CREATE TABLE IF NOT EXISTS rooms (
  code TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_ts REAL NOT NULL
);
```

**Why:** The natural unit of persistence is "the whole room" — every state change touches enough of the tree that a relational decomposition is friction without payoff. JSON blob keeps serialization symmetric with the existing `view_for` / `public_lobby` style. `updated_ts` is bookkeeping (debugging, future "show me the most recent N rooms" tooling), not used for replay.

### Write-through on every state change, not write-behind

**Choice:** Every room-mutating path calls `await REGISTRY.persist(room)` at the end of its critical section. No background flusher.

**Why:** Write-behind buys nothing here:
- Crash window. Write-behind means the last N seconds of a game can vanish on a crash — exactly the failure mode we're fixing.
- Bot loop is the hot path and it already `await`s `AI_THINK_SECONDS` (0.6s) between actions. Add a sub-millisecond `to_thread` SQLite write on top — invisible.
- Human turns are paced by network round-trips (typically tens of ms). One extra disk write isn't measurable.
- Operational simplicity. No flusher to manage, no shutdown drain to remember.

### Engine modules add serialization helpers; persistence lives in `rooms.py`

**Choice:** `Card`, `Player`, `Game` get `to_dict / from_dict` (or module-level equivalents for frozen dataclasses). All `sqlite3` calls live in `princess/rooms.py`. `princess/game.py` never imports `sqlite3` or `json`.

**Why:** Two reasons. First, the engine has unit tests that should keep running without a DB. Second, `to_dict` is also useful for logging and ad-hoc debugging — separating the dict shape from the storage backend means a future swap (Postgres? Redis?) only touches `rooms.py`.

### Restore is best-effort; corrupt rows are logged and skipped

**Choice:** During startup, if a row's `payload` fails to parse or `Game.from_dict` raises, log the error with the room code and continue. Don't crash the process.

**Why:** A corrupt DB row should never prevent the server from coming back up — the contributor's blast radius for a serialization bug is then "the rooms that were active during the bad deploy" and not "we can't start the service." Production restart is a tighter loop than offline DB surgery.

### `last_activity_ts` is translated to wall-clock on persist, back to monotonic on restore

**Choice:** `to_dict` stores `wall_last_activity_ts = time.time() - (time.monotonic() - last_activity_ts)`. `from_dict` does the inverse against the new process's monotonic clock.

**Why:** `time.monotonic()` is intentionally not portable across processes (the spec promises only that it goes forward within one process). The idle-eviction check compares two monotonic values, so we want a fresh anchor each restart. Wall-clock is the bridge.

### `PRINCESS_DB_PATH` env var, default `./princess.db`

**Choice:** Read once at startup. No reload-at-runtime support.

**Why:** Matches every other config knob in the project (`ROOM_IDLE_TIMEOUT_SECONDS` etc.). The default lives next to the working directory; in deployment the systemd unit can point it at `/var/lib/princess/rooms.db` or wherever.

### Test fixture uses a per-test temp DB

**Choice:** `tmp_db` fixture sets `PRINCESS_DB_PATH` in `monkeypatch`, instantiates a fresh `RoomRegistry` against it, and yields it. After the test, the file goes away with `tmp_path`.

**Why:** Parallel tests, no shared state, the failure mode of "the previous test left rooms behind" disappears.

### `Game.from_dict` rebuilds, doesn't `__setstate__` hack

**Choice:** Explicit constructor — build the `Player` list, build the `deck` and `pile` lists of `Card`, then set the post-init fields (`current_index`, `phase`, `game_over`, `swap_phase`, `last_actions`, `finished_order`) by direct assignment after `__init__` completes.

**Why:** `Game.__init__` does setup work (deals cards, shuffles deck). We don't want to re-run setup on restore — we want the exact state we saved. The cleanest way is a classmethod `from_dict` that builds an empty `Game`-shaped object (via `object.__new__(cls)`) and assigns every field. This is the same pattern `dataclasses.replace` uses internally.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| `Game.from_dict` drifts from `Game.__init__` invariants as the engine evolves | Tests: a property-style "round-trip a played-out game and assert `to_dict(from_dict(d)) == d`" guards against silent drift. |
| SQLite file lock contention if a second process is accidentally started | Single-process is the documented deployment topology. WAL mode is enabled, so even if a stray reader connects, it doesn't block the writer. |
| Disk corruption (kernel panic mid-write) | SQLite's WAL is crash-safe for individual transactions. Worst case: one row is partially written → JSON parse fails → that one room is skipped on restore. Acceptable. |
| Serialization payload grows large for end-game rooms with long `last_actions` | `last_actions` is bounded (server-side trims to the last N actions). A 4-player round's full payload is < 50 KB even pathologically. SQLite is fine with that. |
| Pylint complains about `sqlite3` boilerplate | Keep the wrapper minimal; add targeted `# pylint: disable=` only where unavoidable. The existing pylint 10/10 bar is the gate. |
| A row written by an older binary blocks startup of a newer binary | `from_dict` defends with explicit `KeyError` handling → log and skip. The deploy continues; only the affected rooms vanish (not worse than today). |
| Test isolation if `REGISTRY` is a module-level singleton | Provide a `reset_registry()` helper used by the fixture; existing tests that don't use the fixture continue to work because they reset `REGISTRY._rooms` themselves. |

## Migration Plan

This is a "new behavior, no production data" change. The migration is:

1. Land the engine serializers (`Card`, `Player`, `Game`) with round-trip tests.
2. Land `Room.to_dict / from_dict` with round-trip tests.
3. Land `RoomRegistry` DB plumbing (open, init schema, persist, forget, restore_all) and unit tests against a `tmp_path` DB.
4. Wire `persist` calls into every mutating handler in `server.py` and into `run_bots`.
5. Wire `lifespan` startup to call `restore_all()`.
6. Integration test: start a room with a game, snapshot, simulate restart (new `RoomRegistry` against the same DB), assert state is identical.
7. Ship. First deploy lands the table-create; second-onward deploys hit the populated table.

Rollback: revert the change. Existing `princess.db` files become orphan disk; deleting them is a one-line cleanup. No client change is required for rollback because clients tolerate `/join` 404 (the pre-existing behavior).

## Open Questions

- **Should serialization version itself with a `schema_version` field inside the payload?** Recommendation: yes, default `1`. Future-proofs against the schema-evolution problem cheaply (one extra integer in the JSON). When/if a v2 lands, `from_dict` can branch.
- **Should we `VACUUM` or otherwise compact the file periodically?** Recommendation: no. Idle eviction already deletes rows; pages get reused. SQLite's auto-vacuum is sufficient. Reconsider if file size becomes an operational concern (it won't, at this scale).
- **Should `persist` errors be fatal or swallowed?** Recommendation: log error and continue. The room is still alive in memory, the next mutating call will retry the write. A persistent write failure (disk full) is a deploy-level problem, not something to crash the game over.
- **What about persisting `room.lock`?** Recommendation: don't. `asyncio.Lock` is process-bound; a fresh lock per restored room is correct.
- **Should we surface a `/api/admin/rooms` endpoint that lists persisted rooms for debugging?** Out of scope for v1. Easy follow-up if needed.
