# Changelog

All notable changes to Princess Card Game will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(nothing yet)

## [0.1.0] — 2026-06-07

Initial release. Everything below was shipped via OpenSpec changes archived under [`openspec/changes/archive/`](openspec/changes/archive/).

### Added

**Game engine** (`princess/game.py`)

- 2–4 player climbing card game on a standard 52-card deck.
- Each player dealt 3 face-down + 3 face-up + 3 hand (or 3 face-down + 6 "choose" + 0 hand when the swap phase is enabled).
- Play source priority hand → face-up → face-down.
- Rank-based legality: played rank ≥ pile top unless a special applies.
- **2** is wild reset (always legal; next play unrestricted).
- **10** burns the pile and the same player plays again.
- **7** forces the next play to be UNDER 7 — the project's defining house rule.
  - **7-on-7 toggle** (`GameConfig.seven_on_seven`) defaults to true.
- **Four of a kind** in a row on the pile burns it.
- Hand auto-refills from the deck after every play.
- Voluntary pickup of the whole pile; turn always passes to the next non-finished player.
- Face-down "blind" plays: revealed → tested; illegal flips force pickup of pile + revealed card.
- Game over when only one player still holds cards; `finished_order` tracks Princess (winner) through last place.
- New `Game.end_round()` — host-driven early termination ranking remaining players by ascending hand size.
- Per-room configuration via `GameConfig`; unknown keys silently ignored for forward compatibility.

**AI bot** (`princess/ai.py`)

- Heuristic decider: plays the lowest legal non-special card, hoards 2s and 10s.
- Completes four-of-a-kind burns when pile + hand allow.
- Blind random pick on face-down plays.
- Swap-phase auto-pick: chooses the top 3 highest-rank cards from the choose pile.

**Server** (`princess/server.py` + `princess/rooms.py`)

- FastAPI + WebSockets, in-memory `RoomRegistry`, 4-char alphanumeric room codes.
- REST endpoints: create / join / bot / config / start / rematch / abort / leave / end_round.
- WebSocket `/ws/{code}/{pid}` carries `play`, `pickup`, and `set_face_up` actions.
- Bot turn loop with safety cap (30 actions when a connected human is waiting; 1000 when only bots remain).
- Force-pickup fallback on any rejected bot action; exception fallback for bot crashes.
- 100-name SFW bot-name roster with no in-room duplicates.
- Per-room rule config (`seven_on_seven`).
- Host-only end-of-round, abort, rematch, and `convert_to_bot` flag on `/leave`.
- Orphan room cleanup: rooms with no connected sockets for `ROOM_IDLE_TIMEOUT_SECONDS` (default 300) are evicted on the next request tick.

**Frontend** (`static/`)

- Vanilla HTML + CSS + JS single-page app, served from `/`.
- Lobby with create / join / host-rules panel / add-bot / start.
- Setup-phase UI: 6 choose cards, pick 3, "Lock in" button.
- Game view: opponents row, pile area with rule indicator, your-table (face-up + face-down in one mini-row), hand, action buttons.
- Sort-hand toggle (rank then suit, client-side; server indices preserved).
- "Quit & return to lobby" opens a contextual modal — non-host: take over with bot / leave; host: end round / abort.
- "(bot)" / "(now a bot)" tag on opponents during play and in the lobby.
- End-of-round panel: winner name in big gold type, finishing order, rematch button (host).
- Hover tooltip on every card naming the rank and the rule (for 2, 7, 10).
- Collapsible "Special cards & house rules" legend; dynamically reflects the active config.
- WCAG AAA color palette, skip link, ARIA labels and roles, keyboard focus rings, `prefers-reduced-motion`.

**Logs** (`princess/logging_config.py`)

- In-memory FIFO ring buffer (2000 entries, drops oldest). No filesystem writes.
- Stdout mirror at configured `LOG_LEVEL` (default INFO).
- Per-room logger namespaces (`princess.room.<code>`) — grep-friendly.
- REST: `GET /api/logs?since=&limit=`, `GET /api/logs/download` (text attachment), `DELETE /api/logs`.
- In-browser `/logs` viewer with live 2s tail, autoscroll, download, clear.
- Instrumented points: room lifecycle, WebSocket connect/disconnect/crash, every play and pickup (success + rejection), bot decisions with pile-top and hand, bot loop safety cap.

**Repository meta** (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `NOTICE`, `.github/`, `openspec/config.yaml`)

- Apache 2.0 license + per-file headers.
- GitHub Actions workflows: `tests.yml`, `lint.yml`, `openspec.yml`.
- PR + issue templates.
- OpenSpec config populated with project context (Python 3.14, 7-under, Princess-only naming) and atomic-commit + docs-sync rules.

### Tests

- 105 pytest tests covering engine, AI, server endpoints, room/registry, logging buffer, and the WebSocket round-trip.

[Unreleased]: https://github.com/mhuot/princess/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mhuot/princess/releases/tag/v0.1.0
