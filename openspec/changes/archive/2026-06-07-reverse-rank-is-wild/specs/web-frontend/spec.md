## MODIFIED Requirements

### Requirement: Game view layout

While `phase == "playing"`, the frontend SHALL render: opponents row, pile area (deck count, top card, rule indicator), a **status stack** of up to three recent actions (newest at the bottom, oldest at the top), collapsible "Special cards & house rules" legend, the user's table (face-up + face-down on a single mini-row), the "Playing from: …" status, the sort-hand toolbar, the user's hand, and the Play/Pick-up action row. The "Your table" SHALL sit between the "Your cards" heading and the "Playing from:" status.

The pile-area **rule indicator** SHALL render dynamically based on `view.config.reverse_rank` (an integer). When the pile top equals the configured reverse rank, the indicator SHALL read `"play UNDER <R> (or another <R>)"` — where `<R>` is the human label for the rank (e.g., `"K"` for rank 13). The "(or another R)" suffix is always present because the reverse rank is always legal as a wild. When the pile is empty the indicator reads `"anything"`; otherwise `"match or beat"`.

The status-stack rendering, glyph rules, and `aria-live` behavior described in the prior version of this requirement are unchanged.

#### Scenario: Rule indicator on a 5 (default)

- **WHEN** the pile top is a 5 and `config.reverse_rank == 5`
- **THEN** `#rule-indicator` reads "play UNDER 5 (or another 5)"

#### Scenario: Rule indicator on a K-under room

- **WHEN** the pile top is a K and `config.reverse_rank == 13`
- **THEN** `#rule-indicator` reads "play UNDER K (or another K)"

#### Scenario: Pile top not the reverse rank

- **WHEN** the pile top is an 8 and `config.reverse_rank == 5`
- **THEN** `#rule-indicator` reads "match or beat"

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

### Requirement: Lobby renders seats and host controls

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config controls as `disabled` with a note that only the host can change them.

The House rules panel SHALL contain at minimum the **Reverse rank** `<select>` whose options list the legal reverse ranks (3, 4, 5, 6, 7, 8, 9, J, Q, K, A). The displayed text uses the human label (J/Q/K/A) but the submitted value is the integer rank (11/12/13/14). The panel SHALL NOT include a "same rank on reverse" control — the reverse rank is always legal as a wild.

Changing the dropdown SHALL trigger a `POST /api/rooms/<code>/config` containing `{"reverse_rank": <int>}`. Non-hosts see the control disabled with the existing `#config-readonly-note`.

#### Scenario: Non-host sees disabled control

- **WHEN** a non-host renders the lobby
- **THEN** the `<select>` for reverse rank is `disabled` and `#config-readonly-note` is visible

#### Scenario: Selecting K posts the correct integer

- **WHEN** the host changes the dropdown to "K"
- **THEN** the `POST /api/rooms/<code>/config` body is `{"host_pid": …, "config": {"reverse_rank": 13}}`

#### Scenario: Default selection is 5

- **WHEN** a fresh lobby is rendered with no prior config change
- **THEN** the dropdown shows "5" selected

#### Scenario: No same-on-reverse checkbox

- **WHEN** the House rules panel is rendered
- **THEN** there is no element with id `cfg-same-on-reverse`

### Requirement: Hover tooltip

Every rendered card (full or mini, including the pile top) SHALL carry a `title` attribute. For rank 2 the tooltip SHALL include the wild-reset description. For rank 10 the tooltip SHALL include the burn description. For the rank equal to `view.config.reverse_rank` the tooltip SHALL include `"Wild + Reverse — always legal; next play must be UNDER <R>."` (where `<R>` is the rank's human label). For all other ranks the tooltip SHALL include just the card's label.

#### Scenario: 5 hover in a default room names both effects

- **WHEN** the user hovers a 5 card and `config.reverse_rank == 5`
- **THEN** the tooltip text is `"5<suit>\nWild + Reverse — always legal; next play must be UNDER 5."`

#### Scenario: 7 hover in a default room is plain

- **WHEN** the user hovers a 7 card and `config.reverse_rank == 5`
- **THEN** the tooltip text is just the card's label (no wild/reverse blurb)

#### Scenario: 7 hover when reverse rank is configured to 7

- **WHEN** the user hovers a 7 card and `config.reverse_rank == 7`
- **THEN** the tooltip text includes `"Wild + Reverse — always legal; next play must be UNDER 7."`
