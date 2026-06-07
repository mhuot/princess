## MODIFIED Requirements

### Requirement: Reverse-rank rule (configurable, default 5)

When the pile top is the room's configured **reverse rank**, the next play SHALL be a rank strictly less than that rank, with two exceptions: (a) 2 and 10 remain always legal (wild reset and burn respectively); (b) another card of the reverse rank itself is legal when `GameConfig.same_on_reverse` is true (the default).

The reverse rank is carried by `GameConfig.reverse_rank` (integer; valid values 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14 — i.e. excluding the wild ranks 2 and 10). The default value SHALL be **5**.

`GameConfig.same_on_reverse` (boolean, default `true`) replaces the previous `GameConfig.seven_on_seven` field.

`GameConfig.from_dict()` SHALL accept an integer `reverse_rank` in the legal set; any out-of-set value SHALL be silently coerced to the default (5). Unknown keys (including the legacy `seven_on_seven`) SHALL be silently ignored.

#### Scenario: 8 illegal on a 5 (default)

- **WHEN** `config.reverse_rank == 5` and the pile top is 5 and a player attempts an 8
- **THEN** the engine rejects with `error == "illegal play"`

#### Scenario: 3 legal on a 5 (default)

- **WHEN** `config.reverse_rank == 5` and the pile top is 5 and a player plays a 3
- **THEN** the play succeeds and the pile top is 3

#### Scenario: 5 on 5 is legal by default

- **WHEN** `config.reverse_rank == 5`, `config.same_on_reverse == true`, the pile top is 5 and a player plays a 5
- **THEN** the play succeeds and the pile top remains 5 (the reverse rule remains active)

#### Scenario: 5 on 5 is illegal when toggle is off

- **WHEN** `config.reverse_rank == 5`, `config.same_on_reverse == false`, the pile top is 5 and a player attempts a 5
- **THEN** the engine rejects the play

#### Scenario: Reverse rank can be changed per room

- **WHEN** a host posts `{"config": {"reverse_rank": 13, "same_on_reverse": true}}` before starting the round
- **THEN** the engine treats K (rank 13) as the reverse anchor; playing an 8 on a K is rejected; playing a 5 on a K succeeds; playing another K on a K succeeds

#### Scenario: 10 burns regardless of reverse rank

- **WHEN** the pile top is the configured reverse rank (any value) and a player plays a 10
- **THEN** the play succeeds, the pile burns, and the player plays again

#### Scenario: 2 resets regardless of reverse rank

- **WHEN** the pile top is the configured reverse rank and a player plays a 2
- **THEN** the play succeeds and the new pile top is 2 (any rank is legal next)

#### Scenario: Invalid reverse_rank coerces to default

- **WHEN** `GameConfig.from_dict({"reverse_rank": 10})` is called (10 is wild and not a legal reverse rank)
- **THEN** the resulting config has `reverse_rank == 5` and `same_on_reverse == true`

#### Scenario: Unknown legacy key is ignored

- **WHEN** `GameConfig.from_dict({"seven_on_seven": false})` is called
- **THEN** the resulting config has the defaults (`reverse_rank == 5`, `same_on_reverse == true`) and no error is raised

### Requirement: Per-room rule configuration

The engine SHALL accept a `GameConfig` at construction. The configuration SHALL be exposed via `public_state()` so the client can render rule-dependent UI. Unknown keys in `GameConfig.from_dict()` SHALL be silently ignored to keep clients forward-compatible. The serialized config SHALL include both `reverse_rank: int` and `same_on_reverse: bool`.

#### Scenario: Defaults applied when no config supplied

- **WHEN** a `Game` is constructed without an explicit config
- **THEN** `game.config.reverse_rank == 5` and `game.config.same_on_reverse == true`

#### Scenario: Config reflected in serialized state

- **WHEN** the client calls `view_for(pid)`
- **THEN** the returned dict's `config` field contains the integer `reverse_rank` and the boolean `same_on_reverse`
