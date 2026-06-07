## MODIFIED Requirements

### Requirement: Voluntary pickup

A player SHALL be able to pick up the entire discard pile on their turn. Picking up SHALL transfer every pile card into the player's hand, clear the pile, and end the picker's turn. The next non-finished player in seating order SHALL become current and SHALL play the first card on the now-empty pile. The pile MUST be non-empty for pickup to succeed.

The same turn-passing rule SHALL apply on every pickup path, including:

- The explicit `Game.pickup(pid)` call.
- The implicit pickup triggered when a face-down card is flipped, found illegal, and the player receives the pile plus the revealed card (`Game._play_face_down`).
- The bot force-pickup fallback in `Room.run_bots()` invoked when the bot's chosen action is rejected by the engine.

Under no circumstances SHALL the picker remain current after a pickup; only a burn (10 or four-of-a-kind) confers a same-player-again replay, and a burn is never a pickup.

#### Scenario: Voluntary pickup advances the turn

- **WHEN** it is `p0`'s turn in a 2-player game and they call `pickup("p0")` on a non-empty pile
- **THEN** the pile becomes empty, the pile cards are appended to `p0`'s hand, and `current_idx` advances so `current_player.pid == "p1"`

#### Scenario: Pickup rejected on empty pile

- **WHEN** the pile is empty and a player calls `pickup`
- **THEN** the engine rejects with `error == "no pile to pick up"` and the current player does not change

#### Scenario: Face-down illegal flip passes the turn

- **WHEN** face-down is `p0`'s active source, the pile top is K, and `p0`'s flipped face-down card is a 3 (illegal)
- **THEN** `p0`'s hand contains the prior pile plus the revealed 3, the pile is empty, `result.picked_up` is true, and `current_player.pid` is now the next non-finished player (`"p1"` in a 2-player game)

#### Scenario: Bot force-pickup fallback passes the turn

- **WHEN** a bot is current, the bot's `decide()` returns a `play` action that the engine rejects, and `Room.run_bots()` falls back to calling `self.game.pickup(bot.pid)`
- **THEN** the pile is added to the bot's hand, the pile is empty, and the next iteration of the bot loop observes a new `current_player` (a different seat than the bot that just picked up)

#### Scenario: Pickup skips finished players

- **WHEN** in a 3-player game, `p1` has already finished and it is `p0`'s turn
- **AND** `p0` calls `pickup` on a non-empty pile
- **THEN** the next `current_player` is `p2`, not `p1`
