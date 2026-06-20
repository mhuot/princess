## ADDED Requirements

### Requirement: Global leaderboard write-through on game-over

The room SHALL, after bumping its in-memory `scoreboard` for a finished game, forward the same event to the `RoomRegistry` so the persistent `leaderboard` table is updated. Only human seats (`seat.is_bot == False`) SHALL be forwarded. The forwarded payload SHALL include `finished_order` and a `{pid: display_name}` map for the included seats. The forward SHALL inherit the same idempotency guarantee as the in-memory bump (no double-count on rebroadcast).

#### Scenario: Forward humans only

- **WHEN** a game ends with finished order `[human_pid, bot_pid]`
- **THEN** the registry's leaderboard upsert is called once with only the human's pid + name

#### Scenario: No forward without DB

- **WHEN** the registry has no SQLite connection bound
- **THEN** the room still bumps its in-memory scoreboard and the forward is a no-op

#### Scenario: Forward inherits idempotency

- **WHEN** the same finished game triggers two broadcasts
- **THEN** the registry's leaderboard write is invoked at most once for that game
