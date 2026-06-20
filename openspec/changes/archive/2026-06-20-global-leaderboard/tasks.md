## 1. Persistence layer

- [x] 1.1 Extend `_open_db()` in `princess/rooms.py` to `CREATE TABLE IF NOT EXISTS leaderboard …` plus the `idx_leaderboard_wins` index. Keep the existing `rooms` table behaviour unchanged.
- [x] 1.2 Add a `_normalize_name(display: str) -> str` helper (strip, collapse whitespace, lowercase). Place it next to `_fresh_scoreboard_entry`.
- [x] 1.3 Add `RoomRegistry._bump_global_leaderboard(finished_order, display_by_pid)` that runs the upsert in `asyncio.to_thread`. Use `INSERT … ON CONFLICT(name_key) DO UPDATE SET col = col + ?` for `princess_wins`, `last_places`, `rounds_played`, and always overwrite `display_name` + `updated_ts`. Wrap in try/except `sqlite3.Error`, log via `_persist_log`.
- [x] 1.4 Hook `Room._bump_scoreboard_if_needed()` to build the human-only `display_by_pid` map and call the registry helper after the in-memory bump. Preserve the `_scoreboard_counted_for_game` idempotency marker so re-broadcasts don't double-count globally either.

## 2. HTTP endpoint

- [x] 2.1 Add a `_LeaderboardCache` (5-second TTL keyed by `(limit, sort, min_rounds)`) to `princess/server.py`. Use `time.monotonic()`; do not depend on wall clock.
- [x] 2.2 Implement `GET /api/leaderboard` with `limit` (1–200, default 50), `sort` (`wins`|`winrate`|`rounds`, default `wins`), `min_rounds` (default 5). Return 400 on out-of-range parameters. Empty/missing table → empty list.
- [x] 2.3 Apply the existing slowapi limiter at 60/min/IP. Verify via the same `X-Forwarded-For` path used by `POST /api/rooms`.
- [x] 2.4 Wrap SQLite reads in try/except `sqlite3.Error`; on failure log + return an empty list with HTTP 200 (read failure should not break the page).

## 3. Static page

- [x] 3.1 Create `static/leaderboard.html`: `<title>Hall of Princesses · Princess</title>`, skip link, header, table skeleton, footer disclaimer ("Names are user-typed; this is a casual board, not a ranking system."). Inherit `styles.css`.
- [x] 3.2 Create `static/leaderboard.js`: fetch `/api/leaderboard`, render rows, wire sort-header buttons with `aria-pressed`, surface fetch errors with a polite retry message. No external libraries.
- [x] 3.3 Add minimal CSS to `static/styles.css` for the leaderboard table (or `static/leaderboard.css` if it grows). Stay inside the existing palette; verify ≥7:1 contrast.
- [x] 3.4 Add a `/leaderboard` route in `princess/server.py` serving `static/leaderboard.html`.

## 4. Link surfaces

- [x] 4.1 Add a "Hall of Princesses" anchor to the desktop footer in `static/index.html` (or wherever the footer markup lives) and to `static/app.js` if rendered there.
- [x] 4.2 Add a "Hall of Princesses" entry to the mobile menu sheet in `static/mobile.html` + `static/mobile.js`; ensure ≥44 px tap target. (Implementation note: placed in the mobile lobby switch-row alongside "View desktop site" — there is no general mobile menu sheet; existing dialogs are scoped to rules/quit/rename.)

## 5. Tests

- [x] 5.1 Create `tests/test_leaderboard.py`. Cover: table creation on boot, name normalization (case + whitespace), bump excludes bots, idempotency across rebroadcasts, SQLite error swallowed without raising, no-DB fast-path is a no-op.
- [x] 5.2 Add endpoint tests: default sort, `sort=winrate` respects `min_rounds`, `limit` clamping/400, cache hit, empty database returns empty list. (429 limiter coverage skipped — `PRINCESS_RATE_LIMIT_DISABLED=1` is set globally in conftest; rate-limit behaviour is exercised by the existing limiter tests for other endpoints.)
- [x] 5.3 Coverage included in `tests/test_leaderboard.py::test_room_bump_excludes_bots` — keeps the bot-exclusion check next to the rest of the leaderboard fixtures rather than splitting it into `test_persistence.py`.
- [x] 5.4 Added `section_hall_of_princesses` to `scripts/smoke_test.py` covering both the desktop footer link and the mobile lobby link (incl. 44 px tap-target assertion).

## 6. Docs & changelog

- [x] 6.1 README: add a "Hall of Princesses" subsection under Ops with the table shape, the env var (same `PRINCESS_DB_PATH`), and the clear-via-sqlite command.
- [x] 6.2 CHANGELOG.md: add a line under `[Unreleased]` → Added: "Hall of Princesses — persistent global leaderboard at `/leaderboard` plus `GET /api/leaderboard`."

## 7. Validation

- [x] 7.1 `openspec validate global-leaderboard --strict` passes.
- [x] 7.2 `black princess tests && pylint princess tests` clean (10.00/10).
- [x] 7.3 `pytest -q` passes including the new tests (220 passed, +25 over baseline).
- [x] 7.4 Local smoke (`scripts/smoke_test.py` against `http://127.0.0.1:8000`) passes the leaderboard sections (43/43 checks, +4 over baseline).
