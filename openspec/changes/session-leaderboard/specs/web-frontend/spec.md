## MODIFIED Requirements

### Requirement: End-of-round panel

When `view.game_over` is true the frontend SHALL hide the play surface entirely (opponents, pile area, legend, status stack, setup area, your-area) and render only the `#game-over` panel containing: a "Winner!" kicker, the winner's name in large gold type, a subtitle (a special line if the user is the winner), a **winning-action line** describing the move that ended the round, the full finishing-order list (1st = "Princess", last = "last place"), a **Session record line** (this change) summarizing the calling user's session counters, a "Play a rematch" button (host only), a "Back to lobby" button, and (for non-hosts) a "Waiting for the host…" note.

The frontend SHALL hide the play surface through both the `hidden` attribute on each element AND CSS that enforces the attribute (`<selector>[hidden] { display: none !important; }`) so author display rules cannot silently override the attribute. Any element rendered with `display: flex`, `display: block`, or other explicit display value MUST have a paired `[hidden]` rule that forces `display: none`.

The **winning-action line** SHALL be sourced from `view.last_actions[-1]` (the newest action in the engine's bounded history). It SHALL be rendered with the same glyphs used by the status stack — `🔥` when `burned`, `↑` when `picked_up`, `👑 <player name>` when `finished_pid` is set. If `last_actions` is empty (impossible in normal play but possible defensively), the line SHALL be omitted gracefully.

The **Session record line** SHALL be sourced from the room-server's scoreboard broadcast (the top-level `scoreboard` field on the `state` envelope). It SHALL render the calling user's entry only, in the form `Session record: Princess <P> · Last place <L> · <R> rounds`, where `<P>` is `princess_wins`, `<L>` is `last_places`, and `<R>` is `rounds_played`. When `last_places == 0` the `· Last place 0` segment MAY be elided to reduce noise (implementation choice). When `rounds_played == 0` the line SHALL be hidden entirely. The line SHALL sit below the finishing-order list and above the rematch button so the eye reads finish-this-round, then how-we're-doing, then what's-next.

#### Scenario: Host sees rematch button

- **WHEN** the game ends and the user is the host
- **THEN** the `#rematch-btn` is visible and `#rematch-note` is hidden

#### Scenario: Non-host sees waiting note

- **WHEN** the game ends and the user is not the host
- **THEN** `#rematch-btn` is hidden and `#rematch-note` reads "Waiting for the host to start a rematch…"

#### Scenario: Play surface is fully hidden

- **WHEN** the game ends and the winner panel renders
- **THEN** none of `#opponents`, `.pile-area`, `.legend`, `#status-stack`, `#setup-area`, `#you-area` has any visible content — each is `display: none` even though their normal rule sets `display: flex` or `display: block`

#### Scenario: Winning action shown in panel

- **WHEN** the round ends because Mike flipped his last face-down card
- **THEN** the `#game-over` panel contains a line reading "Mike flipped <card> 👑 Mike" between the winner subtitle and the results list

#### Scenario: Winning action with burn glyph

- **WHEN** the round ends on a 10-burn that empties the player's hand
- **THEN** the winning-action line ends with `🔥 👑 <player name>`

#### Scenario: Status stack stays hidden after game-over

- **WHEN** the game ends and a state-broadcast triggers a re-render of `renderGame`
- **THEN** the stale `#status-stack` content is no longer visible, regardless of whether `renderStatus` was called in the game-over branch

#### Scenario: Session record line rendered after rematches

- **WHEN** the user has played 4 rounds in this room and the broadcast `scoreboard[user_pid]` is `{"princess_wins": 3, "last_places": 1, "rounds_played": 4}`
- **THEN** the winner panel contains a "Session record: Princess 3 · Last place 1 · 4 rounds" line below the finishing-order list

#### Scenario: Session record line hidden on first round

- **WHEN** the user is in their first round and the broadcast `scoreboard[user_pid]` shows `{"princess_wins": 1, "last_places": 0, "rounds_played": 1}` (just bumped by this round's game-over)
- **THEN** the Session record line IS shown (rounds_played == 1, which is > 0) reading "Session record: Princess 1 · 1 round"

#### Scenario: Session record line hidden when no rounds played

- **WHEN** the broadcast `scoreboard[user_pid]["rounds_played"] == 0` (defensive case, should not happen in practice)
- **THEN** the Session record line is absent from the panel

### Requirement: Game view layout

While `phase == "playing"`, the frontend SHALL render: opponents row, pile area (deck count, top card, rule indicator), a **status stack** of up to three recent actions (newest at the bottom, oldest at the top), collapsible "Special cards & house rules" legend, the user's table (face-up + face-down on a single mini-row), the "Playing from: …" status, the sort-hand toolbar, the user's hand, and the Play/Pick-up action row. The "Your table" SHALL sit between the "Your cards" heading and the "Playing from:" status.

The pile-area **rule indicator** SHALL render dynamically based on `view.config.reverse_rank` (an integer). When the pile top equals the configured reverse rank, the indicator SHALL read `"play UNDER <R> (or another <R>)"` — where `<R>` is the human label for the rank (e.g., `"K"` for rank 13). The "(or another R)" suffix is always present because the reverse rank is always legal as a wild. When the pile is empty the indicator reads `"anything"`; otherwise `"match or beat"`.

The status-stack rendering, glyph rules, and `aria-live` behavior described in the prior version of this requirement are unchanged.

Each opponent's name display AND the user's own name display in the opponents row SHALL append inline session-scoreboard badges sourced from the top-level `scoreboard` field on the broadcast envelope:

- When `scoreboard[pid]["princess_wins"] > 0`, append `· Princess <N>` after the name (where `<N>` is the count).
- When `scoreboard[pid]["last_places"] > 0`, append `· Last <N>` after the name (or after the Princess badge when both are present).
- When both counters are `0`, render no badges (the name stays clean).

Badges SHALL use the same accent color family as the wild `★` glyph so the visual treatment is consistent with the rest of the UI. Badges SHALL be inline with the name (not on a new line) so the chip's vertical rhythm doesn't shift.

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

#### Scenario: Opponent name shows Princess badge when wins exist

- **WHEN** an opponent's scoreboard entry has `princess_wins == 2` and `last_places == 0`
- **THEN** the opponent's row in `#opponents` renders the name followed by `· Princess 2` inline, in the wild-accent color, and shows no `Last` badge

#### Scenario: Opponent name shows both badges when both counters > 0

- **WHEN** an opponent's scoreboard entry has `princess_wins == 1` and `last_places == 1`
- **THEN** the opponent's row renders `<name> · Princess 1 · Last 1` inline

#### Scenario: Opponent with zero counters shows no badge

- **WHEN** an opponent's scoreboard entry has `princess_wins == 0` and `last_places == 0`
- **THEN** the opponent's row renders the bare name with no trailing `· Princess` or `· Last` suffix

#### Scenario: User's own row shows the badge

- **WHEN** the calling user has `princess_wins == 3` in the broadcast scoreboard
- **THEN** the user's own name in the opponents row (or wherever the user's name renders in the play view) displays `· Princess 3` inline
