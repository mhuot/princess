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
- A **Rename** button on the **caller's own seat row** (whether host or non-host). Clicking it replaces the seat's name with an inline `<input type="text" maxlength="20">` pre-filled with the current name.

Non-callers do NOT see the Rename button on someone else's row. Non-hosts do NOT see Remove on bot rows.

The inline Rename input SHALL behave as follows:

- **Escape** cancels: the input collapses back to the original name and no network call is made.
- **Enter** (or **blur with a changed non-empty value**) submits to `POST /api/rooms/<code>/rename` with the caller's pid and the trimmed value. While the POST is in flight, the input SHALL be `disabled` to prevent double-submit; the input SHALL remain in the DOM (it SHALL NOT be replaced with the static name span until the response resolves).
- **On a 2xx response**, the input SHALL be replaced with the lobby's standard name span. Any error currently shown in `#lobby-error` from a prior failed attempt SHALL be cleared.
- **On any 4xx response** (including **409 Conflict** when the name collides with another seat, and **422 Unprocessable Entity** when validation fails), the input SHALL remain in the DOM, the error SHALL surface in `#lobby-error` using the existing helper (`showError("lobby-error", e.message)`), the input SHALL be re-enabled, re-focused, and its contents SHALL be programmatically selected (`input.focus(); input.select()`) so the user can immediately type a replacement value without clicking Rename again.
- **Blur with an unchanged value** is a no-op cancel: the input collapses without a POST.

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

#### Scenario: Rename input stays open on a 409 collision

- **WHEN** a non-host named "Pat" clicks Rename, types "Mike" (the host's name), and presses Enter
- **THEN** the rename POST returns 409, `#lobby-error` shows the server's `"name 'Mike' is already taken in this room"` message, the inline `<input>` remains in the DOM, is re-enabled, is focused, and its full value "Mike" is selected so the user can type over it without clicking Rename again

#### Scenario: Rename input stays open on a 422 overlength

- **WHEN** the user clicks Rename and submits a name longer than 20 characters (somehow bypassing `maxlength` — e.g., paste-and-Enter on a browser that briefly exceeds the cap before truncation)
- **THEN** the POST returns 422, `#lobby-error` shows the validation message, the input remains in the DOM, is re-enabled, is focused, and its contents are selected

#### Scenario: Successful rename collapses the input and clears prior error

- **WHEN** the user previously saw a 409 (with the input still open) and now types a non-conflicting name and presses Enter
- **THEN** the POST returns 200, the inline input is removed in favor of the standard name span, and any prior `#lobby-error` message is cleared

#### Scenario: Input is disabled while the rename POST is in flight

- **WHEN** the user presses Enter to submit a rename
- **THEN** the `<input>` element's `disabled` attribute is `true` for the duration of the POST; on response (success or failure) the disabled state is removed before any focus/select call

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

### Requirement: Share room link (desktop)

The desktop lobby SHALL include a **Share link** button positioned next to the room code display. Clicking the button SHALL build a deep-link URL of the form `<location.origin>/room/<state.code>` and attempt the following chain:

1. If `navigator.share` is available, call `navigator.share({ title: "Princess Card Game", text: "Join my Princess room <code>:", url: <link> })`. On success, no further visual confirmation is needed (the OS share sheet *is* the confirmation). On `AbortError` (user dismissal), return silently. On other errors, fall through to step 2.
2. Call `navigator.clipboard.writeText(<link>)`. On success, the button's label SHALL flip to **Copied!** for ~1500 ms then revert to **Share link**.
3. On any failure of both steps, the operation SHALL be a silent no-op (no exception, no toast).

The button SHALL be disabled (or no-op guarded) if `state.code` is unset (e.g., the user is on the landing page before creating/joining a room).

#### Scenario: Button copies URL to clipboard

- **WHEN** the host is in a lobby with `state.code = "AB12"` on a browser without `navigator.share` (or in a secure context where share was declined)
- **THEN** clicking **Share link** copies `<origin>/room/AB12` to the clipboard and the button label briefly reads **Copied!**

#### Scenario: navigator.share opens OS sheet when available

- **WHEN** the host is in a lobby on a browser with `navigator.share`
- **THEN** clicking **Share link** invokes `navigator.share` with the URL `<origin>/room/<code>` and no clipboard write occurs unless the share fails

#### Scenario: User dismisses share sheet silently

- **WHEN** `navigator.share` rejects with `AbortError`
- **THEN** the button's label does not flip to **Copied!** and no clipboard write occurs

#### Scenario: Guard against pre-room click

- **WHEN** the user is on the landing page and (somehow) clicks the Share button before joining/creating a room
- **THEN** no network call is made, no clipboard write occurs, and no exception is thrown

### Requirement: "Mobile site" footer link

The desktop UI footer SHALL include a "Mobile site" link in the same area as the existing "View logs" link. Clicking it SHALL:

1. Clear the `princess_prefer_desktop` cookie (so the server is free to redirect future requests to `/m` based on UA).
2. Navigate to `/m`.

#### Scenario: Mobile site link present

- **WHEN** the desktop footer is rendered
- **THEN** an element with `id="switch-to-mobile"` is visible and links to `/m`

#### Scenario: Click clears the desktop-preference cookie

- **WHEN** the user clicks `#switch-to-mobile` on a page where the `princess_prefer_desktop` cookie was set
- **THEN** the cookie is cleared (set to expire in the past) before navigation completes

### Requirement: Auto-join from deep link (desktop)

When the desktop UI loads with `location.pathname` matching `/room/<code>`, the frontend SHALL skip the standard lobby form and attempt to join that room automatically via a three-tier chain:

1. **Session sentinel:** If `sessionStorage.princess_session` exists and its `code` field matches the URL code, the frontend SHALL reopen the WebSocket with the stored `pid`. On success the seated player UI loads directly. **On WebSocket close with `event.code === 4001`** (server signal that the stored pid or room is permanently gone), the frontend SHALL:
   1. Best-effort delete `sessionStorage.princess_session`.
   2. Reset the partially-seated DOM: hide `#room-view` and `#game-view` (toggle `hidden`), show `#lobby`.
   3. Call `autoJoinFromUrl()` again **in the same page** — this re-enters the chain, but because the sentinel is now cleared, it lands at tier 2 (saved name) or tier 3 (focused name view). The frontend SHALL NOT call `location.reload()` in this path.

   On a WebSocket close with `event.code !== 4001` (transient drop, network blip, server crash), the frontend SHALL NOT clear the sentinel and SHALL NOT re-run `autoJoinFromUrl()` — that path is owned by the separate `websocket-reconnect` change (today it is a no-op).
2. **Saved name:** If `localStorage.princess_name` is set, the frontend SHALL `POST /api/rooms/<code>/join` with that name. On success it SHALL stash a fresh `princess_session` in sessionStorage and open the WS. On API error it SHALL fall through to step 3.
3. **Focused name view:** A compact view with one input (`#focused-name`) and one button (`Join room <code>`) SHALL be rendered. The standard lobby form (Create/Join buttons + code input) SHALL be hidden. The button SHALL be `disabled` while `#focused-name`'s trimmed value is empty. On submit, the name SHALL be `trim()`-med before being saved to `localStorage.princess_name` and sent to the join API.

On a successful join or successful sentinel reconnect, the frontend SHALL persist:

- `localStorage.princess_name = <name>`
- `sessionStorage.princess_session = JSON.stringify({code, pid, name})`

On a join API failure (404, 409, etc.) at any tier, the frontend SHALL hide the focused view, show the standard lobby with the code prefilled in `#room-code`, and surface the error in `#lobby-error`.

Storage writes (and deletions) SHALL be best-effort (private browsing, quota errors are swallowed silently).

#### Scenario: Auto-join with saved name

- **WHEN** the user (with `localStorage.princess_name = "Mike"`) opens `https://<host>/room/AB12` for a room that exists
- **THEN** the frontend POSTs `/api/rooms/AB12/join` with `name: "Mike"`, opens the WS, and the page enters the seated-player UI without showing any lobby form

#### Scenario: Auto-join shows focused name view when name unknown

- **WHEN** a new visitor opens `https://<host>/room/AB12` and `localStorage.princess_name` is empty
- **THEN** `#focused-join` is visible, the standard lobby (Create/Join + second code input) is hidden, and the focused button text reads `Join room AB12`

#### Scenario: Focused submit saves name + joins

- **WHEN** the focused view is shown, the user types `Pat` and clicks the Join button
- **THEN** `localStorage.princess_name` is `"Pat"`, the POST fires with `name: "Pat"`, and on success the seated UI loads

#### Scenario: Refresh restores host via sentinel

- **WHEN** the host of room AB12 (with `sessionStorage.princess_session = {code: "AB12", pid: "<host_pid>", name: "Mike"}`) refreshes the page
- **THEN** the frontend reopens the WS with `<host_pid>` and the page restores the host's seated UI without creating a new seat

#### Scenario: Join failure falls back to standard lobby

- **WHEN** auto-join is attempted against a room that doesn't exist (`POST /api/rooms/AB12/join` returns 404)
- **THEN** `#focused-join` is hidden, `#room-code` is prefilled with `AB12`, the standard lobby is visible, and `#lobby-error` shows the 404 detail message

#### Scenario: Non-code paths do not auto-join

- **WHEN** the user opens `https://<host>/` (no code in the path)
- **THEN** the standard lobby is shown and no join API call is made

#### Scenario: Join button is disabled with an empty name

- **WHEN** the focused view is rendered with an empty `#focused-name`
- **THEN** the `#focused-join-btn` is `disabled`; typing a non-whitespace character enables it; clearing the input back to empty (or to only spaces) disables it again

#### Scenario: Name is trimmed before save and submit

- **WHEN** the user types `"  Pat  "` and clicks Join
- **THEN** `localStorage.princess_name` is set to `"Pat"` and the POST body has `name: "Pat"` (no leading/trailing whitespace)

#### Scenario: Stale sentinel triggers in-page retry, not a reload

- **WHEN** the page loads `/room/AB12` with `sessionStorage.princess_session = {code: "AB12", pid: "stale", name: "Mike"}`, a saved `localStorage.princess_name = "Mike"`, and the room AB12 either exists with no seat for `"stale"` (so the server closes with `code=4001, reason="unknown_pid"`) or no longer exists (so the server closes with `code=4001, reason="unknown_room"`)
- **THEN** `sessionStorage.princess_session` is cleared, `#room-view` and `#game-view` are hidden, `#lobby` is visible, no `location.reload()` is invoked, and the saved-name tier fires: `POST /api/rooms/AB12/join` with `name: "Mike"` runs in the same page, succeeding (if the room exists) and seating the user, or falling through to the standard lobby with an error (if the room is gone)

#### Scenario: Stale sentinel with no saved name lands on the focused view

- **WHEN** the page loads `/room/AB12` with a stale sentinel and `localStorage.princess_name` is empty, and the server closes with `code=4001`
- **THEN** the sentinel is cleared, the seated DOM is hidden, the landing is restored, and `#focused-join` becomes visible (tier 3) with the focused button reading `Join room AB12` — all without a page reload

#### Scenario: Non-4001 close does not trigger the in-page retry

- **WHEN** a successfully-seated player's WebSocket closes with `event.code === 1006` (abnormal closure)
- **THEN** the frontend does NOT clear `sessionStorage.princess_session` and does NOT re-enter `autoJoinFromUrl()` — the close is treated as transient and left for separate reconnect logic to handle

### Requirement: Play & burn animations (desktop)

The desktop frontend SHALL fire subtle CSS-keyframe animations in response to flagged entries appearing in `view.last_actions`. Animations are triggered by JS class-toggling against existing DOM elements; all timing and easing live in CSS via `@keyframes`. Every animation SHALL respect `prefers-reduced-motion` through an explicit `@media (prefers-reduced-motion: reduce)` override that suppresses transforms, shakes, and bounces (color flashes and gentle glows MAY remain).

The frontend SHALL maintain a `state.lastSeenActionIndex` (initialized to `-1`) and SHALL evaluate, on every render, whether `(view.last_actions?.length ?? 0) - 1 > state.lastSeenActionIndex`. Only when that condition holds — i.e., a NEW action entry has appeared — SHALL any animation dispatch run. After dispatch, `state.lastSeenActionIndex` SHALL advance to the newest index. The index SHALL reset to `-1` whenever the phase transitions out of `"playing"` (game-over → rematch → setup → playing). Re-renders triggered by an opponent's pre-lock-in selection toggle, a peer rename, or any other no-new-action broadcast SHALL NOT replay any animation.

Each animation SHALL add a one-shot class to its target element and SHALL remove that class on the `animationend` event (registered with `{ once: true }`), with a `setTimeout` fallback at `duration + 50ms` to guarantee cleanup if `animationend` does not fire (e.g., under a reduced-motion override that disables the animation entirely).

The four animations are:

1. **Burn flash** — when `view.last_actions[newest].burned === true`, the frontend SHALL add `.is-burning` to `#pile-card` (the discard's top card). The keyframe SHALL run ~300 ms and combine a brief warm-accent color flash with a single bounce (`translateY` 0 → ~ -8 px → 0). If no `#pile-card` element exists at the moment of dispatch (e.g., a chain-burn cleared the pile and the next state has not yet placed a new card), the dispatch SHALL be a silent no-op for that entry.

2. **Pickup sweep** — when `view.last_actions[newest].picked_up === true`, the frontend SHALL add `.is-pickup` to `.pile-area`. The pile-area keyframe SHALL run ~280 ms and dip opacity briefly while applying a small shake (`translateX` ±2 px). Additionally, if the picked-up player is the user (`view.last_actions[newest].player_pid === state.pid`), the frontend SHALL add `.is-pickup` to `#hand` (the user's hand container). The hand keyframe SHALL lift the row ~2 px and apply an accent border glow that fades within ~280 ms. If the picker is an opponent, the hand animation SHALL NOT run.

3. **Illegal-play shake** — when the WebSocket returns an error in response to a `play` message (the existing `showError("action-error", msg)` path), the frontend SHALL add `.is-illegal` to every card element currently carrying `.selected` inside `#hand` and `#your-table`. The keyframe SHALL run ~200 ms with a red-tinted shake (`translateX` -3 → +3 → -3 → 0). The existing error toast behavior is unchanged.

4. **Winner celebrate** — when `view.game_over === true` and the game-over panel renders, the winner-name `<span>` (`#winner-name`) SHALL receive the class `.is-celebrating`. The keyframe SHALL run ~350 ms with a small grow (`scale` 1.0 → 1.08 → 1.0) plus a soft gold drop-shadow. A `state.celebratedRoundId` (or equivalent gate keyed to the round-ending action index) SHALL ensure the animation fires only once per round; subsequent game-over re-renders within the same round SHALL NOT replay the animation.

Animation durations SHALL live in CSS custom properties on `:root` — `--anim-burn: 300ms`, `--anim-pickup: 280ms`, `--anim-illegal: 200ms`, `--anim-celebrate: 350ms` — and keyframes SHALL reference them via `animation-duration`. WCAG AAA contrast SHALL be preserved at every mid-animation frame; the warm-accent flash color SHALL meet ≥ 7:1 contrast against the pile-card background.

The `@media (prefers-reduced-motion: reduce)` override SHALL:

- Disable the burn bounce; the color flash MAY remain.
- Disable the pickup shake and hand lift; the opacity dip and the static border-glow fade MAY remain.
- Disable the illegal shake; a brief red border on the selected card MAY remain. The toast is unaffected.
- Disable the winner grow; the gold drop-shadow MAY remain as a brief static halo.

#### Scenario: Burn flash fires on a 10-burn

- **WHEN** a state broadcast arrives where `view.last_actions[-1]` has `burned: true` and that index exceeds `state.lastSeenActionIndex`
- **THEN** the `#pile-card` element receives the `.is-burning` class for the duration of the keyframe, then loses it on `animationend`; `state.lastSeenActionIndex` advances to the new index

#### Scenario: Burn flash does not fire on a peer's selection toggle

- **WHEN** a state broadcast arrives where `view.last_actions.length` is unchanged from the previous render (an opponent toggled a setup selection)
- **THEN** no class is added to `#pile-card`; no animation runs

#### Scenario: Pickup sweep on the user's own pickup animates both pile and hand

- **WHEN** the user picks up the pile and the newest action has `picked_up: true` with `player_pid === state.pid`
- **THEN** both `.pile-area` and `#hand` receive `.is-pickup`; the hand animation lifts and glows briefly

#### Scenario: Pickup sweep on an opponent's pickup animates only the pile

- **WHEN** an opponent picks up the pile (`picked_up: true`, `player_pid !== state.pid`)
- **THEN** `.pile-area` receives `.is-pickup`; `#hand` does NOT receive the class

#### Scenario: Illegal-play shake on the selected card

- **WHEN** the user clicks Play with a 6 selected against a pile top of 8 and the server rejects the play
- **THEN** the selected 6's card button receives `.is-illegal` for ~200 ms; the existing error toast appears alongside

#### Scenario: Winner celebrate fires once per round

- **WHEN** the game-over panel first renders for a round and the winner-name span is mounted with `.is-celebrating`
- **THEN** the celebration animation runs; subsequent re-renders of `#game-over` within the same round (e.g., on a state broadcast prior to rematch) do NOT re-add the class

#### Scenario: Reduced-motion user gets the color flash but no bounce

- **WHEN** the user's browser reports `prefers-reduced-motion: reduce` and a burn fires
- **THEN** `#pile-card` flashes the warm-accent color but does NOT bounce; no `translateY` is applied

#### Scenario: Action index resets on round end

- **WHEN** a round ends (`view.game_over` becomes true) and the host triggers a rematch that transitions the phase back into `"setup"` then `"playing"`
- **THEN** `state.lastSeenActionIndex` is `-1` at the moment the first `last_actions` entry of the new round arrives, so the first action's animation fires correctly

#### Scenario: Reconnect mid-round catches up

- **WHEN** the WebSocket reconnects mid-round and the new state broadcast contains a `last_actions` list whose tail index exceeds the local `state.lastSeenActionIndex`
- **THEN** the renderer dispatches the animation for the newest entry (not for every missed entry in between); the index advances to the latest

#### Scenario: prefers-reduced-motion overrides exist for all four animations

- **WHEN** `static/styles.css` is parsed
- **THEN** the `@media (prefers-reduced-motion: reduce)` block contains overrides for each of `.is-burning`, `.is-pickup`, `.is-illegal`, and `.is-celebrating` that disable their transform/shake components
