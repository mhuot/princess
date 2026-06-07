## ADDED Requirements

### Requirement: End-of-round endpoint

The server SHALL expose `POST /api/rooms/{code}/end_round` accepting `{"host_pid": <pid>}`. It SHALL be host-only and SHALL require an in-progress (non-`game_over`) game. On success it SHALL synthesize a game-over result: every player not already in `finished_order` SHALL be appended in **ascending hand-size order** (smaller hand finishes earlier). The engine's `game_over` SHALL be set to `True` and a state broadcast SHALL fire so all clients show the winner panel.

#### Scenario: Host ends a live round

- **WHEN** a 3-player game is in progress and the host calls `/end_round`
- **THEN** the broadcast state has `game_over: true` and `finished_order` contains all three pids ordered by ascending hand size

#### Scenario: Non-host call rejected

- **WHEN** a non-host pid calls `/end_round`
- **THEN** the server responds 403

#### Scenario: Already finished call rejected

- **WHEN** `room.game.game_over` is already `true` and `/end_round` is called
- **THEN** the server responds 409

### Requirement: Leave with bot conversion

The server SHALL accept an optional `convert_to_bot: bool` (default `false`) field on `POST /api/rooms/{code}/leave`. When `convert_to_bot` is `true` AND `room.game` is in progress, the leaver's `Seat.is_bot` SHALL be set to `True` in place (the pid remains the same, the player's hand / face-up / face-down / finished state remain untouched), the leaver's WebSocket SHALL be closed, and the room's lobby / state SHALL be re-broadcast so other clients render the seat as a bot.

When `convert_to_bot` is `true` but no game is in progress (lobby phase), the request SHALL behave as a normal leave — the seat is removed.

The host SHALL NOT be allowed to leave under any flag (matches existing rule); the host MUST use `/abort` or `/end_round`.

#### Scenario: Non-host converts seat to bot mid-game

- **WHEN** a non-host calls `/leave` with `convert_to_bot: true` mid-game
- **THEN** the seat is still present in `room.seats` but with `is_bot = True`; the player's hand size in the engine is unchanged

#### Scenario: Bot loop runs the converted seat

- **WHEN** the converted seat's pid becomes `current_pid`
- **THEN** `run_bots()` processes it as a normal bot turn (calling `decide()` on its hand)

### Requirement: Cap policy depends on connected humans

`Room.run_bots()` SHALL cap its per-call iteration count based on whether any **connected** human seats are currently in the room. A seat counts as a connected human when `is_bot == False AND socket is not None`:

- If at least one seat is a connected human, the cap remains 30 actions per call (matches the existing safety net for "humans are waiting").
- Otherwise (bot-only room, or every human seat has dropped its socket), the cap SHALL be raised to a high value sufficient to play any honest round to completion (e.g. 1000 actions) so the room can finish.

The hard "decide returned an illegal action → force pickup" and "exception during a bot turn → force pickup" fallbacks SHALL remain in place under either policy.

#### Scenario: Connected-human room keeps the strict cap

- **WHEN** at least one seat in the room is a connected human (`is_bot == False AND socket is not None`)
- **THEN** `run_bots()` exits the loop after at most 30 actions and logs an error if the cap is hit

#### Scenario: All-disconnected room runs to natural completion

- **WHEN** no seat in the room is a connected human (every seat is either a bot or a human with `socket is None`)
- **THEN** `run_bots()` continues until `game_over` is `True` (or the 1000-action lifetime ceiling), and the loop does not log a "safety cap" error on exit

### Requirement: Orphan room cleanup

The server SHALL evict any room from the registry whose seats are all disconnected (`socket is None`) AND whose `last_activity_ts` is more than 5 minutes old (configurable via `ROOM_IDLE_TIMEOUT_SECONDS`, default 300). The eviction check SHALL run opportunistically at the end of `_handle_message` and after each room-mutating REST endpoint; no separate scheduler or background task is required.

`Room.last_activity_ts` SHALL be updated on every action (play, pickup, set_face_up, config change, bot loop iteration). On connect, `last_activity_ts` SHALL be refreshed.

#### Scenario: Idle disconnected room is evicted

- **WHEN** a room has zero connected sockets and `last_activity_ts` is older than 5 minutes
- **THEN** the next post-action tick removes the room from the registry; subsequent `/join` calls receive HTTP 404

#### Scenario: Active rooms are never evicted

- **WHEN** a room is receiving WebSocket messages
- **THEN** `last_activity_ts` is refreshed and the room remains in the registry indefinitely

#### Scenario: Bot-only room is evicted after the round ends

- **WHEN** a bot-only room finishes its round and no socket reconnects within the idle window
- **THEN** the room is evicted from the registry
