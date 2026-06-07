## MODIFIED Requirements

### Requirement: End-of-round panel

When `view.game_over` is true the frontend SHALL hide the play surface entirely (opponents, pile area, legend, status stack, setup area, your-area) and render only the `#game-over` panel containing: a "Winner!" kicker, the winner's name in large gold type, a subtitle (a special line if the user is the winner), a **winning-action line** describing the move that ended the round, the full finishing-order list (1st = "Princess", last = "last place"), a "Play a rematch" button (host only), a "Back to lobby" button, and (for non-hosts) a "Waiting for the host…" note.

The frontend SHALL hide the play surface through both the `hidden` attribute on each element AND CSS that enforces the attribute (`<selector>[hidden] { display: none !important; }`) so author display rules cannot silently override the attribute. Any element rendered with `display: flex`, `display: block`, or other explicit display value MUST have a paired `[hidden]` rule that forces `display: none`.

The **winning-action line** SHALL be sourced from `view.last_actions[-1]` (the newest action in the engine's bounded history). It SHALL be rendered with the same glyphs used by the status stack — `🔥` when `burned`, `↑` when `picked_up`, `👑 <player name>` when `finished_pid` is set. If `last_actions` is empty (impossible in normal play but possible defensively), the line SHALL be omitted gracefully.

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
