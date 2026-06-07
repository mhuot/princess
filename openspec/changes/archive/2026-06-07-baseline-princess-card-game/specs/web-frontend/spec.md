## ADDED Requirements

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

In the room view the frontend SHALL render: the room code, the list of seats with host/bot/offline badges, a "House rules" config panel, and (for the host only) Add-bot and Start-game buttons. Non-hosts SHALL see the config checkboxes as `disabled` with a note that only the host can change them.

#### Scenario: Non-host sees disabled toggles

- **WHEN** a non-host renders the lobby
- **THEN** every input inside `#config-panel` is disabled and `#config-readonly-note` is visible

### Requirement: Setup phase UI

While `phase == "setup"`, the frontend SHALL hide the game-play surface and render the setup area: three face-down placeholders plus six selectable "choose" cards. The user SHALL be able to toggle exactly three selections. Selecting a fourth replaces the oldest selection. The "Lock in selection" button SHALL be enabled only when exactly three are selected and the user is not already ready.

#### Scenario: Fourth selection replaces oldest

- **WHEN** three cards are selected and the user clicks a fourth
- **THEN** the first-selected card deselects and the fourth becomes selected, keeping the total at three

#### Scenario: Pending list shows waiting players

- **WHEN** any player has not yet locked in
- **THEN** `#setup-status` reads "Waiting on: <comma-separated names>"

### Requirement: Game view layout

While `phase == "playing"`, the frontend SHALL render: opponents row, pile area (deck count, top card, rule indicator), status line, collapsible "Special cards & house rules" legend, the user's table (face-up + face-down on a single mini-row), the "Playing from: …" status, the sort-hand toolbar, the user's hand, and the Play/Pick-up action row. The "Your table" SHALL sit between the "Your cards" heading and the "Playing from:" status.

#### Scenario: Pile rule indicator reflects the engine rule

- **WHEN** the pile top is a 7 and `config.seven_on_seven` is true
- **THEN** `#rule-indicator` reads "play UNDER 7 (or another 7)"

#### Scenario: Pile rule indicator with 7-on-7 disabled

- **WHEN** the pile top is a 7 and `config.seven_on_seven` is false
- **THEN** `#rule-indicator` reads "must play UNDER 7"

### Requirement: Card display

Cards in any row SHALL show their rank label (e.g., `K`) and suit glyph (♠♥♦♣). Hearts and diamonds SHALL render in red, spades and clubs in black, with WCAG-AAA-compliant foreground colors against the card background. Special-card cards (ranks 2, 7, 10) SHALL show a gold ★ badge.

#### Scenario: 10 of Spades displays a star

- **WHEN** the 10♠ is rendered
- **THEN** its element has CSS class `special` and a ★ badge in the upper-right

### Requirement: Hover tooltip

Every rendered card (full or mini, including the pile top) SHALL carry a `title` attribute that names the card and, for ranks 2, 7, and 10, the card's rule (wild reset, reverse, burn).

#### Scenario: 7 hover explains the reverse rule

- **WHEN** the user hovers a 7 card
- **THEN** the native tooltip reads `"7H\nReverse — next card must be UNDER 7."` (or similar with the appropriate suit)

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

When `view.game_over` is true the frontend SHALL hide the play surface (opponents, pile area, legend, status line, your-area, setup-area) and render only the `#game-over` panel containing: a "Winner!" kicker, the winner's name in large gold type, a subtitle (a special line if the user is the winner), the full finishing-order list (1st = "Princess", last = "last place"), a "Play a rematch" button (host only), a "Back to lobby" button, and (for non-hosts) a "Waiting for the host…" note.

#### Scenario: Host sees rematch button

- **WHEN** the game ends and the user is the host
- **THEN** the `#rematch-btn` is visible and `#rematch-note` is hidden

#### Scenario: Non-host sees waiting note

- **WHEN** the game ends and the user is not the host
- **THEN** `#rematch-btn` is hidden and `#rematch-note` reads "Waiting for the host to start a rematch…"

### Requirement: Quit & return to lobby

During an in-progress game the frontend SHALL display a red-bordered "Quit & return to lobby" button. Clicking it SHALL prompt for confirmation. For the host the action SHALL POST `/abort` and remain in the room (which transitions to the lobby view). For a non-host the action SHALL POST `/leave`, close the WebSocket, and redirect to `/`.

#### Scenario: Host abort confirmed

- **WHEN** the host clicks Quit and confirms
- **THEN** `POST /api/rooms/<code>/abort` fires and the next broadcast renders the lobby for everyone

#### Scenario: Non-host leave confirmed

- **WHEN** a non-host clicks Quit and confirms
- **THEN** `POST /api/rooms/<code>/leave` fires, the WS closes, and the browser navigates to `/`

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
