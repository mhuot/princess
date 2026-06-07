## MODIFIED Requirements

### Requirement: Player-scoped view

The engine SHALL expose `view_for(pid)` returning a state dict that includes opponent face-up cards (visible to all), hand and face-down counts only (no card identities) for opponents, and full hand contents only for the calling player. The dict SHALL include the most recent game events as a `last_actions` list of at most three entries, oldest at index 0, newest at the end. For backward compatibility the dict SHALL also include a `last_action` string equal to `last_actions[-1]["text"]` when the list is non-empty, or an empty string when it is empty.

Each entry in `last_actions` SHALL be an object with at least:

- `text` — a short human-readable description (e.g., `"Alice played 6S, 6C"`, `"Bot Genius picked up the pile"`).
- `actor_pid` — the pid of the player who caused the event, or `null` when no specific actor applies (e.g., the initial deal).
- `burned` — boolean; `true` when the event burned the pile.
- `picked_up` — boolean; `true` when the event was a pickup (voluntary, face-down-illegal, or bot fallback).
- `finished_pid` — pid of a player who finished on this event, or `null`.

The list SHALL be bounded — the engine MUST NOT allow it to grow past three entries; appending past the cap SHALL drop the oldest entry.

#### Scenario: Empty pile and fresh game starts with the deal entry

- **WHEN** a new game finishes its swap-phase deal and the first player becomes current
- **THEN** `view_for(pid)["last_actions"]` contains exactly one entry whose `text` describes the deal completion

#### Scenario: List never grows past three

- **WHEN** four or more game events are recorded in a row
- **THEN** `view_for(pid)["last_actions"]` contains exactly three entries, and the oldest event is no longer present

#### Scenario: Newest entry exposed under the legacy key

- **WHEN** the most recent event has text `"Bob picked up the pile"`
- **THEN** `view_for(pid)["last_action"]` equals `"Bob picked up the pile"` AND `view_for(pid)["last_actions"][-1]["text"]` equals the same string

#### Scenario: Burn flag is set for a 10 play

- **WHEN** a player plays a 10 onto a non-empty pile
- **THEN** the newest `last_actions` entry has `burned: true`

#### Scenario: Burn flag is set for a four-of-a-kind

- **WHEN** a player completes a four-of-a-kind on the pile
- **THEN** the newest `last_actions` entry has `burned: true`

#### Scenario: Picked-up flag is set for voluntary pickup

- **WHEN** a player voluntarily picks up the pile
- **THEN** the newest `last_actions` entry has `picked_up: true` and `burned: false`

#### Scenario: Picked-up flag is set for face-down illegal flip

- **WHEN** a face-down blind reveal is illegal and the player receives the pile + the revealed card
- **THEN** the newest `last_actions` entry has `picked_up: true`

#### Scenario: Finished flag is set when a player runs out

- **WHEN** a player's last card is played and the player becomes finished
- **THEN** the newest `last_actions` entry has `finished_pid` equal to that player's pid

### Requirement: Per-room rule configuration

The engine SHALL accept a `GameConfig` at construction. The configuration SHALL be exposed via `public_state()` so the client can render rule-dependent UI. Unknown keys in `GameConfig.from_dict()` SHALL be ignored to keep clients forward-compatible.

#### Scenario: Default config enables 7-on-7

- **WHEN** a `Game` is constructed without an explicit config
- **THEN** `game.config.seven_on_seven` is true

#### Scenario: Config reflected in serialized state

- **WHEN** the client calls `view_for(pid)`
- **THEN** the returned dict contains a `config` key with the current `GameConfig`
