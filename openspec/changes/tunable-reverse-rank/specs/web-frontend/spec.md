## MODIFIED Requirements

### Requirement: Game view layout

While `phase == "playing"`, the frontend SHALL render: opponents row, pile area (deck count, top card, rule indicator), a **status stack** of up to three recent actions (newest at the bottom, oldest at the top), collapsible "Special cards & house rules" legend, the user's table (face-up + face-down on a single mini-row), the "Playing from: …" status, the sort-hand toolbar, the user's hand, and the Play/Pick-up action row. The "Your table" SHALL sit between the "Your cards" heading and the "Playing from:" status.

The pile-area **rule indicator** SHALL render dynamically based on `view.config.reverse_rank` (an integer) and `view.config.same_on_reverse` (a boolean). When the pile top equals the configured reverse rank, the indicator SHALL read either `"play UNDER <R> (or another <R>)"` when `same_on_reverse` is true, or `"must play UNDER <R>"` when false — where `<R>` is the human label for the rank (e.g., `"K"` for rank 13). When the pile is empty the indicator reads `"anything"`; otherwise `"match or beat"`.

The status-stack rendering, glyph rules, and aria-live behavior described in the prior version of this requirement are unchanged.

#### Scenario: Rule indicator with default 5-under

- **WHEN** the pile top is a 5 and `config.reverse_rank == 5` and `config.same_on_reverse == true`
- **THEN** `#rule-indicator` reads "play UNDER 5 (or another 5)"

#### Scenario: Rule indicator with K-under

- **WHEN** the pile top is a K and `config.reverse_rank == 13`
- **THEN** `#rule-indicator` reads "play UNDER K (or another K)" (or, with `same_on_reverse == false`, "must play UNDER K")

#### Scenario: Pile top not the reverse rank

- **WHEN** the pile top is an 8 and `config.reverse_rank == 5`
- **THEN** `#rule-indicator` reads "match or beat"

### Requirement: Lobby renders seats and host controls

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config controls as `disabled` with a note that only the host can change them.

The House rules panel SHALL contain at minimum:

- A **Reverse rank** `<select>` whose options list the legal reverse ranks (3, 4, 5, 6, 7, 8, 9, J, Q, K, A). The displayed text uses the human label (J/Q/K/A) but the submitted value is the integer rank (11/12/13/14).
- An **Allow same rank on reverse** `<input type="checkbox">` (was "Allow 7 on 7" pre-change).

Changing either control SHALL trigger a `POST /api/rooms/<code>/config` containing both fields. Non-hosts see both controls disabled with the existing `#config-readonly-note`.

#### Scenario: Non-host sees disabled controls

- **WHEN** a non-host renders the lobby
- **THEN** the `<select>` for reverse rank and the same-on-reverse checkbox are both `disabled` and `#config-readonly-note` is visible

#### Scenario: Selecting K as reverse rank posts the correct integer

- **WHEN** the host changes the dropdown to "K"
- **THEN** the `POST /api/rooms/<code>/config` body is `{"host_pid": …, "config": {"reverse_rank": 13, "same_on_reverse": <current toggle>}}`

#### Scenario: Default selection is 5

- **WHEN** a fresh lobby is rendered with no prior config change
- **THEN** the dropdown shows "5" selected and the same-on-reverse checkbox is checked

### Requirement: Hover tooltip

Every rendered card (full or mini, including the pile top) SHALL carry a `title` attribute. For ranks 2 and 10, the tooltip SHALL include the standard wild/burn description. For the rank equal to `view.config.reverse_rank`, the tooltip SHALL include `"Reverse — next card must be UNDER <R>"` (where `<R>` is the rank's human label). For all other ranks the tooltip SHALL include just the card's label.

#### Scenario: 5 hover in a default room mentions the reverse rule

- **WHEN** the user hovers a 5 card and `config.reverse_rank == 5`
- **THEN** the tooltip text is `"5<suit>\nReverse — next card must be UNDER 5."`

#### Scenario: 7 hover in a default room is plain

- **WHEN** the user hovers a 7 card and `config.reverse_rank == 5`
- **THEN** the tooltip text is just the card's label (no reverse rule blurb)

#### Scenario: 7 hover when reverse rank is configured to 7

- **WHEN** the user hovers a 7 card and `config.reverse_rank == 7`
- **THEN** the tooltip text includes `"Reverse — next card must be UNDER 7."`
