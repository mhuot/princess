## Purpose

The `room-server` capability is Princess's FastAPI HTTP + WebSocket front door. It owns an in-memory room registry, the room lifecycle (create / join / add-bot / config / start / rematch / abort / leave), the WebSocket play/pickup/set_face_up message protocol, host-only authorization, the bot-name pool, and the four-character room code namespace. All state lives in process memory; a restart forgets every room.

## Requirements

### Requirement: Room creation

The server SHALL expose `POST /api/rooms` accepting `{"name": <string 1–20 chars>}`. On success it SHALL allocate a fresh 4-character alphanumeric room code (A–Z, 0–9), create a `Room` whose host is the caller, and return `{"code": <code>, "pid": <opaque id>}`.

#### Scenario: Code is unique within active rooms

- **WHEN** `POST /api/rooms` is called
- **THEN** the returned `code` does not collide with any existing room in the registry

#### Scenario: Host seat is recorded

- **WHEN** a room is created
- **THEN** the registry's room contains exactly one seat whose `pid == host_pid` and `is_bot == False`

### Requirement: Join by code

The server SHALL expose `POST /api/rooms/{code}/join` accepting `{"name": <string 1–20 chars>}`. It SHALL append a new human seat and broadcast the updated lobby to all connected sockets. The endpoint SHALL reject with HTTP 404 if the code is unknown, HTTP 409 if the game has already started, and HTTP 409 if the room is at capacity.

#### Scenario: Successful join

- **WHEN** a player calls `/join` on a lobby room with one open seat
- **THEN** they receive a new `pid` and the room now has one more seat

#### Scenario: Join after start rejected

- **WHEN** a player attempts to join a room whose game is already in progress
- **THEN** the server responds 409

### Requirement: Add bot (host only)

The server SHALL expose `POST /api/rooms/{code}/bot` accepting `{"host_pid": <pid>}`. The action SHALL be authorized only when `host_pid` matches `room.host_pid`. On success it SHALL pick a name from the SFW bot-name roster avoiding duplicates within the room, append a bot seat, broadcast the lobby, and return `{"ok": true, "name": <picked>}`.

#### Scenario: Non-host bot add rejected

- **WHEN** a non-host calls `/bot`
- **THEN** the server responds 403

#### Scenario: Names are unique per room

- **WHEN** the host adds bots into a room
- **THEN** no two seats in the room share the same name unless the name pool was exhausted (in which case a `Bot <4-digit>` fallback name is used)

### Requirement: Update room config (host only, pre-start)

The server SHALL expose `POST /api/rooms/{code}/config` accepting `{"host_pid": <pid>, "config": <dict>}`. It SHALL be host-only, allowed only before the game starts, and SHALL parse via `GameConfig.from_dict` (ignoring unknown keys). On success it SHALL broadcast the updated lobby.

#### Scenario: Toggle 7-on-7 off

- **WHEN** the host posts `{"config": {"seven_on_seven": false}}`
- **THEN** all connected clients receive a lobby broadcast with the updated config

#### Scenario: Config change after start rejected

- **WHEN** a host attempts to change config while `room.game` exists
- **THEN** the server responds 409

### Requirement: Start game (host only, ≥2 seats)

The server SHALL expose `POST /api/rooms/{code}/start` accepting `{"host_pid": <pid>}`. It SHALL be host-only and SHALL require at least 2 seats. On success it SHALL create a `Game` with `swap_phase=True` and the current `room.config`, auto-pick face-up cards for any bot seats, broadcast initial state, and run the bot loop.

#### Scenario: Single-seat start rejected

- **WHEN** the host calls `/start` with only one seat in the room
- **THEN** the server responds 409

#### Scenario: Already-started start rejected

- **WHEN** `room.game` already exists and the host calls `/start`
- **THEN** the server responds 409

### Requirement: Rematch (host only, post-game)

The server SHALL expose `POST /api/rooms/{code}/rematch` accepting `{"host_pid": <pid>}`. It SHALL require `room.game.game_over == True`. On success it SHALL discard the finished game, start a fresh one with the same seats and config, broadcast state, and run bots.

#### Scenario: Rematch before game-over rejected

- **WHEN** a host calls `/rematch` while the game is still in progress
- **THEN** the server responds 409 with `error == "no finished game to rematch"`

### Requirement: Abort game (host only)

The server SHALL expose `POST /api/rooms/{code}/abort` accepting `{"host_pid": <pid>}`. It SHALL set `room.game = None` and broadcast the lobby. The seats SHALL remain intact so the host can restart.

#### Scenario: Abort returns room to lobby

- **WHEN** a host calls `/abort` mid-game
- **THEN** all clients receive a `lobby` broadcast and `room.game` is None

### Requirement: Leave room (non-host)

The server SHALL expose `POST /api/rooms/{code}/leave` accepting `{"pid": <pid>}`. The host SHALL NOT be allowed to leave (must abort instead). On success the seat SHALL be removed and the room SHALL be re-broadcast.

#### Scenario: Host leave rejected

- **WHEN** the host calls `/leave`
- **THEN** the server responds 409 with `error == "host can't leave — use abort instead"`

### Requirement: WebSocket lifecycle

The server SHALL expose `WS /ws/{code}/{pid}`. On connect it SHALL attach the socket to the matching seat, send an initial `lobby` or `state` message reflecting current room status, and rebroadcast the lobby so other players see the connect state. On disconnect it SHALL detach the socket and rebroadcast.

#### Scenario: Mid-game connect receives state

- **WHEN** a player connects to `/ws/<code>/<their pid>` while `room.game` exists
- **THEN** the first message they receive is `{"type": "state", "view": …}`

### Requirement: WebSocket action protocol

The WebSocket SHALL accept JSON messages with `type` ∈ {`play`, `pickup`, `set_face_up`}. Other types SHALL elicit an `error` reply. Engine rejections (`result.ok == False`) SHALL elicit an `error` reply to the originating socket only; successful actions SHALL trigger a state broadcast to all sockets followed by `run_bots()`.

#### Scenario: Unknown message type returns error

- **WHEN** a client sends `{"type": "shuffle"}`
- **THEN** the server replies `{"type": "error", "message": "unknown type: shuffle"}`

#### Scenario: Rejected play returns error to sender only

- **WHEN** a client sends a `play` that the engine rejects
- **THEN** only the sender receives `{"type": "error", "message": <reason>}` and no state broadcast is sent

#### Scenario: Successful play broadcasts state

- **WHEN** a client sends a `play` that the engine accepts
- **THEN** every connected seat receives an updated `state` message before `run_bots` is invoked

### Requirement: Bot name pool

The server SHALL ship a SFW pool of 100 playful names mocking the player and asserting bot superiority. Names SHALL be ≤ 20 characters. `pick_bot_name(taken)` SHALL return a name not already used in the room, or fall back to `Bot <4-digit>` if all names are taken.

#### Scenario: Fallback when pool exhausted

- **WHEN** the `taken` set contains all 100 names
- **THEN** `pick_bot_name` returns a string matching `^Bot \d{4}$`

### Requirement: Room code format

Room codes SHALL be exactly 4 characters drawn from `A–Z` and `0–9`. The registry's `get(code)` SHALL be case-insensitive so users can type either case.

#### Scenario: Lookup is case-insensitive

- **WHEN** a room with code `XJ4Q` exists and `REGISTRY.get("xj4q")` is called
- **THEN** the same room is returned

### Requirement: Single-process state

The room registry SHALL live entirely in process memory; no persistent store is required. Server restart SHALL forget all rooms.

#### Scenario: Rooms cleared on restart

- **WHEN** the server process is restarted
- **THEN** all prior room codes return HTTP 404 from `/api/rooms/{code}/join`

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

### Requirement: Remove bot endpoint

The server SHALL expose `POST /api/rooms/{code}/remove_bot` accepting `{"host_pid": <pid>, "bot_pid": <pid>}`. The endpoint SHALL be host-only and SHALL be allowed **only while the room is in the lobby** (`room.game is None`). On success it SHALL remove the matching bot seat from `room.seats` and broadcast the updated lobby. The endpoint SHALL respond:

- **404** if the room code is unknown.
- **403** if `host_pid` does not match `room.host_pid`.
- **409** if `room.game is not None` (a game is in progress or finished).
- **404** if `bot_pid` does not match any seat in the room.
- **409** if the matching seat is not a bot (`seat.is_bot == False`).

#### Scenario: Host removes a bot successfully

- **WHEN** the host posts `/remove_bot` with a valid `bot_pid` for a bot seat
- **THEN** the response is 200, the seat is removed from `room.seats`, and a lobby broadcast goes out

#### Scenario: Non-host attempt rejected

- **WHEN** a non-host pid posts `/remove_bot`
- **THEN** the server responds 403

#### Scenario: Remove after game starts rejected

- **WHEN** `/remove_bot` is called while `room.game is not None`
- **THEN** the server responds 409

#### Scenario: Attempt to remove a human seat rejected

- **WHEN** `/remove_bot` is called with a `bot_pid` belonging to a human seat
- **THEN** the server responds 409

#### Scenario: Unknown bot_pid rejected

- **WHEN** `/remove_bot` is called with a `bot_pid` that does not match any seat
- **THEN** the server responds 404

### Requirement: Rename endpoint

The server SHALL expose `POST /api/rooms/{code}/rename` accepting `{"pid": <pid>, "new_name": <string 1–20 chars>}`. The endpoint SHALL allow a seated player to rename **themselves** at any time (lobby or mid-round). On success it SHALL update `seat.name` and, if a game is in progress, also update the corresponding `Player.name` on `room.game`. After the update the server SHALL broadcast the updated lobby (when `room.game is None`) or state (when a game is in progress).

The endpoint SHALL respond:

- **404** if the room code is unknown.
- **404** if `pid` does not match any seat in the room.
- **422** if `new_name` is missing, empty, or longer than 20 characters (Pydantic validation).

The caller's `pid` is the implicit authorization — anyone holding a pid for a seat can rename that seat. There is no host gate; the only valid rename target is the caller's own seat.

#### Scenario: Player renames themselves in the lobby

- **WHEN** a seated player posts `/rename` with their own `pid` and a valid `new_name`
- **THEN** the response is 200, `seat.name` reflects the new name, and a lobby broadcast goes out

#### Scenario: Player renames themselves mid-round

- **WHEN** a seated player posts `/rename` with their own `pid` and a valid `new_name` while `room.game` is in progress
- **THEN** the response is 200, both `seat.name` and `room.game.player(pid).name` reflect the new name, and a state broadcast goes out

#### Scenario: Unknown pid rejected

- **WHEN** `/rename` is called with a `pid` that does not match any seat
- **THEN** the server responds 404

#### Scenario: Empty name rejected

- **WHEN** `/rename` is called with `new_name == ""`
- **THEN** the server responds 422

#### Scenario: Overlong name rejected

- **WHEN** `/rename` is called with a `new_name` longer than 20 characters
- **THEN** the server responds 422

### Requirement: Mobile static routes

The server SHALL expose `GET /m` returning `static/mobile.html` and `GET /m/{code}` returning the same file. The shortcut URL form `<host>/m/<code>` allows a host to share a phone-friendly join link with friends.

These routes serve a **different** static page than `GET /` and `GET /room/{code}`; the latter pair continues to return `static/index.html` (the desktop UI).

#### Scenario: /m serves mobile.html

- **WHEN** a `GET /m` request reaches the server
- **THEN** the response body is the contents of `static/mobile.html`

#### Scenario: /m/{code} serves mobile.html

- **WHEN** a `GET /m/AB12` request reaches the server
- **THEN** the response body is the contents of `static/mobile.html` (the page reads the code from `location.pathname` at runtime)

#### Scenario: Desktop routes unchanged

- **WHEN** a `GET /` or `GET /room/AB12` request reaches the server
- **THEN** the response body is `static/index.html` — the desktop UI is unaffected by the addition of `/m`
