## ADDED Requirements

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
