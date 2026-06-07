## ADDED Requirements

### Requirement: Bot decision interface

The AI module SHALL expose `decide(game, player) -> AIDecision` returning either an action `"play"` with a source + indices, or `"pickup"`. The decision SHALL never return invalid indices for the player's current active source.

#### Scenario: Returns pickup when no legal play

- **WHEN** the bot's hand has no card that satisfies the current rules
- **THEN** `decide` returns `AIDecision(action="pickup", source=None, indices=None)`

#### Scenario: Returns play with valid indices

- **WHEN** the bot has at least one legal card
- **THEN** `decide` returns `AIDecision(action="play", source=<active_source>, indices=[<valid index, …>])`

### Requirement: Prefer lowest legal non-special

The bot SHALL play the lowest legal rank that is not a 2 or a 10, preserving wild/burn cards for future emergencies. It SHALL play a single card unless rule-driven combinations apply (see four-of-a-kind below).

#### Scenario: Lowest non-special chosen

- **WHEN** the pile top is 4 and the bot's hand is `[10♠, 2♥, 5♦, 9♣]`
- **THEN** `decide` chooses the 5

### Requirement: Complete four-of-a-kind burns when possible

If the top of pile is rank R with a run of length k and the bot holds at least `4 − k` copies of R in hand, the bot SHALL play exactly `4 − k` of them to trigger the four-of-a-kind burn.

#### Scenario: Complete a 4-of-a-kind from 2-in-pile + 2-in-hand

- **WHEN** the pile is `[6♣, 6♦]`, the bot holds `[6♠, 6♥, 9♦]`, and 6 is legal
- **THEN** `decide` plays exactly two 6s to complete the four-of-a-kind

### Requirement: Use specials only when forced

The bot SHALL use a 10 (burn) or 2 (reset) only when no non-special legal play exists. It SHALL prefer burn (10) over reset (2) when both are options.

#### Scenario: Only specials left

- **WHEN** the bot has only `[10♠, 2♥]` legal against a pile top of K
- **THEN** `decide` plays the 10 first

### Requirement: 7-under and 7-on-7 are respected

The bot SHALL obey `is_legal_rank` (which already consults `GameConfig.seven_on_seven`). Specifically, when the pile top is 7 and `seven_on_seven` is enabled, a 7 in hand is considered legal; when disabled, it is not.

#### Scenario: Plays a low card when 7 is on top

- **WHEN** the pile top is 7 and the bot's hand is `[5♥, 8♦]`
- **THEN** `decide` chooses the 5 (the 8 is not legal)

### Requirement: Random blind face-down pick

When the bot's active source is face-down, the bot SHALL choose one face-down index uniformly at random.

#### Scenario: Blind selection

- **WHEN** the bot has 3 face-down cards remaining and no hand or face-up cards
- **THEN** `decide` returns a play action with one index drawn from `range(3)`

### Requirement: Swap-phase auto-pick

When the host starts a game, the server SHALL submit `set_face_up` on behalf of each bot, selecting the three highest-rank cards from their 6-card `choose` pile. This SHALL happen synchronously during `Room.start_game()` so the phase advances as soon as humans lock in.

#### Scenario: Bot picks top three by rank

- **WHEN** a bot's `choose` pile contains ranks `[3, 7, 9, 10, J, 2]`
- **THEN** the bot's face-up locks in as `[J, 10, 9]` (any tie-break is acceptable)

### Requirement: Bot turn loop

The server SHALL provide `Room.run_bots()` that advances the game while the current player is a bot. Each iteration SHALL: (a) wait `AI_THINK_SECONDS`, (b) call `decide`, (c) submit the chosen action, (d) broadcast state. The loop SHALL exit immediately when the current player becomes a human, the game ends, or the room enters a non-playing phase.

#### Scenario: Stops when human becomes current

- **WHEN** a bot's play advances the turn to a human player
- **THEN** `run_bots` returns before the next iteration

### Requirement: Bot loop safety cap

`run_bots` SHALL execute at most 30 actions per invocation. If the cap is reached the loop SHALL halt and log an `ERROR` line so a human can resume.

#### Scenario: Safety cap halts runaway loops

- **WHEN** `run_bots` would otherwise iterate past 30 actions in a single call
- **THEN** the loop exits and an error is recorded at `princess.room.<code>`

### Requirement: Force-pickup fallback

If the engine rejects a bot's chosen action (`result.ok == False`), the server SHALL force a pickup on that player so the turn advances. If the pickup also fails the loop SHALL log an `ERROR` and exit. Unhandled exceptions during a bot turn SHALL be caught and trigger the same fallback.

#### Scenario: Rejection triggers pickup

- **WHEN** `decide` returns a play that the engine rejects
- **THEN** the server calls `pickup` for that bot and emits a `WARN` log line

### Requirement: Bot decisions are logged

Every bot action SHALL be logged with at minimum the player id, name, action, source, indices, pile top, and the bot's hand summary at the time of decision.

#### Scenario: Decision context recorded

- **WHEN** a bot decides during play
- **THEN** a log entry with level `INFO` and prefix `bot decision pid=…` is written to the per-room logger
