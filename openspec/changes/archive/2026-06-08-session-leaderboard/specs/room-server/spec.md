## ADDED Requirements

### Requirement: Session scoreboard

`Room` SHALL maintain a session-level scoreboard tracking per-seat counters that persist across rematches within the same room lifetime. The scoreboard SHALL be exposed at `Room.scoreboard: dict[str, dict[str, int]]` keyed by `Seat.pid`. Each entry SHALL contain at least three integer counters:

- `princess_wins` — number of rounds in this session in which the seat finished first (i.e., was `finished_order[0]` at game-over).
- `last_places` — number of rounds in which the seat finished last (i.e., was `finished_order[-1]`).
- `rounds_played` — number of rounds in which the seat appeared in `finished_order` at game-over.

A fresh entry with all three counters at `0` SHALL be created whenever a new seat is added to the room — via room creation, `/api/rooms/{code}/join`, `/api/rooms/{code}/bot`, or a `convert_to_bot` flag on `/api/rooms/{code}/leave` (the convert path keeps the existing entry untouched because the pid is unchanged).

A seat's entry SHALL be dropped when the seat is removed via `/api/rooms/{code}/remove_bot` or via `/api/rooms/{code}/leave` without `convert_to_bot`.

The room SHALL bump the scoreboard exactly once per round when `room.game.game_over` flips to `True`. The bump SHALL apply the following updates:

- `scoreboard[finished_order[0]]["princess_wins"] += 1`
- `scoreboard[finished_order[-1]]["last_places"] += 1`
- For every pid in `finished_order`, `scoreboard[pid]["rounds_played"] += 1`

The bump SHALL be idempotent — a state re-broadcast for the same already-finished `Game` SHALL NOT bump again. The implementation SHALL track which round (or whether the current `Game` instance) has already been counted so that a reconnect-driven re-broadcast, a host-only `/end_round` re-render, or any other repeat does not double-count. The "already counted" marker SHALL clear on the next `start_game` / rematch so the new round can be counted when it ends.

`/api/rooms/{code}/abort` SHALL reset every entry in the scoreboard to `{princess_wins: 0, last_places: 0, rounds_played: 0}`. Entries themselves SHALL NOT be dropped (the seats remain after abort). `/api/rooms/{code}/rematch` SHALL leave the scoreboard untouched.

When the room is evicted by the idle-room sweep, the scoreboard is dropped along with the rest of the room state (no special handling required).

#### Scenario: Fresh entry on seat creation

- **WHEN** a `Room` is created via `POST /api/rooms`
- **THEN** `room.scoreboard[host_pid] == {"princess_wins": 0, "last_places": 0, "rounds_played": 0}`

#### Scenario: Join adds an entry

- **WHEN** a player joins via `POST /api/rooms/{code}/join` and receives `pid = "p2"`
- **THEN** `room.scoreboard["p2"] == {"princess_wins": 0, "last_places": 0, "rounds_played": 0}`

#### Scenario: Add-bot adds an entry

- **WHEN** the host POSTs `/api/rooms/{code}/bot` and a new bot seat is created
- **THEN** the bot's pid exists as a fresh-zero key in `room.scoreboard`

#### Scenario: Remove-bot drops the entry

- **WHEN** the host POSTs `/api/rooms/{code}/remove_bot` with a valid bot pid
- **THEN** that pid is absent from `room.scoreboard` after the call

#### Scenario: Leave (without convert_to_bot) drops the entry

- **WHEN** a non-host POSTs `/api/rooms/{code}/leave` with `convert_to_bot: false`
- **THEN** that pid is absent from `room.scoreboard` after the call

#### Scenario: Leave with convert_to_bot preserves the entry

- **WHEN** a non-host POSTs `/api/rooms/{code}/leave` with `convert_to_bot: true` mid-game
- **THEN** that pid's `room.scoreboard` entry is unchanged (the seat stays under the same pid as a bot)

#### Scenario: Game-over bumps the winner and the last-place seat

- **WHEN** a 3-player round ends with `finished_order == ["p1", "p0", "p2"]` and broadcast_state fires
- **THEN** `room.scoreboard["p1"]["princess_wins"]` is incremented by 1, `room.scoreboard["p2"]["last_places"]` is incremented by 1, and each of `p0`, `p1`, `p2` sees `rounds_played` increase by 1

#### Scenario: Re-broadcast of a finished game does not double-count

- **WHEN** a round ends, broadcast_state fires once, then a player reconnects and broadcast_state fires a second time for the same finished `Game`
- **THEN** every counter that was bumped on the first broadcast remains at the same value after the second broadcast (no double count)

#### Scenario: Rematch preserves counters

- **WHEN** a round ends, the scoreboard bumps, and the host POSTs `/api/rooms/{code}/rematch`
- **THEN** the scoreboard counters retain their previous values after the new game starts, and a subsequent game-over for the new round bumps from those values (not from zero)

#### Scenario: Abort zeroes the scoreboard

- **WHEN** the host POSTs `/api/rooms/{code}/abort` while scoreboard entries are non-zero
- **THEN** every entry in `room.scoreboard` is reset to `{"princess_wins": 0, "last_places": 0, "rounds_played": 0}` and no entry is dropped (the seats persist)

#### Scenario: 2-player round bumps both Princess and last place on different pids

- **WHEN** a 2-player round ends with `finished_order == ["p0", "p1"]`
- **THEN** `room.scoreboard["p0"]["princess_wins"] += 1` and `room.scoreboard["p1"]["last_places"] += 1` — both fire from the same single round

### Requirement: Scoreboard in lobby and state broadcasts

`Room.public_lobby()` SHALL include a `"scoreboard"` field at the top level — a dict mapping each seated pid to its scoreboard entry (`{princess_wins, last_places, rounds_played}`). The set of keys SHALL match the set of pids in `room.seats`.

The WebSocket `{"type": "state", ...}` message produced for each seated, connected player SHALL include the room's scoreboard at the top level of the envelope, alongside the existing `view` field — `{"type": "state", "view": <view_for_pid>, "scoreboard": {pid: {...}, ...}}`. The engine's `view_for(pid)` SHALL NOT be modified.

The scoreboard broadcast SHALL fire on every existing broadcast trigger — connect, lobby change, config change, action, game-over — so clients reflect the latest counters without a separate request.

#### Scenario: Lobby broadcast includes scoreboard

- **WHEN** a client receives a `{"type": "lobby", "room": ...}` message
- **THEN** the `room` object contains a `"scoreboard"` key whose value is a dict with one entry per seated pid, and each entry contains `princess_wins`, `last_places`, `rounds_played` as integers

#### Scenario: State broadcast includes scoreboard

- **WHEN** a seated player's WebSocket receives a `{"type": "state", ...}` message
- **THEN** the message contains a top-level `"scoreboard"` key whose value mirrors `room.scoreboard` at the moment of the broadcast

#### Scenario: Scoreboard reflects the latest bump

- **WHEN** a round ends and the broadcast state is delivered
- **THEN** the `"scoreboard"` field in the broadcast already reflects the post-bump counters (the winner shows `princess_wins` one higher than before the round)
