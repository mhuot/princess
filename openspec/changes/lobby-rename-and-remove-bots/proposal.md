## Why

Two small ergonomic gaps in the lobby:

1. **Host can add bots but can't remove them.** If you click "Add bot" three times by mistake or your friends bail and you decide to go 1v1 instead, you're stuck — the only way out is `/abort` and starting a fresh room.
2. **Players can't rename themselves.** You typo your name on join, or you joined as "test" and now want to be called "Mike" — there's no fix without leaving the room and rejoining (which spawns a new pid and confuses the lobby state).

Both are pure-lobby operations on seat metadata. No engine changes; no impact mid-round.

## What Changes

- **Server:**
  - `POST /api/rooms/{code}/remove_bot` with `{host_pid, bot_pid}` — host-only, lobby-only (room.game must be `None`), removes a bot seat from `room.seats`. Rejects 403 for non-hosts, 409 if the room has a game in progress, 409 if `bot_pid` is not actually a bot seat, and 404 for missing rooms.
  - `POST /api/rooms/{code}/rename` with `{pid, new_name}` — any seated player can rename themselves. The name has the same constraint as join (1–20 chars). Host can rename themselves too. Works during lobby AND during a round (broadcasts the change). The `pid` must match a seat in the room; otherwise 404.
- **Frontend:**
  - Lobby seat list: each **bot** row gets a small "Remove" button visible to the host only. Clicking it POSTs `/remove_bot` and the lobby re-renders.
  - Lobby seat list: each row for the **current user** gets a small "Rename" button next to their badge. Clicking it opens an inline `<input>` (or a small modal) with the current name pre-filled; on submit, POST `/rename` and re-render.
  - Optional: a "Rename" affordance on the game-view header so a player can rename mid-round without going back to the lobby.

## Capabilities

### Modified Capabilities

- `room-server`: add the two endpoints + their authorization / validation rules.
- `web-frontend`: lobby seat list gains per-row controls; rename UI is reachable from the lobby (and from the game header, if implemented).

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/server.py` — two new POST handlers + Pydantic bodies.
  - `princess/rooms.py` — broadcast helpers already exist; no new methods needed.
  - `static/app.js` — `renderLobby` adds per-row buttons; new handlers `removeBot(pid)` and `renameSelf(newName)`; game-view header gets an optional "Rename" button.
  - `static/index.html` — game-view header gets a "Rename" link (small button) for the rename-mid-round path.
  - `static/styles.css` — minor styling for the new buttons (matches existing badge/button look).
  - `tests/test_server.py` — coverage for both endpoints (success + 403 + 409 + 404 paths).
- **Affected APIs:** two new endpoints. Existing endpoints unchanged.
- **Affected dependencies:** none.
- **Docs touched:** README (small "Lobby" sub-section gains a sentence about rename + remove bot), CHANGELOG `[Unreleased]`.
- **Depends on:** none beyond the current main; this change has no engine or spec overlaps with anything in flight.
- **Out of scope:** host renaming another player's seat (each player owns their own name); promoting a non-host to host; kicking a human (use `/leave` or quit modal for now); persistent player names across sessions.
