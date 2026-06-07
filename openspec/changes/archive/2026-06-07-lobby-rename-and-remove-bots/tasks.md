## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/lobby-rename-and-remove-bots`.

## 2. Server endpoints

- [ ] 2.1 In `princess/server.py`, add `RemoveBotBody(BaseModel)` with `host_pid: str` and `bot_pid: str`.
- [ ] 2.2 Add `POST /api/rooms/{code}/remove_bot` handler: 404 if room missing, 403 if non-host, 409 if `room.game is not None`, 404 if `bot_pid` not in `room.seats`, 409 if the matching seat is not a bot. On success: pop the seat, log, broadcast lobby.
- [ ] 2.3 Add `RenameBody(BaseModel)` with `pid: str` and `new_name: str = Field(min_length=1, max_length=20)`.
- [ ] 2.4 Add `POST /api/rooms/{code}/rename` handler: 404 if room missing, 404 if `pid` not in `room.seats`. On success: update `seat.name`; if `room.game` exists, also update `room.game.player(pid).name`. Then broadcast lobby (no game) or state (game in progress). Log the rename.

## 3. Server tests (`tests/test_server.py`)

- [ ] 3.1 `test_remove_bot_success` — host posts; the bot seat is removed; only the host seat remains.
- [ ] 3.2 `test_remove_bot_rejects_non_host` → 403.
- [ ] 3.3 `test_remove_bot_rejects_after_start` → 409.
- [ ] 3.4 `test_remove_bot_rejects_human_seat` → 409.
- [ ] 3.5 `test_remove_bot_unknown_bot_pid` → 404.
- [ ] 3.6 `test_rename_in_lobby_updates_seat` — the human player's `seat.name` reflects the new name.
- [ ] 3.7 `test_rename_mid_game_updates_seat_and_player` — start a game, rename, assert both `seat.name` and `room.game.player(pid).name` match.
- [ ] 3.8 `test_rename_unknown_pid_returns_404`.
- [ ] 3.9 `test_rename_empty_name_returns_422` (Pydantic validation).
- [ ] 3.10 `test_rename_overlong_name_returns_422`.

## 4. Frontend JS

- [ ] 4.1 In `static/app.js` `renderLobby(room)`: when rendering each seat, append a small Remove button after the badge area for bot seats **iff** `state.isHost`. Wire `click` to call `removeBot(seat.pid)`.
- [ ] 4.2 In the same render: when the seat's `pid === state.pid`, append a small Rename button after the badges. Wire it to swap the name `<span>` for an inline `<input>` (or open the rename UI).
- [ ] 4.3 Add `removeBot(botPid)` async helper that POSTs `/api/rooms/<code>/remove_bot` with `{host_pid: state.pid, bot_pid: botPid}` and surfaces errors via `showError("lobby-error", ...)`.
- [ ] 4.4 Add `renameSelf(newName)` async helper that POSTs `/api/rooms/<code>/rename` with `{pid: state.pid, new_name: newName}` and surfaces errors via `showError("lobby-error", ...)`. Don't fire if `newName === currentName` (avoid noop POST).
- [ ] 4.5 Inline rename behavior: Enter or `blur` (with non-empty changed value) submits; Escape reverts; clicking outside reverts. Trim leading/trailing whitespace before submit; reject after trim if empty.
- [ ] 4.6 Game-view rename: in the `#game-header` row, add a small button "Rename" next to "Quit & return to lobby". `click` → `prompt("New name?", current)`; if the result is non-empty and trimmed and ≤ 20 chars, call `renameSelf(value)`.

## 5. Frontend HTML/CSS

- [ ] 5.1 In `static/index.html`, add a `<button type="button" id="rename-btn">Rename</button>` to `#game-header` (before or after the quit button).
- [ ] 5.2 In `static/styles.css`, add `.seat-action` (small, unobtrusive) styling for the per-row Remove and Rename buttons; reuse existing color tokens. Ensure focus-visible outline.

## 6. Docs

- [ ] 6.1 In `README.md`, the "Quick start" section (or a new short "Lobby" sub-section) gains a sentence: "Hosts can remove a bot, and any player can rename themselves at any time — see the per-row buttons in the lobby and the Rename button in the game header."
- [ ] 6.2 In `CHANGELOG.md` `## [Unreleased]`, append under `### Added`:
  - "Host can remove a bot seat from the lobby via per-row Remove button (`POST /api/rooms/{code}/remove_bot`)."
  - "Players can rename themselves from the lobby (inline input) or mid-round (Rename button in the game header) via `POST /api/rooms/{code}/rename`."

## 7. Verify locally

- [ ] 7.1 `black princess tests`
- [ ] 7.2 `pylint princess tests` — expect 10.00/10.
- [ ] 7.3 `pytest -q` — expect green.
- [ ] 7.4 `openspec validate --specs --strict` and `openspec validate lobby-rename-and-remove-bots --strict`.
- [ ] 7.5 Manual smoke: create a room, add two bots. As host, click Remove on one bot → it vanishes. Click Rename on your own row → inline input appears, type a new name, Enter → all clients see the new name. Start a round, click Rename in game header → prompt → all opponents see the new name.

## 8. Ship

- [ ] 8.1 Commit per spec policy (`lobby-rename-and-remove-bots: <task title>`), or one logical commit if the work is tightly intertwined (matches the project's pattern from prior changes).
- [ ] 8.2 Push the branch; open a PR with the template.
- [ ] 8.3 Watch CI; fix any red.
- [ ] 8.4 Squash-merge into main once green.

## 9. Wrap up

- [ ] 9.1 Run `openspec status --change lobby-rename-and-remove-bots` and confirm 4/4 artifacts done.
- [ ] 9.2 `/opsx:archive lobby-rename-and-remove-bots` after merge.
