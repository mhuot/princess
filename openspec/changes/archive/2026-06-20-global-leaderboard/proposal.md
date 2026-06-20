## Why

Today's `session-leaderboard` only counts Princess wins within a single live room — start a new room and the counters reset to zero. Players who come back across days have no way to see whether they're climbing or just churning. A persistent global leaderboard turns repeat play into something to chase, surfaces the bots-vs-humans tally honestly (humans only), and costs almost nothing on top of the SQLite store we already opened for `persistent-rooms`.

## What Changes

- **New `leaderboard` SQLite table** keyed by a normalized name (lowercased, trimmed, collapsed whitespace). Columns: `name_key`, `display_name`, `princess_wins`, `last_places`, `rounds_played`, `updated_ts`. Lives in the existing `PRINCESS_DB_PATH` database alongside `rooms`.
- **Bots are excluded.** Only seats with `is_bot = False` contribute to global counters. Bot names are randomized roasts; aggregating them would be noise.
- **Hooked into the existing game-over path.** When `_bump_scoreboard_if_needed()` records a finished game, the room also schedules an async upsert (one row per human seat involved). Idempotent via the same `_scoreboard_counted_for_game` marker.
- **New REST endpoint** `GET /api/leaderboard?limit=N&sort=wins|winrate|rounds` returns a JSON list ordered by the chosen key. Default `sort=wins`, `limit=50`, hard cap `limit=200`.
- **New static page** at `/leaderboard` (Hall of Princesses): top 50 by Princess wins with sortable columns, WCAG AAA contrast, mobile-responsive. Linked from the desktop footer and the mobile menu sheet.
- **No reset surface.** `/abort` does not reduce counts (aborted rounds never reached game-over so they were never counted). Operators clear via direct SQL.
- **Read-mostly.** The endpoint is rate-limited (60/min/IP via the existing slowapi limiter) and returns cached results refreshed every 5 seconds.
- **Spec updates** for `room-server` (write-through to leaderboard on game-over), `web-frontend` (footer link + page), `mobile-frontend` (menu link), and a new `global-leaderboard` capability owning the data model, endpoint, and page contract.

## Capabilities

### New Capabilities
- `global-leaderboard`: persistent cross-room win/loss aggregation, the `/api/leaderboard` REST endpoint, the `/leaderboard` HTML page, and the rules for what counts (humans only, idempotent per game).

### Modified Capabilities
- `room-server`: game-over hook also upserts the global leaderboard for every human seat in `finished_order`.
- `web-frontend`: desktop footer gains a "Hall of Princesses" link; new static page at `/leaderboard`.
- `mobile-frontend`: mobile menu sheet gains the same link; the leaderboard page is responsive so the link works on both.

## Impact

- **Code**: `princess/rooms.py` (new `_bump_global_leaderboard()` helper + table creation in `_open_db`), `princess/server.py` (new endpoint + static route), `static/leaderboard.html` + `static/leaderboard.js` + `static/leaderboard.css` (or extension of `styles.css`), `static/app.js` (footer link), `static/mobile.js` (menu link).
- **APIs**: new `GET /api/leaderboard`. No changes to existing WS payloads or REST endpoints.
- **Storage**: new `leaderboard` table in the existing SQLite DB. Forward-compatible: missing table → server creates it on boot; missing rows are treated as zero. No migration needed.
- **Docs**: README "Ops" section gains a Leaderboard subsection (env vars, table shape, clearing); `CHANGELOG.md` `[Unreleased]` gets a "Hall of Princesses" entry.
- **Tests**: new `tests/test_leaderboard.py` covering bump-on-game-over, bot exclusion, idempotency, endpoint payload, sort order, rate limit, and corruption resilience.
- **Naming policy**: every UI surface and code path says "Princess"; the inspiring game's vulgar name does not appear.
