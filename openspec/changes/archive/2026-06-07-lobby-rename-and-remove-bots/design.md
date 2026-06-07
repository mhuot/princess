## Context

The lobby's seat-management surface is asymmetric: the host can grow the room (add bots, accept joins) but can't shrink it without `/abort`. And players have no way to fix a typo'd name. Both gaps are cheap to close: seat data is just a list of `Seat` dataclasses in memory, and the lobby already re-renders on a broadcast.

## Goals / Non-Goals

**Goals:**
- Host can remove a bot seat from the lobby in one click.
- A seated player can rename themselves; the new name is reflected to everyone immediately.
- Stay within existing lobby-broadcast plumbing; no new state machinery.

**Non-Goals:**
- Hosts renaming other players. Each player owns their own name.
- Kicking humans. Existing `/leave` + the quit modal already cover human exit.
- Persistent identity across browser refreshes / server restarts. Out of scope.
- Mid-round bot removal. Once `room.game` exists the seats are part of the game state — removing one would orphan a player object. If the user wants this later it's a separate change.

## Decisions

### Two endpoints, not one unified `/seats/{pid}` PATCH/DELETE
**Choice:** Distinct `POST /remove_bot` and `POST /rename`. Both use POST + JSON body (no REST `DELETE` or `PATCH`).
**Why:** Matches every other endpoint in this project. The frontend posts JSON; nothing speaks REST.

### Host-only for `/remove_bot`; self-only for `/rename`
**Choice:** `/remove_bot` checks `host_pid == room.host_pid`. `/rename` checks the caller's `pid` matches the targeted seat.
**Why:** Bot removal affects the lobby for everyone, so it's a host-level decision. Renaming yourself is a personal preference and shouldn't require host blessing.

### `/rename` works during a round
**Choice:** No "lobby-only" gate on rename. Mid-round renames are allowed; the change broadcasts as a state update so opponents see the new name.
**Why:** Renames are display-only. The engine carries names on `Player`, but `Player.name` isn't used by any rule logic — only by `last_actions` text and `view_for` serialization. Touching `seat.name` AND `player.name` keeps the two in lockstep.
**Trade-off:** A player can mid-round change to a confusing name; UX risk only.

### Validation matches `/join`
**Choice:** `new_name` is required, 1–20 characters. Empty / over-length names get 400.
**Why:** Symmetry with the join endpoint, which uses the same Pydantic `Field(min_length=1, max_length=20)`.

### Rename in-game touches both `seat.name` AND `Player.name`
**Choice:** The rename handler updates `seat.name` always, AND if `room.game` exists it also updates the corresponding `Player.name` on the game object.
**Why:** Otherwise the opponent's row label (from `view.players[].name`) lags behind the lobby row label. Both fields are display-only; updating both is cheap.

### Lobby button placement
**Choice:** "Remove" button on the right side of each bot row (after the bot badge). "Rename" button on the right side of the user's own seat row (after the host/online badges).
**Why:** Per-row affordances are discoverable. The host's row gets both badges and the rename button — no remove button (the host can't remove themselves; that path is `/abort`).

### Rename UI: inline input, not a modal
**Choice:** Clicking "Rename" replaces the seat row's name text with an `<input type="text" maxlength="20">` pre-filled with the current name. Enter or blur submits; Escape cancels.
**Why:** Faster than opening a dialog for a single field. Matches the lobby's lightweight feel.

### Game-view rename
**Choice:** Add a small "Rename" button to the existing `#game-header` row (next to "Quit & return to lobby"). Same inline-input pattern, applied to a tiny "you're X" label or, simplest, a button that opens a `prompt()` — pragmatic for v1.
**Why:** Rare-use surface; a `confirm()`-style prompt is acceptable. Promote to inline UI if it gets used.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Host accidentally removes a bot they wanted | Single-click is fast; we can add a "Removed Bot Genius" toast if it gets reported. |
| Renaming mid-round shows up in the status stack as a name change | Acceptable; we don't add a "X is now Y" entry, but `last_actions` after rename will reference the new name. |
| Bot-name collision after rename — two players with the same name | Allowed; each pid is unique. The status stack uses player names which can repeat, but the rendering already trusts the engine's name strings. |
| Pylint complains about another short helper | Code already disables `missing-function-docstring` etc. — no new disables expected. |
| Browser caches old `app.js` and the host sees a button that 404s on click | Existing pattern: the user hard-refreshes after each merge. CONTRIBUTING already mentions this. |

## Migration Plan

1. Server: add `RemoveBotBody`, `RenameBody`, the two handlers, and the broadcast/logging hooks.
2. Tests: 5–6 new test_server cases (success, 403, 404, 409, validation).
3. Frontend: extend `renderLobby` per-row, wire `removeBot(pid)` and `renameSelf(newName)`.
4. Frontend: add a small "Rename" button to `#game-header`.
5. Docs: README "Lobby" sub-section, CHANGELOG `[Unreleased]`.
6. Commit + push + green CI + merge.

Rollback: revert the server handlers; the frontend buttons become no-ops since the endpoints return 404. (Belt and braces: revert the static files too.)

## Open Questions

- Should the game-header rename be `prompt()` for v1 or inline like the lobby? **Recommendation:** `prompt()` for v1 — easy to upgrade later.
- Should the lobby show a "Bot removed" toast or just rely on the lobby re-render to tell the story? **Recommendation:** silent re-render; the seat is just gone.
