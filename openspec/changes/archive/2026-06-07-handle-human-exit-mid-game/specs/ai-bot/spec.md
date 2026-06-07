## MODIFIED Requirements

### Requirement: Bot loop safety cap

`Room.run_bots()` SHALL apply an action cap that depends on whether any **connected** human (non-bot seat with a live WebSocket) remains in the room:

- **At least one connected human:** at most 30 actions per call. If the cap is reached the loop SHALL halt and log an `ERROR` line so a human can resume.
- **No connected humans (bot-only OR all humans disconnected):** the cap SHALL be raised so the round can finish naturally. A high ceiling such as 1000 lifetime actions SHALL apply as a runaway-loop backstop; reaching it SHALL also log an `ERROR` line.

The "connected human" check uses `seat.is_bot == False AND seat.socket is not None`. The cap policy SHALL be evaluated each `run_bots()` invocation so a mid-round conversion (or socket close) lifts the cap on the next loop entry.

#### Scenario: Connected-human room exits at 30

- **WHEN** `run_bots()` is invoked in a room with at least one human seat whose WebSocket is connected
- **AND** the loop would otherwise iterate past 30 actions in a single call
- **THEN** the loop exits and an error is recorded at `princess.room.<code>`

#### Scenario: All humans disconnected, loop plays out

- **WHEN** `run_bots()` is invoked in a room with no connected human sockets (either all seats are bots, or every human seat's socket is `None`)
- **THEN** the loop continues until `game_over` is `True` or the lifetime backstop trips, without exiting at 30

## ADDED Requirements

### Requirement: Bot takeover for converted seats

When a human seat is converted to a bot via `POST /leave` with `convert_to_bot: true`, the bot SHALL inherit the player's existing `hand`, `face_up`, `face_down`, and `finished` state without modification. Subsequent bot decisions for that seat SHALL go through the existing `decide()` heuristic with no special treatment.

#### Scenario: Hand is preserved across conversion

- **WHEN** a human seat with 5 hand cards is converted to a bot mid-round
- **THEN** the seat's player still has those exact 5 cards and `decide()` operates on them

#### Scenario: No re-deal on conversion

- **WHEN** a seat is converted to a bot
- **THEN** the engine state (deck, pile, finished_order, current_idx) is unchanged
