## MODIFIED Requirements

### Requirement: Reverse-rank rule (configurable, default 5)

The reverse rank SHALL be **always legal regardless of pile top**, joining 2 (wild reset) and 10 (burn) as a third unconditionally-legal rank. The configured reverse rank is carried by `GameConfig.reverse_rank` (integer; default **5**; valid 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14 — i.e. excluding 2 and 10).

When a card whose rank equals the reverse rank lands on the pile, the **next** play SHALL be a rank strictly less than the reverse rank, with the standing exceptions: 2 and 10 remain always legal, and another card of the reverse rank is itself always legal (because the reverse rank is wild).

`GameConfig.same_on_reverse` is removed. `GameConfig.from_dict()` SHALL silently ignore any incoming `same_on_reverse` key (and the legacy `seven_on_seven` key) for forward compatibility. An invalid `reverse_rank` value (anything not in the legal set) SHALL be silently coerced to the default 5.

#### Scenario: Reverse rank legal on a King (default 5)

- **WHEN** `config.reverse_rank == 5` and the pile top is K and a player plays a 5
- **THEN** the play succeeds and the pile top is 5

#### Scenario: Reverse rank legal on a 7

- **WHEN** `config.reverse_rank == 5` and the pile top is 7 and a player plays a 5
- **THEN** the play succeeds and the pile top is 5

#### Scenario: 8 illegal on a 5

- **WHEN** `config.reverse_rank == 5` and the pile top is 5 and a player attempts an 8
- **THEN** the engine rejects with `error == "illegal play"`

#### Scenario: 3 legal on a 5 (under-rule still active)

- **WHEN** `config.reverse_rank == 5` and the pile top is 5 and a player plays a 3
- **THEN** the play succeeds and the pile top is 3

#### Scenario: 5 on 5 always legal

- **WHEN** `config.reverse_rank == 5` and the pile top is 5 and a player plays a 5
- **THEN** the play succeeds and the pile top is still 5 (the under-rule remains active)

#### Scenario: Reverse rank can be changed per room

- **WHEN** a host posts `{"config": {"reverse_rank": 13}}` before starting the round
- **THEN** the engine treats K as the reverse anchor: K is always legal regardless of pile top, and playing an 8 onto a K is rejected (because the under-K rule activates)

#### Scenario: 10 burns regardless of reverse rank

- **WHEN** the pile top is the configured reverse rank and a player plays a 10
- **THEN** the play succeeds and the pile burns

#### Scenario: 2 resets regardless of reverse rank

- **WHEN** the pile top is the configured reverse rank and a player plays a 2
- **THEN** the play succeeds and the new pile top is 2

#### Scenario: Invalid reverse_rank coerces to default

- **WHEN** `GameConfig.from_dict({"reverse_rank": 10})` is called (10 is wild, not a legal reverse value)
- **THEN** the resulting config has `reverse_rank == 5`

#### Scenario: Legacy same_on_reverse and seven_on_seven keys ignored

- **WHEN** `GameConfig.from_dict({"reverse_rank": 7, "same_on_reverse": false, "seven_on_seven": false})` is called
- **THEN** the resulting config has `reverse_rank == 7` and no `same_on_reverse` attribute

### Requirement: Per-room rule configuration

The engine SHALL accept a `GameConfig` at construction. The configuration SHALL be exposed via `public_state()` so the client can render rule-dependent UI. Unknown keys in `GameConfig.from_dict()` SHALL be silently ignored to keep clients forward-compatible. The serialized config SHALL include `reverse_rank: int` (and SHALL NOT include `same_on_reverse`).

#### Scenario: Defaults applied when no config supplied

- **WHEN** a `Game` is constructed without an explicit config
- **THEN** `game.config.reverse_rank == 5`

#### Scenario: Config reflected in serialized state

- **WHEN** the client calls `view_for(pid)`
- **THEN** the returned dict's `config` field contains the integer `reverse_rank` and does not contain `same_on_reverse`
