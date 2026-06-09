## Why

After a rematch the previous round's outcome vanishes. A player who has won three Princess crowns in a session can't tell that from a player who just joined — both render identically in the winner panel and the opponent strip. The only signal is the current round's `finished_order`, which gets overwritten the moment the host clicks **Play a rematch**. That removes the satisfying through-line of a long session ("I'm up 4–2 on Bob") and removes any reason to keep playing once a single round ends.

A session-level scoreboard fixes this with one new piece of room state: counters per seat that survive every rematch but reset on `/abort` and on room eviction. The engine already emits `finished_order` per round; the room layer needs to bump counters when a round closes and surface those counts in lobby / state broadcasts. Both UIs already render the winner panel and the opponent strip — they only need to read two more fields.

## What Changes

- **Room owns a session scoreboard.** New `Room.scoreboard: dict[str, dict[str, int]]` keyed by `seat.pid`. Each value is `{"princess_wins": int, "last_places": int, "rounds_played": int}`. Initialized to zeros when a seat is created (room create, join, add-bot, or convert-to-bot). Persists across rematches.
- **Bumped on game-over, exactly once per round.** When `room.game.game_over` flips to `True` and the room broadcasts the final state, the room SHALL increment counters from `room.game.finished_order` — `princess_wins += 1` for `finished_order[0]`, `last_places += 1` for `finished_order[-1]`, `rounds_played += 1` for every pid in `finished_order`. The bump is idempotent per round (a re-broadcast of the same finished game does NOT double-count).
- **Reset only on abort and eviction.** `/abort` zeroes the scoreboard for every seat. The idle-room sweep that evicts a room obviously drops scoreboard with the rest of the room state. `/rematch` does NOT reset.
- **Removed seats lose their entry.** When a seat is removed via `/remove_bot` or `/leave` (without `convert_to_bot`), its scoreboard entry is dropped. A new seat at the same name later starts at zero.
- **Lobby broadcast surfaces scoreboard.** `Room.public_lobby()` includes `scoreboard: {pid: {...}}` keyed by pid so clients can render counts on lobby seats too (between rounds, while seeing the rematch button).
- **State broadcast surfaces scoreboard.** `Game.view_for(pid)` keeps its existing shape; the room layer attaches a `scoreboard: {pid: {...}}` field at the **top level** of the per-seat state payload (alongside `view`) — clients read it the same way in both screens.
- **Desktop winner panel adds a "Session record" line.** Under the finishing-order list, a small line summarizing the calling user's row reads, e.g., `Session record: Princess 3 · Last place 1 · 4 rounds`. If `rounds_played == 0` after the bump (impossible in normal play) the line is hidden gracefully.
- **Mobile winner panel adds the same line** at a smaller font size to fit the narrow column.
- **Desktop opponent boxes and mobile opponent chips** append a small inline `· Princess N` (and a faint `· Last N` if `last_places > 0`) after each player's name, when `N > 0`. The badge uses the existing accent color used for the wild `★` glyph. The user's own row gets the same treatment so they see their own count too.
- **Spec updates** in `room-server` (new requirement: session scoreboard model + broadcast), `web-frontend` (winner-panel line + opponent name badge), and `mobile-frontend` (winner-panel line + opponent chip badge).

## Capabilities

### Modified Capabilities

- `room-server`: owns the per-room scoreboard model, bumps it on game-over, resets it on abort, and serializes it in both `lobby` and `state` broadcasts.
- `web-frontend`: winner panel renders a "Session record" line for the calling user; opponent boxes (and the user's own name) display `· Princess N` and optional `· Last N` badges.
- `mobile-frontend`: same as web-frontend, smaller font, the badge slots into the opponent chip's name line.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/rooms.py` — new `Room.scoreboard` dict; new `_bump_scoreboard()` helper invoked from the game-over path; reset on `/abort`; entry add/drop on seat add/remove; include in `public_lobby()` and on the state envelope.
  - `princess/server.py` — `broadcast_state` (or its caller chain) attaches `scoreboard` next to `view`; `/abort` clears the dict; `/remove_bot` and `/leave` drop the removed pid's entry.
  - `static/app.js`, `static/styles.css` — winner-panel "Session record" line; opponent name badge.
  - `static/mobile.js`, `static/mobile.css` — same, mobile-sized.
- **Affected APIs:** the `lobby` and `state` WebSocket payloads gain a top-level `scoreboard` dict. Adding a field is forward-compatible; clients that don't read it ignore it.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Added` bullet.
- **Out of scope:**
  - Cross-room or cross-session persistence (no database; in-memory only — matches existing room-server policy).
  - Most-cards-burned / longest-streak / fanciest stats. Princess wins and last places are the two ranks that matter.
  - Server-pushed leaderboard for spectators outside the room.
  - Animations on count bump.
