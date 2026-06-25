# 👑 Princess Card Game

> _A climbing-card game with a 5-under house rule (tunable per room)._
> _Built in an afternoon. Plays for hours._

```
   ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐
   │A♠   │  │K♥   │  │7♦   │  │2♣   │
   │  ♛  │  │  ♛  │  │  ♛  │  │  ♛  │
   │   A │  │   K │  │   7 │  │   2 │
   └─────┘  └─────┘  └─────┘  └─────┘
            climb · burn · reset · reverse
```

[![Tests](https://github.com/mhuot/princess/actions/workflows/tests.yml/badge.svg)](https://github.com/mhuot/princess/actions/workflows/tests.yml)
[![Lint](https://github.com/mhuot/princess/actions/workflows/lint.yml/badge.svg)](https://github.com/mhuot/princess/actions/workflows/lint.yml)
[![OpenSpec](https://github.com/mhuot/princess/actions/workflows/openspec.yml/badge.svg)](https://github.com/mhuot/princess/actions/workflows/openspec.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)

## Quick start

```bash
git clone https://github.com/mhuot/princess.git
cd princess && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m princess
```

Open <http://127.0.0.1:8000>, enter a name, click **Create new room**, click **Add bot** (they have *opinions* about your skill), and click **Start game**. That's it.

**On a phone?** Phones are auto-redirected from `/` to `/m` (the touch-friendly UI — wrapped hand, sticky action bar, bottom-sheet menus). Share `/m/<code>` with friends to drop them straight into the join screen. To force the desktop UI on a phone, append `?desktop=1` or use the **View desktop site** link in the mobile lobby; the reverse-direction **Mobile site** link sits in the desktop footer.

In the lobby: the host can **Remove** any bot seat (per-row button), and any player can **Rename** themselves via the inline input on their own row — or via the Rename button in the game header during a live round.

> Need a screenshot? Add one to `docs/screenshot.png` — see [Contributing](CONTRIBUTING.md#screenshots).

## The reverse-rank house rule (default: 5-under)

This is the one rule that makes Princess Princess.

> **The reverse rank is a wild card. Playing it forces the next play to be UNDER it.**

The default reverse rank is **5**, so `5 → 4`, `5 → 3`, `5 → 2` are all legal. `5 → 8` is not. There are **three wild ranks** — each one is always legal regardless of the pile top:

- **2** — wild reset. Resets the pile so anything goes.
- **10** — burn. Clears the pile; you play again.
- **The reverse rank itself** (default 5) — always legal AND forces the next play to be UNDER it. So a 5 can land on a King; the next player then needs an under-5, a 2, a 10, or another 5.

The reverse rank is tunable per room from the lobby's **House rules** panel: pick any rank from 3 through A (excluding the other wilds, 2 and 10). Want a 7-under variant? Set it to 7. Want a high-stakes A-under? Set it to A.

## Features

- **2–4 player rooms over the internet.** Share a 4-character room code, your friends join from their browser. WebSocket-driven, FastAPI backend, vanilla JS frontend — no build step.
- **Play solo against AI.** A heuristic bot picks lowest legal, hoards 2s and 10s, completes four-of-a-kind burns when it can.
- **100 random bot names that roast you.** *Skill Issue*, *Cope Dispenser*, *Mid Bot Maxine*, *Mensa Queen*, *Diff Lord*, …
- **Quit modal with options.** Take over with a bot (round continues without you), end the round (winner banner with current standings), or abort to lobby.
- **Pre-game swap phase.** Dealt 3 face-down + 6 to choose from; pick 3 to go face-up, 3 stay in hand. Bots auto-pick their highest.
- **WCAG AAA color palette.** ≥7:1 contrast, skip link, keyboard-visible focus rings, `prefers-reduced-motion` respect.
- **In-browser log viewer at `/logs`.** Live-tail with auto-refresh, download as text, clear button. No filesystem footprint — bounded 2000-entry ring buffer. The log API (`/api/logs*`) is restricted to loopback clients only; session tokens are redacted before they ever reach the buffer.
- **Tested.** 105 unit + integration tests covering the engine, AI, server, log buffer, room lifecycle, and the WebSocket round-trip.
- **Spec-driven.** Every behavior is documented in [`openspec/specs/`](openspec/specs/) — game-engine, ai-bot, room-server, web-frontend, logging, repository-meta.

## Project layout

```
princess/
├── princess/            # Python server + engine
│   ├── game.py          #   pure-Python rules engine
│   ├── ai.py            #   heuristic bot
│   ├── rooms.py         #   in-memory room registry, bot loop
│   ├── server.py        #   FastAPI HTTP + WebSockets
│   ├── bot_names.py     #   100-name roster
│   └── logging_config.py#   in-memory FIFO + handler
├── static/              # Vanilla JS / CSS / HTML
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── logs.html
├── tests/               # 105 pytest tests
├── openspec/            # Spec set + change history
│   ├── specs/           #   6 capability specs
│   └── changes/archive/ #   completed proposals
├── CONTRIBUTING.md      # dev setup, OpenSpec workflow, PR checklist
├── CHANGELOG.md         # Keep a Changelog format
├── LICENSE              # Apache 2.0
└── NOTICE               # attribution
```

## Ops

### Health check and logs

The server exposes an unauthenticated liveness probe and optional rotating
file logging, both intended for production deployments behind nginx.

**`GET /healthz`** returns `200 OK` with a small JSON payload:

```json
{
  "status": "ok",
  "uptime_seconds": 312,
  "rooms": 4,
  "log_buffer_size": 187
}
```

`uptime_seconds` is measured from process start (monotonic clock). `rooms`
is the current in-memory room count. `log_buffer_size` is the live count of
entries in the in-memory ring buffer (capacity is fixed at 2000). The
endpoint does no per-room work and does no I/O — it is safe to probe at
high frequency from nginx, an external uptime monitor (Uptime Robot,
Better Uptime, etc.), or any orchestrator.

**File logging** is opt-in via env var. Defaults preserve the existing
"no files on disk" behaviour in development.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRINCESS_LOG_PATH` | _(unset)_ | Path to the rotating log file. Unset/empty → no file handler attached. |
| `PRINCESS_LOG_MAX_BYTES` | `10485760` (10 MB) | Bytes per file before rotation. |
| `PRINCESS_LOG_BACKUP_COUNT` | `5` | Number of rotated backups kept. |

The file handler writes one JSON object per line (JSONL) with fields
`ts`, `level`, `logger`, `message`, `room`, and an optional `exc_info`
when `logger.exception(...)` is used. `room` is parsed from logger names
of the form `princess.room.<code>`, enabling per-room grep:

```
jq 'select(.room=="AB12")' /var/log/princess.log
```

Stdout and the in-browser `/logs` viewer keep the existing human-readable
single-line format. The file is purely a deploy-spanning backup so a
container restart does not take the history with it. If the configured
path cannot be opened, the server logs a single warning to stdout and
continues without the file handler — startup never fails on a misconfigured
log path.

**nginx upstream health check** (OSS nginx — passive via
`proxy_next_upstream`; active health checks require nginx-plus):

```nginx
upstream princess_app {
    server 127.0.0.1:8000 max_fails=2 fail_timeout=10s;
}

location / {
    proxy_pass http://princess_app;
    proxy_next_upstream error timeout http_502 http_503 http_504;
}

location = /healthz {
    proxy_pass http://princess_app/healthz;
    access_log off;
}
```

**docker-compose** snippet mounting the host log directory:

```yaml
services:
  princess:
    image: princess:latest
    environment:
      PRINCESS_LOG_PATH: /var/log/princess/princess.log
      PRINCESS_LOG_MAX_BYTES: "10485760"
      PRINCESS_LOG_BACKUP_COUNT: "5"
    volumes:
      - /var/log/princess:/var/log/princess
```

### Hall of Princesses (global leaderboard)

A persistent leaderboard at `/leaderboard` aggregates Princess wins,
last-place finishes, and rounds played across **every room and every server
restart**. It lives in the same SQLite database as `persistent-rooms`
(`PRINCESS_DB_PATH`, default `./princess.db`) and creates its `leaderboard`
table idempotently at startup.

Rows are keyed by a normalized name (lowercase, whitespace-collapsed) so
"Alice", "ALICE", and "  alice  " aggregate into one entry. **Bots are
excluded** — only seats with `is_bot = False` contribute to counters.

**`GET /api/leaderboard`** accepts three optional query parameters:

| Parameter | Default | Range / values | Notes |
| --- | --- | --- | --- |
| `limit` | `50` | `1`–`200` | Max rows returned. |
| `sort` | `wins` | `wins` \| `winrate` \| `rounds` | Sort key, descending. |
| `min_rounds` | `5` | `>=0` | Win-rate floor; ignored unless `sort=winrate`. |

Responses are cached in-process for 5 seconds per `(limit, sort, min_rounds)`
tuple and rate-limited to 60 requests per minute per IP.

The page itself is a static HTML view linked from the desktop footer and the
mobile lobby switch row. There is no admin UI for clearing — operators reset
counters with `sqlite3 princess.db "DELETE FROM leaderboard"`. The schema:

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

### Persistent rooms

Rooms (seats, host, config, in-progress games, and the session scoreboard)
persist to an embedded SQLite store so a restart — including the deploy
loop that ships every push to `main` — does not wipe live lobbies or
mid-round state. Clients reconnect via the existing pid-in-`localStorage`
sentinel; the WS handler finds the restored seat by code and resumes.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PRINCESS_DB_PATH` | `./princess.db` | SQLite file path. Read once at startup. |

In a systemd / docker deployment, point this at a writable persistent
path, e.g. `/var/lib/princess/rooms.db`. The schema is a single table
(`rooms(code TEXT PRIMARY KEY, payload TEXT, updated_ts REAL)`) with the
full room serialized as a JSON blob; write-through on every mutating
handler keeps it in sync. Corrupt rows are logged and skipped on
startup so a single bad row never blocks the server from coming back up.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). The short version:

1. Fork & clone.
2. `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
3. `black princess tests && pylint princess tests && pytest -q`.
4. For any non-trivial change, open an OpenSpec proposal first — see the [`openspec/`](openspec/) directory and the workflow in CONTRIBUTING.

## House naming policy

This project is called **Princess**. In all code, UI copy, commit messages, and public-facing surfaces (including GitHub topics and descriptions), the inspiring game's vulgar name is **never used**. Private design notes can mention the family of games (Shithead/Karma) for context; everything else stays Princess. Reviewers enforce.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). Copyright © 2026 Mike Huot.

A `NOTICE` file accompanies redistributions per Section 4(d) of the license.
