## MODIFIED Requirements

### Requirement: Rename endpoint

The server SHALL expose `POST /api/rooms/{code}/rename` accepting `{"pid": <pid>, "new_name": <string 1–20 chars>}`. The endpoint SHALL allow a seated player to rename **themselves** at any time (lobby or mid-round). On success it SHALL update `seat.name` (using the **trimmed** form of `new_name`) and, if a game is in progress, also update the corresponding `Player.name` on `room.game`. After the update the server SHALL broadcast the updated lobby (when `room.game is None`) or state (when a game is in progress).

The endpoint SHALL respond:

- **404** if the room code is unknown.
- **404** if `pid` does not match any seat in the room.
- **422** if `new_name` is missing, empty, or longer than 20 characters (Pydantic validation).
- **409** if any **other** seat in the room already has a name that matches `new_name` after both are trimmed and case-folded. The 409 detail SHALL include the offending name in quotes — e.g., `"name 'Mike' is already taken in this room"`.

If `new_name.strip().casefold()` equals the caller's current `seat.name.strip().casefold()`, the endpoint SHALL return **200** without modifying state or broadcasting (rename-to-self is a no-op).

The caller's `pid` is the implicit authorization — anyone holding a pid for a seat can rename that seat. There is no host gate; the only valid rename target is the caller's own seat.

#### Scenario: Player renames themselves in the lobby

- **WHEN** a seated player posts `/rename` with their own `pid` and a valid `new_name` that doesn't collide with another seat
- **THEN** the response is 200, `seat.name` reflects the trimmed new name, and a lobby broadcast goes out

#### Scenario: Player renames themselves mid-round

- **WHEN** a seated player posts `/rename` with their own `pid` and a valid `new_name` while `room.game` is in progress
- **THEN** the response is 200, both `seat.name` and `room.game.player(pid).name` reflect the new name, and a state broadcast goes out

#### Scenario: Rename to a duplicate name is rejected

- **WHEN** `/rename` is called with a `new_name` matching another seat (case-insensitive, whitespace-trimmed)
- **THEN** the response is 409 and the detail is `"name '<existing_name>' is already taken in this room"`

#### Scenario: Rename to own current name is a no-op

- **WHEN** `/rename` is called with `new_name` that matches the caller's current seat name (case-insensitive, whitespace-trimmed)
- **THEN** the response is 200 but no state change or broadcast occurs

#### Scenario: Unknown pid rejected

- **WHEN** `/rename` is called with a `pid` that does not match any seat
- **THEN** the server responds 404

#### Scenario: Empty name rejected

- **WHEN** `/rename` is called with `new_name == ""`
- **THEN** the server responds 422

#### Scenario: Overlong name rejected

- **WHEN** `/rename` is called with a `new_name` longer than 20 characters
- **THEN** the server responds 422

## ADDED Requirements

### Requirement: Per-room unique names on join and create

The server SHALL enforce that no two seats in the same room share a name. Name comparison SHALL be **case-insensitive** and **whitespace-trimmed**.

`POST /api/rooms` (create room) SHALL trim the host's `name` before persisting it on the host's seat. No dedupe check is needed at create time because the host is always the first seat.

`POST /api/rooms/{code}/join` SHALL trim the joining player's `name` and reject the request with **409 Conflict** if any existing seat (human or bot) has a matching name. The 409 detail SHALL include the offending name in quotes — e.g., `"name 'Mike' is already taken in this room"`.

`POST /api/rooms/{code}/bot` SHALL continue to use `pick_bot_name(taken)` where `taken = {s.name for s in room.seats}` — this already covers human + bot names; no behavior change required, but the check SHALL remain in place.

#### Scenario: Duplicate human-on-human join is rejected

- **WHEN** a player attempts to `POST /join` with a name that already matches an existing human seat
- **THEN** the response is 409 with detail `"name '<existing_name>' is already taken in this room"`

#### Scenario: Case-insensitive duplicate join is rejected

- **WHEN** a player attempts to `POST /join` with `"mike"` while another seat is named `"Mike"`
- **THEN** the response is 409

#### Scenario: Whitespace-padded duplicate join is rejected

- **WHEN** a player attempts to `POST /join` with `"  Mike  "` while another seat is named `"Mike"`
- **THEN** the response is 409

#### Scenario: Joining with a bot's name is rejected

- **WHEN** the host adds a bot that happens to be named `"Galaxy Brain"`, and a human player attempts to `POST /join` with `"Galaxy Brain"`
- **THEN** the response is 409

#### Scenario: Bot pick avoids collision with existing humans

- **WHEN** the host POSTs `/bot` for a room whose host is named `"Galaxy Brain"`
- **THEN** the resulting bot seat's name is NOT `"Galaxy Brain"` (the bot-name picker already considers `{s.name for s in room.seats}`)

#### Scenario: Create-room trims the host's name

- **WHEN** the host POSTs `/api/rooms` with `name = "  Mike  "`
- **THEN** the host's seat name is `"Mike"` (trimmed)
