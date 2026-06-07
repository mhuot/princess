## ADDED Requirements

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
