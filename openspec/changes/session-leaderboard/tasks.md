## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/session-leaderboard`.

## 2. Room model

- [ ] 2.1 In `princess/rooms.py`, add a new field on `Room`: `scoreboard: dict[str, dict[str, int]] = field(default_factory=dict)`. Add a private `_scoreboard_counted_for_game: int | None = field(default=None)` (or equivalent boolean flag) to track idempotency of the bump.

- [ ] 2.2 Add `Room._ensure_scoreboard_entry(pid: str) -> None` that, if `pid not in self.scoreboard`, sets `self.scoreboard[pid] = {"princess_wins": 0, "last_places": 0, "rounds_played": 0}`.

- [ ] 2.3 Add `Room._drop_scoreboard_entry(pid: str) -> None` that pops `pid` from `self.scoreboard` (no-op if absent).

- [ ] 2.4 Wire `_ensure_scoreboard_entry` into every seat-add path:
  - `RoomRegistry.create_room` after appending the host seat.
  - `Room.add_seat` (or wherever join happens) for `/join`.
  - The bot-add path inside `rooms.py` for `/bot`.
  - The convert-to-bot path is a no-op (the pid is unchanged and the entry already exists; do not re-init).

- [ ] 2.5 Wire `_drop_scoreboard_entry` into:
  - The `/remove_bot` seat removal.
  - The `/leave` (non-convert) seat removal.

## 3. Scoreboard bump

- [ ] 3.1 Add `Room._bump_scoreboard_if_needed() -> None`. It SHALL:
  - return early if `self.game is None` or `self.game.game_over is False`.
  - return early if the current game's identity (e.g., `id(self.game)`) has already been recorded as counted in `_scoreboard_counted_for_game`.
  - read `finished_order = list(self.game.finished_order)`.
  - if non-empty: increment `scoreboard[finished_order[0]]["princess_wins"] += 1`, `scoreboard[finished_order[-1]]["last_places"] += 1`, and `scoreboard[pid]["rounds_played"] += 1` for each pid in `finished_order` (defensive guard: skip pids not in `self.scoreboard`).
  - set `_scoreboard_counted_for_game = id(self.game)`.

- [ ] 3.2 Clear the counted flag in `start_game()` (and therefore also in the rematch path that calls `start_game`).

- [ ] 3.3 Call `_bump_scoreboard_if_needed()` at the top of `broadcast_state` so the lobby snapshot it produces — and the state envelope each seat receives — already reflects the bumped counters.

## 4. Broadcast surfaces

- [ ] 4.1 In `Room.public_lobby()`, add `"scoreboard": dict(self.scoreboard)` at the top level alongside `seats` and `config`.

- [ ] 4.2 In `broadcast_state`, change the per-seat send so the envelope also carries `scoreboard`:

  ```python
  msg = {"type": "state", "view": view, "scoreboard": dict(self.scoreboard)}
  await self._send(seat.socket, msg)
  ```

- [ ] 4.3 Confirm `broadcast_lobby` (when called after `/abort`, `/rematch`, etc.) already calls `public_lobby()` and thus auto-picks up the new field. No other change needed.

## 5. Reset on abort

- [ ] 5.1 In `princess/server.py` `/abort` handler, after setting `room.game = None`, zero every existing entry: `for k in room.scoreboard: room.scoreboard[k] = {"princess_wins": 0, "last_places": 0, "rounds_played": 0}`. Do NOT drop the entries — the seats persist.

- [ ] 5.2 No change needed to `/rematch` — it deliberately preserves the scoreboard.

## 6. Desktop UI

- [ ] 6.1 In `static/app.js`, in the message handler for `state` (and `lobby`), stash the broadcast `scoreboard` field on `state.scoreboard` (or equivalent client-state key).

- [ ] 6.2 In `renderOpponents` (the opponents row builder for the play view), for each opponent (and for the user's own row if it's rendered in the same surface), look up `state.scoreboard[opp_pid]`. If `princess_wins > 0` append a span `<span class="score-badge">· Princess <N></span>` to the name line; if `last_places > 0` append `<span class="score-badge">· Last <N></span>`.

- [ ] 6.3 In `renderGameOver` (the winner-panel builder), after the finishing-order list and before the rematch button, render a `<p class="session-record">Session record: Princess <P> · Last place <L> · <R> rounds</p>` line using the current user's scoreboard entry. Hide the line entirely when `R == 0`. Elide the `· Last place 0` clause when `L == 0` (style choice — match the proposal's example).

- [ ] 6.4 In `static/styles.css`, add `.score-badge { color: var(--accent); font-size: 0.85em; margin-left: 0.25em; }` (or equivalent that matches the wild-accent palette). Add `.session-record { color: var(--accent); font-size: 0.95em; margin-top: 0.5em; }`. Style is intentionally restrained — no animations, no background.

## 7. Mobile UI

- [ ] 7.1 In `static/mobile.js`, mirror the message-handler change so the broadcast `scoreboard` is available alongside the view.

- [ ] 7.2 In `renderOpponents(view, scoreboard)` (mobile opponents strip), append `<span class="m-score-badge">· Princess <N></span>` (and optionally `· Last <N>`) inline after the existing name + (bot) tag, when the counters are > 0. The user's own name elsewhere in the play view gets the same treatment.

- [ ] 7.3 In the mobile winner-panel builder, render the same `Session record: …` line, sized down via `.m-session-record { font-size: 0.85rem; }`.

- [ ] 7.4 In `static/mobile.css`, add `.m-score-badge { color: var(--accent); font-size: 0.7rem; margin-left: 0.2em; }` and `.m-session-record { color: var(--accent); font-size: 0.85rem; margin-top: 0.5em; }`.

## 8. Docs

- [ ] 8.1 In `CHANGELOG.md` `## [Unreleased]`, add a `### Added` bullet:
  - "Session-level scoreboard — Princess wins and last places now persist across rematches within a room. Counts surface in the winner panel and inline next to player names in both UIs. `/abort` resets the score; rematches preserve it. [session-leaderboard]"

## 9. Verify

- [ ] 9.1 `black princess tests`.
- [ ] 9.2 `pylint princess tests` → 10.00/10.
- [ ] 9.3 `pytest -q` → green. Add room-level tests covering: fresh entry on create/join/bot; drop on remove_bot/leave; preserved on convert_to_bot; bump on game-over (Princess + last place + rounds_played for each pid); idempotency across two broadcasts of the same finished game; rematch preserves; abort zeroes.
- [ ] 9.4 `openspec validate --specs --strict` and `openspec validate session-leaderboard --strict`.
- [ ] 9.5 Manual smoke (desktop): create a room, add 2 bots, play 3 rounds with rematches; verify the winner panel's Session record line accumulates correctly and the opponent names show `· Princess N` once a bot has a win; click `/abort`, verify counts reset to zero on the next lobby render.
- [ ] 9.6 Manual smoke (mobile at 390 × 844): same scenario, verify the mobile winner panel and opponent chip badges render and stay legible.

## 10. Ship

- [ ] 10.1 Commit: `session-leaderboard: Track Princess wins and last places across rematches`.
- [ ] 10.2 Push the branch; open a PR.
- [ ] 10.3 Watch CI; auto-merge once green.

## 11. Wrap up

- [ ] 11.1 `openspec status --change session-leaderboard` → all done.
- [ ] 11.2 `/opsx:archive session-leaderboard` after merge.
