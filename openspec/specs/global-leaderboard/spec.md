# global-leaderboard Specification

## Purpose
TBD - created by archiving change global-leaderboard. Update Purpose after archive.
## Requirements
### Requirement: Persistent leaderboard table

The server SHALL maintain a `leaderboard` table in the existing SQLite database identified by `PRINCESS_DB_PATH`. The schema SHALL be:

```
leaderboard(
    name_key       TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL,
    princess_wins  INTEGER NOT NULL DEFAULT 0,
    last_places    INTEGER NOT NULL DEFAULT 0,
    rounds_played  INTEGER NOT NULL DEFAULT 0,
    updated_ts     REAL NOT NULL
)
```

The table SHALL be created idempotently on every server startup (`CREATE TABLE IF NOT EXISTS`). An index on `princess_wins DESC` SHALL also be created idempotently. Persistence SHALL be disabled when `PRINCESS_DB_PATH` is unset — in that case the endpoint serves an empty list and bumps are no-ops.

#### Scenario: Table created on first boot

- **WHEN** the server starts with a `PRINCESS_DB_PATH` pointing to a fresh file
- **THEN** the `leaderboard` table exists in the database with the schema above

#### Scenario: Table preserved across restarts

- **WHEN** the server is restarted and a `leaderboard` row already exists
- **THEN** the row is preserved with its counters intact

#### Scenario: No-op without DB path

- **WHEN** `PRINCESS_DB_PATH` is unset and a game ends
- **THEN** no SQLite write is attempted and the server logs no error

### Requirement: Name normalization

The server SHALL derive `name_key` from a player's display name by stripping leading and trailing whitespace, collapsing internal whitespace runs to a single space, and lowercasing the result. `display_name` SHALL store the most recently observed casing.

#### Scenario: Casing variants merge

- **WHEN** "Alice" wins one game and "ALICE" wins another
- **THEN** the table holds one row with `princess_wins = 2` and `display_name = "ALICE"`

#### Scenario: Whitespace normalized

- **WHEN** "  bob  " and "bob" each finish a game
- **THEN** both contribute to the same `name_key = "bob"` row

### Requirement: Bump on game-over

The server SHALL upsert leaderboard counters exactly once per finished game per human seat in `finished_order`. The first pid SHALL receive `princess_wins += 1`, the last pid SHALL receive `last_places += 1`, and every human pid in `finished_order` SHALL receive `rounds_played += 1`. Bumps SHALL be idempotent: re-broadcasting the same game-over state SHALL NOT double-count.

#### Scenario: Wins and last-place credited once

- **WHEN** a four-player game ends with finished_order `[a, b, c, d]` (all human)
- **THEN** `a.princess_wins += 1`, `d.last_places += 1`, and all four `rounds_played += 1`

#### Scenario: Bot seats excluded

- **WHEN** a three-player game ends with `[human1, bot, human2]`
- **THEN** only `human1` and `human2` rows are upserted; no leaderboard row is created for the bot

#### Scenario: Idempotent across rebroadcasts

- **WHEN** the same finished game triggers two broadcasts
- **THEN** counters are bumped exactly once

### Requirement: Write failure isolation

When a SQLite write fails (disk error, schema mismatch), the server SHALL log the exception and continue serving the WS broadcast. The in-memory per-room scoreboard SHALL remain accurate even when the global write fails.

#### Scenario: SQLite error does not break broadcast

- **WHEN** the global leaderboard upsert raises `sqlite3.Error`
- **THEN** the WS state broadcast still completes and the room remains playable

### Requirement: Leaderboard read endpoint

The server SHALL expose `GET /api/leaderboard` returning JSON `{"entries": [...], "generated_ts": <float>}`. Each entry SHALL include `display_name`, `princess_wins`, `last_places`, `rounds_played`, and `win_rate` (princess_wins divided by max(rounds_played, 1), rounded to four decimal places).

The endpoint SHALL accept query parameters:

- `limit` (1–200, default 50) — maximum rows returned.
- `sort` (`wins` | `winrate` | `rounds`, default `wins`) — sort key, descending.
- `min_rounds` (default 5, ignored when sort != `winrate`) — minimum `rounds_played` filter when sorting by win rate.

Results SHALL be cached in-process for 5 seconds keyed by `(limit, sort, min_rounds)`. The endpoint SHALL be rate-limited to 60 requests per minute per IP via the existing slowapi limiter.

#### Scenario: Default response

- **WHEN** `GET /api/leaderboard` is called with no parameters
- **THEN** the response contains up to 50 rows sorted by `princess_wins` descending

#### Scenario: Win-rate floor filters small samples

- **WHEN** `sort=winrate` and a player has `rounds_played=2`
- **THEN** the player is excluded from the response (default `min_rounds=5`)

#### Scenario: Limit clamped

- **WHEN** `limit=500` is requested
- **THEN** the server responds with HTTP 400 (or clamps to 200; pick one and document)

#### Scenario: Empty database

- **WHEN** the leaderboard table is empty
- **THEN** the response is `{"entries": [], "generated_ts": <float>}`

#### Scenario: Cache hit

- **WHEN** two identical requests arrive within 5 seconds
- **THEN** the second request returns from cache without querying SQLite

#### Scenario: Rate limit

- **WHEN** an IP exceeds 60 requests in a minute
- **THEN** the server responds with HTTP 429

### Requirement: Hall of Princesses page

The server SHALL serve a static HTML page at `/leaderboard` titled "Hall of Princesses". The page SHALL fetch `/api/leaderboard` on load, render a table with columns Rank, Player, Princess Wins, Last Places, Rounds, Win Rate, and offer column-header buttons that re-fetch with the matching `sort` value. The page SHALL meet WCAG AAA contrast (≥7:1), include a skip link, expose ARIA labels on sort buttons, and respect `prefers-reduced-motion`.

#### Scenario: Page renders top 50

- **WHEN** a user navigates to `/leaderboard` with at least 50 humans in the table
- **THEN** 50 rows are displayed sorted by Princess Wins descending

#### Scenario: Sort by win rate

- **WHEN** the user activates the Win Rate header
- **THEN** the page re-fetches with `sort=winrate` and renders the new order

#### Scenario: Empty state

- **WHEN** the table is empty
- **THEN** the page displays a friendly empty-state message and a link back to `/`

#### Scenario: WCAG AAA contrast

- **WHEN** the page is rendered with the production palette
- **THEN** every text element passes a ≥7:1 contrast check against its background

