## Purpose

The `web-frontend` capability is Princess's browser UI: a single-page app served from the room server that renders the landing form, the lobby (with the house-rules config panel), the setup-phase pick-3-of-6 surface, the in-game view (opponents, pile, legend, your-table, hand), the end-of-round winner banner with rematch flow, quit-to-lobby controls, the live-tail logs page, and WCAG-AAA-compliant accessibility (contrast, focus rings, ARIA roles, `prefers-reduced-motion`).

## Requirements

### Requirement: Single-page app served from server

The server SHALL serve `index.html` for both `/` and `/room/{code}`. Static assets (`app.js`, `styles.css`) SHALL be served from `/static/`. The frontend SHALL detect a `/room/{code}` URL on load and pre-populate the room-code input.

#### Scenario: Direct link to room pre-fills code

- **WHEN** a user navigates to `/room/AB12`
- **THEN** the page loads `index.html` and the room-code input shows `AB12`

### Requirement: Create or join from the landing form

The landing page SHALL provide a name input, a "Create new room" button, and a separate "Join room" path with a room-code input. The name field SHALL be required for both paths. Errors SHALL surface inline via `#lobby-error` rather than alert dialogs.

#### Scenario: Missing name blocks create

- **WHEN** the user clicks "Create new room" with an empty name
- **THEN** the error banner displays "Enter your name first." and no network call is made

### Requirement: Lobby renders seats and host controls

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config controls as `disabled` with a note that only the host can change them.

Each seat row SHALL render zero, one, or two per-row controls:

- A **Remove** button on **bot rows**, visible to the host only. Clicking it posts to `/api/rooms/<code>/remove_bot` with the bot's pid and the host's pid; on success the lobby re-renders and the seat is gone.
- A **Rename** button on the **caller's own seat row** (whether host or non-host). Clicking it replaces the seat's name with an inline `<input type="text" maxlength="20">` pre-filled with the current name. Pressing Enter (or blurring the input with a non-empty value) submits to `/api/rooms/<code>/rename` with the caller's pid; Escape cancels. On success the lobby re-renders.

Non-callers do NOT see the Rename button on someone else's row. Non-hosts do NOT see Remove on bot rows.

The House rules panel SHALL contain the **Reverse rank** `<select>` (as previously specified). Changing it triggers `POST /api/rooms/<code>/config`.

The House rules panel SHALL contain at minimum the **Reverse rank** `<select>` whose options list the legal reverse ranks (3, 4, 5, 6, 7, 8, 9, J, Q, K, A). The displayed text uses the human label (J/Q/K/A) but the submitted value is the integer rank (11/12/13/14). The panel SHALL NOT include a "same rank on reverse" control — the reverse rank is always legal as a wild.

Changing the dropdown SHALL trigger a `POST /api/rooms/<code>/config` containing `{"reverse_rank": <int>}`. Non-hosts see the control disabled with the existing `#config-readonly-note`.

When the host clicks **Start game**, the frontend SHALL inspect `room.seats.length` from the most recent lobby broadcast. If exactly **1** (the host is alone), the frontend SHALL open a centered `<dialog id="solo-start-modal">` modal titled "You're alone in the room." offering three primary actions — **Add 1 bot**, **Add 2 bots**, **Add 3 bots** — plus a **Back to lobby** button. On a primary action, the frontend SHALL sequentially `POST /api/rooms/{code}/bot` `N` times and, on success, `POST /api/rooms/{code}/start`. On any `POST /bot` failure, the frontend SHALL surface the error in the existing lobby-error slot and SHALL NOT POST `/start`. If `room.seats.length >= 2`, the frontend SHALL NOT open the modal and SHALL post `/start` directly as today.

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

#### Scenario: Solo start opens the bot prompt

- **WHEN** the host is the only seated player and clicks Start game
- **THEN** the `#solo-start-modal` `<dialog>` opens with three "Add N bot(s)" buttons and a "Back to lobby" button

#### Scenario: Add 2 bots and start

- **WHEN** the host clicks "Add 2 bots" in the solo-start modal
- **THEN** the frontend POSTs `/api/rooms/<code>/bot` twice in sequence, then POSTs `/api/rooms/<code>/start`, then the modal closes

#### Scenario: Back to lobby leaves the room unchanged

- **WHEN** the host clicks "Back to lobby" in the solo-start modal
- **THEN** the modal closes; no POSTs are made; the host remains on the lobby in its prior state

#### Scenario: No prompt when a bot is already seated

- **WHEN** the host has one bot in the room and clicks Start game
- **THEN** the modal does NOT open and `/api/rooms/<code>/start` is posted as today

#### Scenario: Bot add failure aborts auto-start

- **WHEN** the host clicks "Add 3 bots" and the second `POST /bot` fails (e.g., 409 room full)
- **THEN** the frontend surfaces the error in the lobby-error slot, does NOT post `/start`, and leaves any successfully-added bots in the room

#### Scenario: Host sees Remove on bot rows

- **WHEN** the host renders a lobby containing two bot seats
- **THEN** each bot row carries a Remove button; the host's own row does not carry one

#### Scenario: Non-host does NOT see Remove on bot rows

- **WHEN** a non-host renders the same lobby
- **THEN** no bot row carries a Remove button

#### Scenario: Caller sees Rename on their own row only

- **WHEN** a non-host renders a lobby with the host and two bots
- **THEN** the non-host's own row carries a Rename button; the host's row and the bot rows do not

#### Scenario: Rename input cancels on Escape

- **WHEN** the user clicks Rename, edits the input, then presses Escape
- **THEN** the input collapses back to the original name and no network call is made

### Requirement: Setup phase UI

While `phase == "setup"`, the frontend SHALL hide the game-play surface and render the setup area: three face-down placeholders plus six selectable "choose" cards. The user SHALL be able to toggle exactly three selections. Selecting a fourth replaces the oldest selection. The "Lock in selection" button SHALL be enabled only when exactly three are selected and the user is not already ready.

**No card is ever rendered in a pre-selected state.** On a fresh render of the setup phase — including the initial transition from lobby to setup, a rematch's setup, and any reconnect-driven re-render of setup — every choose card SHALL appear unselected unless the user has explicitly toggled it in this same setup session.

The frontend SHALL reset its in-memory selection set (`state.setupSelected`) whenever the phase transitions into `"setup"` from any other phase (`"lobby"`, `"playing"`, `"game_over"`, or initial page load), provided the player is not already `ready`. The reset SHALL be implemented in `renderGame(view)` by tracking the previous phase and clearing the Set on the transition edge.

Each choose-card `<button>` SHALL carry an `aria-pressed` attribute (`"true"` when in the user's current selection, `"false"` otherwise) so screen readers announce the selection state.

The visual `.selected` style for a choose card SHALL be unambiguously distinct from the gold ★ corner badge that marks wild-rank cards (2, 10, the configured reverse rank). The selected state SHALL render at minimum:

- A thicker accent border than the unselected state.
- A small "✓" or equivalent positively-affirmed glyph in the corner opposite the wild ★ (which lives in the top-right; ✓ lives in the bottom-left).
- An optional upward translate is permitted to reinforce the "lifted" feel; `prefers-reduced-motion` SHALL suppress it.

#### Scenario: Initial render has zero selections

- **WHEN** the host clicks Start, the server broadcasts the first `state` message with `phase: "setup"`, and `renderSetup` runs
- **THEN** no choose card carries the `.selected` class and the "Lock in selection" button is disabled

#### Scenario: Rematch enters setup with a clean Set

- **WHEN** a round ends, the host triggers a rematch, the server broadcasts the new setup state, and `renderGame` routes into the setup branch
- **THEN** `state.setupSelected.size === 0` and no choose card carries `.selected`, regardless of what was selected in the prior round

#### Scenario: Reconnect mid-setup preserves prior in-session selection

- **WHEN** the user is in setup, has selected two cards, and the WebSocket reconnects (state broadcast arrives, `view.phase` is still `"setup"`, `view.you.ready` is false)
- **THEN** the two prior selections survive the re-render (the previous phase was already `"setup"`; no transition edge fires)

#### Scenario: Fourth selection replaces oldest

- **WHEN** three cards are selected and the user clicks a fourth
- **THEN** the first-selected card deselects and the fourth becomes selected, keeping the total at three

#### Scenario: Pending list shows waiting players

- **WHEN** any player has not yet locked in
- **THEN** `#setup-status` reads "Waiting on: <comma-separated names>"

#### Scenario: aria-pressed reflects selection state

- **WHEN** a user toggles a choose card from unselected to selected
- **THEN** the same button's `aria-pressed` attribute flips from `"false"` to `"true"`

#### Scenario: Selected card on a wild rank wears both badges

- **WHEN** a 5 in the choose pile (default reverse rank) is selected
- **THEN** the card displays both the wild ★ glyph (top-right) and the selected ✓ glyph (bottom-left) — they do not overlap and are visually distinct

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

### Requirement: Card display

Cards in any row SHALL show their rank label (e.g., `K`) and suit glyph (♠♥♦♣). Hearts and diamonds SHALL render in red, spades and clubs in black, with WCAG-AAA-compliant foreground colors against the card background. Special-card cards (ranks 2, 7, 10) SHALL show a gold ★ badge.

#### Scenario: 10 of Spades displays a star

- **WHEN** the 10♠ is rendered
- **THEN** its element has CSS class `special` and a ★ badge in the upper-right

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

### Requirement: Legal-play hint

While it is the user's turn and the active source is hand or face-up, every card whose rank is legal under the current pile + config SHALL be visually marked with a green outline (`legal-hint` class).

#### Scenario: A legal 10 is highlighted regardless of pile

- **WHEN** the user's hand contains a 10 and any pile state is non-empty
- **THEN** the 10's element carries the `legal-hint` class

### Requirement: Selection and play

Clicking a card in the active source SHALL toggle its selection. All selected cards MUST share a rank — switching ranks SHALL clear the prior selection. The "Play selected" button SHALL be enabled only when at least one card is selected and it is the user's turn. Clicking it SHALL send `{type: "play", source, indices}` over the WebSocket.

#### Scenario: Switching rank clears prior selection

- **WHEN** an 8 is selected and the user clicks a 9
- **THEN** the 8 is deselected and only the 9 remains selected

### Requirement: Sort hand toggle

The frontend SHALL provide a "Sort hand" button that toggles a sorted display of the hand (rank ascending, then suit). The toggled state SHALL be reflected in `aria-pressed`. Selection state SHALL track underlying server-side indices regardless of display order.

#### Scenario: Sorted order does not change server indices

- **WHEN** sort is on and the user selects the first card in the sorted display
- **THEN** the action sent to the server uses the card's original index in the hand array

### Requirement: Hand-empty hides hand UI

When the user's hand has zero cards, the frontend SHALL hide the "Your cards" heading, the Sort hand toolbar, and the empty hand row. The Play/Pick-up action row SHALL remain visible directly under the table row.

#### Scenario: Pickup restores hand UI

- **WHEN** the user picks up a non-empty pile and their hand becomes non-empty
- **THEN** the hand heading, sort button, and hand row reappear on the next state broadcast

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

### Requirement: Quit & return to lobby

During an in-progress game the frontend SHALL display a red-bordered "Quit & return to lobby" button. Clicking it SHALL open a small modal (`<dialog>` element with focus management) presenting up to three actions instead of a single confirm prompt:

- **Take over with a bot (continue the round)** — visible to non-host players. Closes the modal, POSTs `/leave` with `convert_to_bot: true`, then closes the WebSocket and redirects the user to `/`. Other players see the seat continue as a bot for the rest of the round.
- **End the round now** — visible to the host only. Closes the modal and POSTs `/end_round`. The user remains in the room; the broadcast game-over state triggers the winner panel for everyone.
- **Abandon and return to lobby** — visible to the host (as "Abort the game"). Closes the modal and POSTs `/abort`; the room returns to the lobby phase. For non-hosts this option is labelled "Leave room" and POSTs `/leave` with `convert_to_bot: false`, redirecting the user to `/` and removing their seat entirely.

The modal SHALL be keyboard accessible: `Esc` closes without action, the first action button is auto-focused, and `Tab` cycles through the available actions.

The game-view header SHALL also expose a small **Rename** button. Clicking it SHALL prompt the user (via a browser `prompt()` or an inline input) for a new name; on confirm the frontend SHALL POST `/api/rooms/<code>/rename` with the caller's pid and the new name. The broadcast state update reflects the new name to all opponents.

#### Scenario: Non-host opens the modal

- **WHEN** a non-host clicks Quit during a live game
- **THEN** the modal shows "Take over with a bot (continue the round)" and "Leave room"; "End the round now" is not present

#### Scenario: Host opens the modal

- **WHEN** the host clicks Quit during a live game
- **THEN** the modal shows "End the round now" and "Abort the game" but does NOT show "Take over with a bot"

#### Scenario: Non-host bot takeover

- **WHEN** a non-host picks "Take over with a bot (continue the round)"
- **THEN** the browser POSTs `/api/rooms/<code>/leave` with `convert_to_bot: true`, closes the WebSocket, and navigates to `/`

#### Scenario: Host ends the round

- **WHEN** the host picks "End the round now"
- **THEN** the browser POSTs `/api/rooms/<code>/end_round`; the next broadcast renders the winner panel for everyone, including the host

#### Scenario: Esc cancels with no action

- **WHEN** the modal is open and the user presses Escape
- **THEN** the modal closes and no network call is made

#### Scenario: Mid-round rename succeeds

- **WHEN** a player clicks the game-header Rename button and confirms a new valid name
- **THEN** the browser POSTs `/api/rooms/<code>/rename`; the next broadcast state shows the new name in the opponent rows for the other players

### Requirement: WCAG AAA accessibility

The frontend SHALL maintain a color palette with ≥ 7:1 normal-text contrast. It SHALL provide a skip link, `aria-live` status regions, ARIA roles on card rows, and keyboard-visible focus outlines. Animations SHALL respect `prefers-reduced-motion`.

#### Scenario: Focus outline visible on tab

- **WHEN** a keyboard user tabs to any button or input
- **THEN** the element receives a 3px gold outline (`outline: 3px solid var(--focus)`)

### Requirement: Logs viewer

The frontend SHALL ship a separate `/logs` page that shows a live tail of the in-memory log buffer. It SHALL provide manual refresh, an auto-refresh toggle (2s interval, on by default), an auto-scroll toggle, a Download button linking to `/api/logs/download`, and a Clear button that calls `DELETE /api/logs` after confirmation. Lines SHALL be color-coded by level (ERROR red, WARN gold, INFO lavender, DEBUG grey).

#### Scenario: Tail appends new lines

- **WHEN** the server emits new log lines while the viewer is open with auto-refresh on
- **THEN** within 2 seconds the new lines appear at the bottom of `#log-stream` and (if auto-scroll is on) the view scrolls to them

#### Scenario: Download produces an attachment

- **WHEN** the user clicks Download
- **THEN** the browser receives a `text/plain` response with `Content-Disposition: attachment; filename="princess.log"`

### Requirement: "Now a bot" tag

When a seat in the room has `is_bot == true`, the frontend SHALL render a small "(bot)" or "(now a bot)" tag next to the name. The tag SHALL be present in the opponents row during play and in the lobby seat list before the game starts. For a seat that started as a human and was converted mid-round, the tag SHALL read "(now a bot)" so the change is obvious; for seats that were bots from the start, the tag SHALL read "(bot)".

The frontend SHALL infer "started as human" by tracking the seat's prior `is_bot` flag in client state — if it was `false` on a previous render and is now `true`, the "now a bot" variant applies for the rest of the round.

#### Scenario: Original bot tagged as "(bot)"

- **WHEN** a seat has been a bot from creation
- **THEN** the opponent name renders followed by " (bot)"

#### Scenario: Converted human tagged as "(now a bot)"

- **WHEN** a seat flips from `is_bot: false` to `is_bot: true` mid-round
- **THEN** the opponent name renders followed by " (now a bot)" until the round ends
