## ADDED Requirements

### Requirement: Standard 52-card deck

The engine SHALL use one standard 52-card deck (ranks 2–14 where 11/12/13/14 are J/Q/K/A, suits S/H/D/C). The deck SHALL contain exactly 52 distinct cards.

#### Scenario: Deck is well-formed

- **WHEN** the engine constructs a fresh deck via `make_deck()`
- **THEN** it returns a list of 52 `Card` instances with no duplicates and all four suits represented for each rank

### Requirement: Player count

The engine SHALL support 2 to 4 players inclusive. Attempts to construct a game with fewer than 2 or more than 4 players SHALL be rejected.

#### Scenario: Reject one-player game

- **WHEN** `Game([single_player])` is constructed
- **THEN** the engine raises a `ValueError`

#### Scenario: Reject five-player game

- **WHEN** `Game([p1, p2, p3, p4, p5])` is constructed
- **THEN** the engine raises a `ValueError`

### Requirement: Initial deal without swap phase

When `swap_phase=False` (test/headless mode), the engine SHALL deal each player exactly 3 face-down cards, 3 face-up cards, and 3 cards in hand from a shuffled deck. The remaining 25 cards (with 3 players: 25; with 2: 34; with 4: 16) SHALL form the draw deck.

#### Scenario: Three players get nine cards each

- **WHEN** a 3-player game is dealt without swap phase
- **THEN** each player has exactly 3 hand, 3 face-up, and 3 face-down cards, and the deck holds 52 − 27 = 25 cards

### Requirement: Swap phase deal

When `swap_phase=True`, the engine SHALL deal each player 3 face-down cards and 6 "choose" cards. Both `hand` and `face_up` start empty. The engine's `phase` SHALL be `"setup"` until every player has locked in. The game SHALL NOT accept play actions during setup.

#### Scenario: Each player picks 3 of 6 for face-up

- **WHEN** a player calls `set_face_up(pid, [i, j, k])` with three valid distinct indices
- **THEN** those three `choose` cards become the player's `face_up` row, the remaining three become their `hand`, and `choose` is emptied

#### Scenario: Phase transitions when all are ready

- **WHEN** the last player locks in their face-up selection
- **THEN** `phase` becomes `"playing"` and the starting player is chosen

#### Scenario: Play action rejected during setup

- **WHEN** any player attempts `play(...)` while `phase == "setup"`
- **THEN** the engine returns `PlayResult(ok=False, error="still setting up — pick your face-up cards")`

### Requirement: Active source priority

A player SHALL play from their first non-empty source in the order hand → face-up → face-down. The engine SHALL reject plays from any source other than the active one.

#### Scenario: Must play from hand when hand has cards

- **WHEN** a player with cards in both `hand` and `face_up` attempts `play(pid, Source.FACE_UP, ...)`
- **THEN** the engine rejects with an error naming the expected source

#### Scenario: Face-up is active once hand and deck are empty

- **WHEN** a player's `hand` is empty and the deck is empty
- **AND** their `face_up` row is non-empty
- **THEN** `active_source()` returns `Source.FACE_UP`

### Requirement: Rank-based legality

A played card's rank SHALL be greater than or equal to the top-of-pile rank unless a special-card exception applies. An empty pile accepts any rank.

#### Scenario: Higher rank is legal

- **WHEN** the pile top is 5 and the player plays an 8
- **THEN** the play succeeds

#### Scenario: Lower rank is illegal

- **WHEN** the pile top is 8 and the player plays a 3
- **THEN** the engine rejects with `error == "illegal play"`

### Requirement: 2 is always legal and resets

A rank-2 card SHALL be playable on any pile top. After it is played, the next play SHALL be legal at any rank.

#### Scenario: 2 plays on a King

- **WHEN** the pile top is K and the player plays a 2
- **THEN** the play succeeds and the new pile top is 2

#### Scenario: Anything plays after a 2

- **WHEN** the pile top is 2
- **THEN** every rank from 3 through A is reported legal

### Requirement: 10 burns the pile

A rank-10 card SHALL be playable on any pile top. After it is played, the discard pile SHALL be cleared and the same player SHALL take another turn.

#### Scenario: 10 burns and replays

- **WHEN** the pile top is 5 and the player plays a 10
- **THEN** the pile becomes empty, `result.burned` is true, `result.same_player_again` is true, and the current player does not change

#### Scenario: 10 plays even when 7-under is active

- **WHEN** the pile top is 7 and the player plays a 10
- **THEN** the play succeeds and burns the pile

### Requirement: 7 forces the next play under 7

When the pile top is a 7, the next play SHALL be a rank strictly less than 7, with two exceptions: (a) 2 and 10 remain always legal; (b) another 7 is legal when `GameConfig.seven_on_seven` is true (the default).

#### Scenario: 8 is illegal on a 7

- **WHEN** the pile top is 7 and the player attempts an 8
- **THEN** the engine rejects with `error == "illegal play"`

#### Scenario: 5 is legal on a 7

- **WHEN** the pile top is 7 and the player plays a 5
- **THEN** the play succeeds and the pile top is 5

#### Scenario: 7 on 7 is legal by default

- **WHEN** the pile top is 7 and `config.seven_on_seven` is true and the player plays a 7
- **THEN** the play succeeds and the pile top is still 7 (under-7 rule remains active)

#### Scenario: 7 on 7 is illegal when toggle is off

- **WHEN** the pile top is 7 and `config.seven_on_seven` is false and the player attempts a 7
- **THEN** the engine rejects the play

### Requirement: Four of a kind burns the pile

When the four most recent cards on the pile share a rank (whether played in one turn or across multiple), the pile SHALL be cleared and the same player SHALL take another turn.

#### Scenario: Four of a kind in a single play

- **WHEN** a player plays all four 8s in one action onto a 5
- **THEN** the pile burns, `result.burned` is true, and `result.same_player_again` is true

#### Scenario: Four of a kind across plays

- **WHEN** the pile is [6♣, 6♦, 6♥] and the player plays the 6♠
- **THEN** the pile burns

### Requirement: Multi-card play must share a rank

A single play action SHALL contain one or more cards, all of the same rank. Mixed-rank plays SHALL be rejected.

#### Scenario: Two same-rank cards play together

- **WHEN** a player plays two 8s in one action onto a 5
- **THEN** the play succeeds and the top of pile is the second 8

#### Scenario: Mixed-rank play rejected

- **WHEN** a player attempts to play an 8 and a 9 together
- **THEN** the engine rejects the play

### Requirement: Voluntary pickup

A player SHALL be able to pick up the entire discard pile on their turn. Picking up SHALL transfer every pile card into the player's hand and advance the turn. The pile MUST be non-empty for pickup to succeed.

#### Scenario: Pickup advances the turn

- **WHEN** it is `p0`'s turn and they call `pickup(p0)`
- **THEN** the pile becomes empty, the pile cards are appended to `p0`'s hand, and the current player advances to the next non-finished player

#### Scenario: Pickup rejected on empty pile

- **WHEN** the pile is empty and a player calls `pickup`
- **THEN** the engine rejects with `error == "no pile to pick up"`

### Requirement: Hand refills from deck

After playing, the engine SHALL refill the player's hand to 3 cards from the top of the deck, drawing one at a time, until the hand reaches 3 or the deck is exhausted.

#### Scenario: Refill from non-empty deck

- **WHEN** a player plays one card from a hand of 3 and the deck has ≥1 card
- **THEN** the hand is refilled back to 3

#### Scenario: No refill from empty deck

- **WHEN** the deck is empty and a player plays
- **THEN** the hand is not refilled

### Requirement: Face-down blind play

When face-down is the active source, the engine SHALL accept exactly one index per action. The chosen card SHALL be revealed and tested for legality. If illegal, the player SHALL receive the entire pile plus the revealed card into their hand, and the turn SHALL advance.

#### Scenario: Legal blind play

- **WHEN** face-down is active, the pile top is 5, and the chosen face-down card is an 8
- **THEN** the play succeeds, `result.revealed == Card(8, …)`, and the 8 goes onto the pile

#### Scenario: Illegal blind play forces pickup

- **WHEN** face-down is active, the pile is [K, K], and the chosen face-down card is a 3
- **THEN** `result.picked_up` is true, the player's hand contains the pile plus the 3, the pile is empty, and the turn advances

### Requirement: Game over and finishing order

A player SHALL be marked finished the first turn they have no cards in any of their three rows. When only one player remains with cards, the engine SHALL set `game_over` to true and append the lone holdout to `finished_order` after the players who already finished. `finished_order[0]` SHALL be the round's winner.

#### Scenario: Two-player game ends when one runs out

- **WHEN** `p0` plays their last card in a 2-player game
- **THEN** `p0.finished` becomes true, `game_over` becomes true, and `finished_order == ["p0", "p1"]`

### Requirement: Per-room rule configuration

The engine SHALL accept a `GameConfig` at construction. The configuration SHALL be exposed via `public_state()` so the client can render rule-dependent UI. Unknown keys in `GameConfig.from_dict()` SHALL be ignored to keep clients forward-compatible.

#### Scenario: Default config enables 7-on-7

- **WHEN** a `Game` is constructed without an explicit config
- **THEN** `game.config.seven_on_seven` is true

#### Scenario: Config reflected in serialized state

- **WHEN** the client calls `view_for(pid)`
- **THEN** the returned dict contains a `config` key with the current `GameConfig`

### Requirement: Player-scoped view

The engine SHALL expose `view_for(pid)` returning a state dict that includes opponent face-up cards (visible to all), hand and face-down counts only (no card identities) for opponents, and full hand contents only for the calling player.

#### Scenario: Opponent hands hidden

- **WHEN** `view_for("p0")` is called
- **THEN** the entry for any player other than `p0` contains `hand_count` and `face_down_count` but no `hand` array
