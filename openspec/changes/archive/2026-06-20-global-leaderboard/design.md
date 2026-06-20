## Context

The `session-leaderboard` change (archived 2026-06-08) gave each room a per-pid `scoreboard` dict tracking `princess_wins`, `last_places`, and `rounds_played`. Counters reset whenever a room is created or aborted, so the leaderboard's "session" is really "this lobby until someone hits Abort." Repeat players have asked for something that survives — a Hall of Princesses they can come back to.

The `persistent-rooms` change (also 2026-06-08) already opens a SQLite database at `PRINCESS_DB_PATH`, creates the `rooms` table on startup, and routes writes through `asyncio.to_thread`. Reusing that connection is the obvious storage path; standing up a second store would mean another env var, another mount, and another corruption surface.

The game-over hook lives in `Room._bump_scoreboard_if_needed()` (`princess/rooms.py:115`). It's already idempotent via the `_scoreboard_counted_for_game` marker. That's the natural place to also bump the global table — every per-room bump is exactly one global bump, never zero, never two.

## Goals / Non-Goals

**Goals:**
- Persist Princess wins, last-place finishes, and rounds played across all rooms and all server restarts.
- Make the data viewable at `/leaderboard` without auth — public read, like the game itself.
- Stay forward-compatible: a server running an older schema must continue working after restart even if the leaderboard table is absent or empty.
- Keep the hot path (game-over) non-blocking. The SQLite write must not stall the WS broadcast.
- Exclude bots so the page tells the truth about humans.

**Non-Goals:**
- Per-user authentication or stable identity. Names are user-typed; anyone can claim any name. v1 collapses by normalized name and accepts the collision risk.
- Cross-server federation. One DB file, one server.
- Historical per-round logs. Counters only; replays/round-by-round history are not stored.
- Admin UI for clearing. Operators clear with `sqlite3 princess.db "DELETE FROM leaderboard"`.
- Win-streak, fastest-Princess, or any non-trivial stat beyond the three counters already tracked per session.

## Decisions

### Storage: extend existing SQLite, new table

New table created by `_open_db()`:

```sql
CREATE TABLE IF NOT EXISTS leaderboard (
    name_key       TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL,
    princess_wins  INTEGER NOT NULL DEFAULT 0,
    last_places    INTEGER NOT NULL DEFAULT 0,
    rounds_played  INTEGER NOT NULL DEFAULT 0,
    updated_ts     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_leaderboard_wins ON leaderboard (princess_wins DESC);
```

`name_key` is `display_name.strip().lower()` with internal whitespace collapsed to single spaces. Same connection, same WAL mode. **Alternative considered:** a separate DB file. Rejected — doubles the ops surface for one table.

### Identity model: normalized name, no auth

Aggregate by `name_key`. The most recently seen casing wins for `display_name`. **Alternative considered:** a stable per-browser cookie. Rejected — privacy footprint for a casual party game, and a name change would orphan history. Name collisions are real but acceptable; a future change can add optional accounts.

### Write path: piggyback on `_bump_scoreboard_if_needed`

After the existing in-memory bump, the room calls `await registry._bump_global_leaderboard(finished_order, name_by_pid, is_bot_by_pid)`. The registry resolves names + bot flags from the room's seats just before scheduling, and runs the upsert in `asyncio.to_thread`. **Alternative considered:** a background queue. Rejected — adds a process to monitor for one write every few minutes.

Failure mode: SQLite errors are caught and logged (same pattern as `persist()`), the game continues. The next game-over for any seat with that name will catch them up by absolute value, because we use `INSERT … ON CONFLICT DO UPDATE SET col = col + ?`.

### Bot exclusion

Filter in the room before calling the registry: only pids where `seat.is_bot == False` end up in the upsert batch. Tested explicitly so a regression in seat-flag plumbing doesn't quietly pollute the table.

### Read path: cached endpoint + static page

`GET /api/leaderboard?limit=N&sort=wins|winrate|rounds` returns up to 200 rows. Defaults: `limit=50`, `sort=wins`. `winrate` is `princess_wins / max(rounds_played, 1)` with a minimum-rounds filter (`min_rounds=5`) so a single lucky win doesn't top the chart. Results are cached in-memory for 5 seconds (`time.monotonic()`-keyed) so a refresh storm during a popular tournament doesn't hammer SQLite.

Rate limit: 60/min/IP via the existing slowapi limiter — generous enough for normal use, mean enough to deter scrapers.

### Page: static, accessible, no JS framework

`/leaderboard` is a vanilla HTML page (`static/leaderboard.html`) that fetches `/api/leaderboard` on load, renders a table with sortable column headers (client-side re-fetch with different `sort`), and links back to `/` and `/m`. Inherits the existing palette (deep purple, gold, near-white) and the WCAG AAA contrast tokens already in `styles.css`. Mobile breakpoint reuses the existing `@media (max-width: 600px)` block.

### Forward compatibility

`_open_db()` runs `CREATE TABLE IF NOT EXISTS leaderboard …` on every boot. Older deploys that miss this run get the table on next restart. The endpoint handles "table missing" by treating it as empty (same try/except shape as `persist`).

## Risks / Trade-offs

- **Name spoofing.** Two players can both call themselves "ProGamer" and merge. → Documented in the page footer ("Names are user-typed; this is a casual board, not a ranking system.") and in README. v2 could add optional accounts.
- **SQLite contention.** Game-over bumps + endpoint reads share the connection. → WAL mode is already on (set by `_open_db`); writers don't block readers. The 5s cache further damps read load.
- **Bot exclusion regressions.** If `is_bot` plumbing breaks, bots silently pollute the table. → Explicit test asserts that `_bump_global_leaderboard` is never called with a bot pid.
- **Display name churn.** A player who plays as "Alice" and later as "ALICE" sees the row flip casing on every game. → Acceptable; documented behavior. Both casings still count toward the same row.
- **Endpoint scraping.** Public, unauth, JSON. → 60/min/IP via slowapi (same limiter as `/api/rooms`). The 5s cache means scrapers can't drive load no matter how fast they ask.
- **Migration when adding columns later.** SQLite makes `ALTER TABLE … ADD COLUMN` cheap, but the bump SQL would need updating. → Out of scope for v1; reserved for follow-up changes.

## Migration Plan

1. Ship the proposal + specs + tasks (this change).
2. Implementer adds the table-creation SQL, the registry helper, the endpoint, the static page, and the link affordances.
3. First server restart after deploy creates the `leaderboard` table on the existing DB file. No backfill — counters start at zero, which is exactly what the page should say at launch.
4. Rollback: revert the deploy. The `leaderboard` table remains in the DB but is unused; the next deploy of this change resumes counting.

## Open Questions

- **Should `winrate` show a confidence band?** A Wilson interval would be honest but visually noisy on a phone. Default v1: plain ratio with a `min_rounds=5` floor.
- **Display name choice when casings disagree.** Last-write-wins is simplest. Alternative: most-frequent casing. Deferred — last-write-wins for v1.
