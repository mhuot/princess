## 1. Pre-conditions

- [x] 1.1 Confirm `baseline-princess-card-game` is archived and `openspec/specs/{ai-bot,room-server,web-frontend}/spec.md` exist (so the MODIFIED + ADDED deltas resolve).
- [x] 1.2 Note: this change does not depend on `show-last-three-moves`. Land in either order — but if both are in flight, sync the `web-frontend` delta first when archiving the later change.

## 2. Engine helper for "end round now"

- [x] 2.1 In `princess/game.py`, add `Game.end_round()` that:
  - returns early with `PlayResult(ok=False, error="game already over")` if `self.game_over` is True;
  - appends every non-finished player to `self.finished_order` sorted by ascending hand size (ties broken by seating index);
  - sets `self.game_over = True`;
  - records a `_record("round ended by host", ...)` entry;
  - returns `PlayResult(ok=True, game_over=True)`.
- [x] 2.2 Add `tests/test_game.py::test_end_round_ranks_by_hand_size`.
- [x] 2.3 Add `tests/test_game.py::test_end_round_no_op_when_game_over`.

## 3. Server: `/end_round`

- [x] 3.1 In `princess/server.py`, add `POST /api/rooms/{code}/end_round` taking `StartBody` (`host_pid`). Reject 404 / 403 / 409 as specified. On success: under `room.lock`, call `room.game.end_round()`, then broadcast state.
- [x] 3.2 Add tests in `tests/test_server.py` for: success path, non-host 403, already-over 409.

## 4. Server: `/leave` `convert_to_bot`

- [x] 4.1 In `princess/server.py`, extend `LeaveBody` with `convert_to_bot: bool = False`.
- [x] 4.2 In the handler: when `convert_to_bot` is true AND `room.game` is in progress, flip `seat.is_bot = True` instead of removing the seat. Then close the WebSocket (`seat.socket.close()` if set) and broadcast state.
- [x] 4.3 When `convert_to_bot` is true AND no game is in progress, behave like the existing remove-seat path.
- [x] 4.4 Host remains forbidden (existing 409).
- [x] 4.5 Add tests in `tests/test_server.py` for: convert-mid-game preserves seat with `is_bot=True`; convert-in-lobby removes the seat; host-with-flag still 409.

## 5. Server: cap policy on `run_bots`

- [x] 5.1 In `princess/rooms.py`, replace the hard `range(30)` with a `for step in range(self._bot_action_cap())` (or equivalent) where `_bot_action_cap()` returns 30 if any seat is `not is_bot`, else 1000.
- [x] 5.2 Update the "safety cap" error log to only fire when humans are seated (mixed room case).
- [x] 5.3 Add `tests/test_rooms.py` (new file) or extend `tests/test_ai.py` with a test that constructs a `Room` containing only bot seats, runs a synthetic short game (e.g., hand of length 1 each), and asserts the loop runs more than 30 actions and reaches `game_over`.

## 6. Server: orphan room cleanup

- [x] 6.1 Add `Room.last_activity_ts` (float, `time.monotonic()`-based). Initialize in `Room.__init__` and update inside `start_game`, `pickup`/`play`/`set_face_up` paths via the WebSocket handler, and each iteration of `run_bots`.
- [x] 6.2 Add `RoomRegistry.evict_idle(timeout_seconds: float)` that drops any room whose seats are all `socket is None` AND `now - last_activity_ts > timeout_seconds`.
- [x] 6.3 Call `REGISTRY.evict_idle(IDLE_TIMEOUT)` at the end of `_handle_message` and from each room-mutating REST endpoint. `IDLE_TIMEOUT` defaults to `int(os.environ.get("ROOM_IDLE_TIMEOUT_SECONDS", 300))`.
- [x] 6.4 Add a unit test that mocks `time.monotonic()` (or accepts an injected clock) and verifies eviction of disconnected idle rooms while sparing active rooms.

## 7. Frontend: quit modal

- [x] 7.1 In `static/index.html`, add a `<dialog id="quit-dialog">` with a heading and an action area. Hide it by default.
- [x] 7.2 In `static/styles.css`, style `#quit-dialog` (centered, accent border, accessible focus rings, `prefers-reduced-motion` respect).
- [x] 7.3 In `static/app.js`, replace the existing `quitGame()` confirm flow with one that opens `#quit-dialog`, builds the visible action set from `state.isHost` + `state.view?.phase === "playing"`, wires each action button to the right POST, and ensures `Esc` closes with no action.
- [x] 7.4 Move existing quit logic (`/abort`, `/leave`) into per-action handlers invoked from the dialog.
- [x] 7.5 Add the "Take over with a bot" handler (`/leave` with `convert_to_bot: true` then redirect).
- [x] 7.6 Add the "End the round now" handler (`/end_round`).

## 8. Frontend: "(bot)" / "(now a bot)" tag

- [x] 8.1 In `static/app.js`, add a `state.seatWasHuman = Set<pid>` populated each render — pids that have been seen with `is_bot: false` at any time during this round.
- [x] 8.2 In `renderOpponents()` and `renderLobby()`, append " (bot)" or " (now a bot)" to the displayed name based on the rules in the spec.
- [x] 8.3 Clear `state.seatWasHuman` on `view.game_over` transitions so the next round starts fresh.

## 9. Smoke tests

- [x] 9.1 Start the server. Create a room with the host, add one bot, join from a second tab as a non-host. Start the game. _(verified)_
- [x] 9.2 From the non-host tab, click Quit → "Take over with a bot." Confirm the seat shows "(now a bot)" in the host tab and the round continues. _(verified)_
- [x] 9.3 As host, click Quit → "End the round now." Confirm the winner banner shows in both tabs with the standings derived from hand sizes. _(verified)_
- [x] 9.4 Confirm via pytest that an all-bot room plays to `game_over` past the prior 30-step cap (`tests/test_rooms.py::test_bots_only_room_runs_past_human_cap`). The original smoke variant — "host closes tab mid-game with bots still seated, bots finish for the host's seat" — additionally requires auto-converting a disconnected human seat to a bot (or routing run_bots through disconnected human seats). That behavior is out of scope for this change; tracked as a future "host-disconnect autoconvert" change.
- [x] 9.5 Leave a room idle for the configured timeout; confirm `/join` of that code returns 404. _(Verified with `ROOM_IDLE_TIMEOUT_SECONDS=8`: created room TNNI, waited 12s, `/join` returned 404 + log line `evicted idle room code=TNNI`.)_

## 10. Wrap up

- [x] 10.1 Run `openspec validate handle-human-exit-mid-game --strict` and confirm valid.
- [x] 10.2 Run the full `pytest` suite — expect green. _(104/104 passed)_
- [x] 10.3 Archive via `/opsx:archive handle-human-exit-mid-game`.
