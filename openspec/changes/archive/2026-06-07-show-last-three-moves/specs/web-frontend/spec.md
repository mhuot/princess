## MODIFIED Requirements

### Requirement: Game view layout

While `phase == "playing"`, the frontend SHALL render: opponents row, pile area (deck count, top card, rule indicator), a **status stack** of up to three recent actions (newest at the bottom, oldest at the top), collapsible "Special cards & house rules" legend, the user's table (face-up + face-down on a single mini-row), the "Playing from: …" status, the sort-hand toolbar, the user's hand, and the Play/Pick-up action row. The "Your table" SHALL sit between the "Your cards" heading and the "Playing from:" status.

The status stack SHALL render each entry from `view.last_actions` as its own line. The newest entry SHALL be visually emphasized (full opacity, accent border) and SHALL carry the "— Your turn." / "— <name>'s turn." suffix. Older entries SHALL be dimmed (lower opacity) and SHALL NOT carry the turn suffix. Entries with `burned: true` SHALL include a fire glyph (🔥) at the end of the text. Entries with `picked_up: true` SHALL include a pickup glyph (e.g., ↑) at the end of the text. Entries with `finished_pid` set SHALL include a crown glyph (👑) and the finishing player's name.

The status-stack container SHALL be a single `aria-live="polite"` region whose announcement is limited to the newest entry. Older entries SHALL be marked `aria-hidden="true"` so screen readers don't re-announce them on every state broadcast.

The frontend MUST tolerate older servers that emit only `view.last_action` (string) and no `last_actions` array; in that case it SHALL render a single-entry stack from the legacy field.

#### Scenario: Pile rule indicator reflects the engine rule

- **WHEN** the pile top is a 7 and `config.seven_on_seven` is true
- **THEN** `#rule-indicator` reads "play UNDER 7 (or another 7)"

#### Scenario: Pile rule indicator with 7-on-7 disabled

- **WHEN** the pile top is a 7 and `config.seven_on_seven` is false
- **THEN** `#rule-indicator` reads "must play UNDER 7"

#### Scenario: Three-line status stack after a bot burn chain

- **WHEN** the broadcast state has `last_actions` of length 3 — `[ "Alice played 8H", "Bot Genius played 10S 🔥", "Bot Genius played 4D" ]`
- **THEN** the `#status-stack` shows three lines in that order, the bottom line is at full opacity with the turn suffix appended, and the top two lines are dimmed without a suffix

#### Scenario: Single entry renders as one line

- **WHEN** `last_actions` contains only the initial "deal complete" entry
- **THEN** `#status-stack` shows exactly one line, no dimmed entries above it, and the line carries the current player's turn suffix

#### Scenario: Burn glyph appears

- **WHEN** any entry in `last_actions` has `burned: true`
- **THEN** that line's rendered text ends with the fire glyph 🔥

#### Scenario: Finish glyph appears with player name

- **WHEN** an entry has `finished_pid == "p2"` and `p2.name == "Bob"`
- **THEN** that line includes the 👑 glyph and Bob's name

#### Scenario: Legacy server fallback

- **WHEN** the broadcast omits `last_actions` but includes `last_action: "Alice played 9C"`
- **THEN** the status stack renders a single line "Alice played 9C — <turn suffix>"
