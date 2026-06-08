## Purpose

The `mobile-frontend` capability is Princess's phone-optimized browser UI, served at `/m` (and `/m/{code}` for direct-join links) parallel to the desktop `web-frontend` at `/`. It is a complete client that talks to the same REST endpoints and WebSocket protocol as the desktop UI, but lays the game out for a portrait-oriented touch viewport: a fan-out hand arc, a sticky bottom action bar with WCAG-sized tap targets, a 2×3 setup grid in place of the desktop's fan-out setup, a bottom-sheet quit modal, a `?`-icon rules sheet in place of the desktop legend, and a full-screen end-of-round winner panel. The mobile UI deliberately omits the House rules config controls, the bot-removal control, and the `/logs` footer link — those stay desktop-only.

## Requirements

### Requirement: Mobile route at /m

The server SHALL serve `static/mobile.html` at `GET /m`. It SHALL also serve the same file at `GET /m/{code}` so a room link of the form `<host>/m/AB12` opens the mobile UI with the room code prefilled into the join input.

The mobile UI SHALL be a complete client — it uses the same REST endpoints (`/api/rooms`, `/join`, `/bot`, `/start`, `/rematch`, `/abort`, `/leave`, `/end_round`, `/rename`) and the same WebSocket protocol (`/ws/{code}/{pid}` with `play` / `pickup` / `set_face_up` messages) as the desktop UI at `/`.

#### Scenario: Mobile root loads the mobile page

- **WHEN** a browser opens `http://<host>/m`
- **THEN** the response body is `static/mobile.html`

#### Scenario: Mobile shortcut prefills the room code

- **WHEN** a browser opens `http://<host>/m/AB12`
- **THEN** the mobile page loads with the room-code input showing `AB12`

### Requirement: Mobile viewport baseline

The mobile UI SHALL render correctly at a minimum portrait viewport width of **390px** (iPhone 14). Wider portrait phones (393, 414, 430) SHALL inherit the same layout with proportionally more breathing room. The mobile HTML's `<meta name="viewport">` tag SHALL set `width=device-width, initial-scale=1, user-scalable=no` to disable pinch-zoom (which would distort the fan-out arc).

#### Scenario: Layout fits 390px portrait

- **WHEN** the mobile page is rendered at viewport `390 × 844` portrait
- **THEN** no element overflows the viewport horizontally and the action bar at the bottom is fully visible

### Requirement: Game view layout (mobile)

The mobile game view SHALL stack vertically (top to bottom):

1. **Top bar** — room code (tap to copy), `?` rules icon, **Rename** button, **Quit** button, status ticker (single-line newest action).
2. **Opponents strip** — single horizontal row, scrolls if needed; each opponent chip SHALL render, in vertical order: name + (bot) tag, current-turn / finished indicator, a **face-up cards row** showing the cards in `view.players[i].face_up` as small mini cards (about 22 × 32 px), and a counts line reading `hand N · down N`. Face-up cards whose rank equals `2`, `10`, or `view.config.reverse_rank` SHALL render with the wild `★` corner glyph. When an opponent has zero face-up cards remaining, the face-up row SHALL collapse to no extra height.
3. **Pile area** — centered: deck count, discard pile top card (full-size), rule indicator below.
4. **Your table** — face-up and face-down cards in a single mini-row (same as desktop layout, just smaller).
5. **Hand toolbar** — a small row above the hand containing a **Sort** toggle button (label flips between `Sort: rank` and `Sort: off`) and a **count** badge (`X cards`). `aria-pressed` reflects the sort state.
6. **Hand (horizontally scrolling row)** — a flex row with `overflow-x: auto`, `scroll-snap-type: x mandatory`, and each card carrying `scroll-snap-align: start`. At a viewport width of 390px the row SHALL show approximately **three full-size cards** at once; users swipe / scroll horizontally to see the rest. Cards SHALL be rendered as plain (un-rotated, un-translated) buttons.
7. **Edge indicators** — two affordances signal that more cards exist off-screen:
   - A subtle gradient fade on the left and right edges of the hand row (CSS pseudo-elements), shown only when the row is scrollable in that direction.
   - Two tappable chevron buttons (`‹` and `›`) anchored at the row's edges. Tapping a chevron scrolls the row by one card width. Both indicators hide when there's no more content in that direction.
8. **Sticky action bar** — bottom of the viewport, always visible: **Play selected** (green) and **Pick up pile** (red). Tap targets ≥ 44 × 44 px.

The hand SHALL handle multi-rank selection identically to the desktop UI (cards must share rank; selecting a different rank clears the prior selection). When sort is ON (default), the hand SHALL be rendered in rank-ascending order, breaking ties by the card's original server-side index (stable). Selecting a sorted card SHALL play the correct server-side index, not the rendered-position index.

#### Scenario: Opponent face-up cards rendered

- **WHEN** an opponent has `face_up: [{rank: 12, suit: "S"}, {rank: 7, suit: "H"}, {rank: 5, suit: "D"}]`
- **THEN** their opponent chip contains three mini cards displaying `Q♠`, `7♥`, `5♦` in that order

#### Scenario: Wild rank gets the ★ glyph in opponent strip

- **WHEN** an opponent's face-up cards include a 10 and the configured reverse rank is 5
- **THEN** both the 10 and any 5 in their face-up row render with the `★` corner glyph; the other face-up cards do not

#### Scenario: Empty face-up collapses

- **WHEN** an opponent has played all three of their face-up cards (`face_up: []`)
- **THEN** the chip's face-up row renders empty (no extra height) and the counts line sits flush below the name

#### Scenario: Finished opponent dims face-up too

- **WHEN** an opponent is finished (`p.finished === true`)
- **THEN** the entire chip (including the face-up row) renders with the `.finished` opacity dimming

#### Scenario: Three cards visible at default width

- **WHEN** the player has 6 cards in hand and the viewport is 390px wide
- **THEN** approximately three cards fit in the hand row without horizontal scrolling, and the remaining three are reachable by swiping or tapping the right chevron

#### Scenario: Scrolling snaps to whole cards

- **WHEN** the player swipes the hand row by a fraction of a card width
- **THEN** the row settles with the next card aligned to the start (`scroll-snap-align: start` behavior)

#### Scenario: Edge indicators reflect scroll position

- **WHEN** the row is scrolled to the start (left edge)
- **THEN** the left chevron and left gradient fade are hidden; the right chevron and right gradient fade are visible (when there's content to the right)

#### Scenario: Tap chevron advances by one card

- **WHEN** the user taps the right chevron
- **THEN** the row scrolls right by one card width and settles on the next snap point

#### Scenario: Sort toggle reorders the hand

- **WHEN** the user taps the **Sort** button while sort is OFF
- **THEN** the hand re-renders in rank-ascending order, the button text reads `Sort: rank`, and `aria-pressed="true"`

#### Scenario: Sorted play uses original server index

- **WHEN** sort is ON and the user taps the visually-first card (a 4) which corresponds to server index 5
- **THEN** the **Play selected** button posts `{indices: [5]}` — not `[0]`

#### Scenario: Hand count badge shown

- **WHEN** the player has 9 cards in hand
- **THEN** the toolbar shows `9 cards` next to the Sort button

#### Scenario: Selected card pops up

- **WHEN** the player taps a card to select it
- **THEN** the card gets the `.selected` class (4px accent border + bottom-left ✓ glyph + slight upward translate)

#### Scenario: Action bar stays visible

- **WHEN** the player scrolls the hand row or taps any card
- **THEN** the action bar at the bottom of the viewport remains visible and tappable

#### Scenario: Tap targets meet accessibility size

- **WHEN** any control (action button, hand card, sort button, chevron, opponent chip, top-bar button) is rendered
- **THEN** its bounding box is at least 44 × 44 logical pixels

### Requirement: Mobile lobby

The mobile lobby SHALL provide: name input, **Create new room** button, room-code input, **Join room** button. Once in a room, the lobby SHALL list seats with name + host/bot/offline tags + the caller's own Rename inline-input control.

The mobile lobby SHALL NOT include the House rules config controls. The current reverse rank SHALL be displayed as read-only text ("Reverse rank: 5"). The host on mobile SHALL be able to add a bot (single Add bot button) and Start the game; bot removal SHALL NOT be available on mobile (defer to desktop).

When the host taps **Start game** on the mobile lobby, the frontend SHALL inspect the most recent lobby broadcast's `room.seats.length`. If exactly **1** (the host is alone), the frontend SHALL open a bottom-sheet `<dialog id="m-solo-sheet" class="m-sheet">` titled "You're alone in the room." offering three primary actions — **Add 1 bot**, **Add 2 bots**, **Add 3 bots** — plus a **Back to lobby** button. On a primary action, the frontend SHALL sequentially `POST /api/rooms/{code}/bot` `N` times and then `POST /api/rooms/{code}/start`. On any `POST /bot` failure, the frontend SHALL surface the error via the existing lobby error helper and SHALL NOT post `/start`. If `seats.length >= 2`, the frontend SHALL skip the sheet and post `/start` directly.

#### Scenario: Mobile lobby has no House rules controls

- **WHEN** a non-host renders the mobile lobby
- **THEN** no element with id `cfg-reverse-rank` or matching the desktop's House rules panel is present

#### Scenario: Host can Add bot and Start

- **WHEN** the host renders the mobile lobby
- **THEN** an **Add bot** button and a **Start game** button are visible

#### Scenario: Reverse rank shown as read-only

- **WHEN** any user renders the mobile lobby
- **THEN** a small "Reverse rank: <rank>" label is shown

#### Scenario: Solo start opens the bottom sheet

- **WHEN** the host is the only seated player on mobile and taps Start game
- **THEN** the `#m-solo-sheet` `<dialog>` opens as a bottom sheet with three "Add N bot(s)" buttons and a "Back to lobby" button

#### Scenario: Mobile Add 2 bots and start

- **WHEN** the host taps "Add 2 bots" in the mobile solo-start sheet
- **THEN** the frontend POSTs `/api/rooms/<code>/bot` twice in sequence, then POSTs `/api/rooms/<code>/start`, then the sheet closes

#### Scenario: Mobile back-to-lobby leaves the room unchanged

- **WHEN** the host taps "Back to lobby" in the mobile solo-start sheet
- **THEN** the sheet closes; no POSTs are made; the host remains on the lobby in its prior state

#### Scenario: Mobile no prompt when a bot is already seated

- **WHEN** the host has one bot in the room and taps Start game on mobile
- **THEN** the sheet does NOT open and `/api/rooms/<code>/start` is posted directly

### Requirement: Mobile setup phase

When `phase == "setup"`, the mobile UI SHALL render the 6 choose cards as a **2×3 grid** (no fan-out). Tap to toggle selection; selecting a fourth replaces the oldest. The **Lock in selection** button SHALL be the sticky bottom action; it is enabled only when exactly three cards are selected.

The setup phase SHALL reset `state.setupSelected` on transition into setup (same rule as desktop, same trigger), and choose-card buttons SHALL carry `aria-pressed` for screen readers.

#### Scenario: Setup uses a 2×3 grid

- **WHEN** the mobile UI renders the setup phase
- **THEN** the 6 choose cards are laid out as 2 rows of 3 columns, not as a fan-out

### Requirement: Mobile end-of-round panel

When `view.game_over` is true, the mobile UI SHALL hide the game surface (top bar, opponents strip, pile, your table, fan-out hand, action bar) and render a full-screen winner panel with the same content shape as the desktop UI: kicker, winner name, subtitle, winning-action line (from `view.last_actions[-1]` with the same 🔥 / ↑ / 👑 glyphs), finishing order, **Play a rematch** (host), **Back to lobby**, and a "Waiting for host…" note for non-hosts.

The mobile UI SHALL enforce hiding via paired `[hidden] { display: none !important; }` CSS rules so the `hidden` attribute always wins (same lesson as the desktop fix).

#### Scenario: Mobile winner panel takes the full screen

- **WHEN** the game ends on mobile
- **THEN** none of the top bar, opponents strip, pile, table, or action bar is visible; only the winner panel is rendered

#### Scenario: Winning action with glyph

- **WHEN** the mobile winner panel renders for a round ended by Mike flipping his last card
- **THEN** a line `"Mike flipped <card> 👑 Mike"` appears between the winner subtitle and the finishing order list

### Requirement: Mobile quit modal (bottom sheet)

The mobile UI SHALL present the Quit modal as a **bottom sheet** that slides up from the screen bottom, rather than a centered `<dialog>`. The options offered are the same as the desktop UI:

- Non-host mid-round: **Take over with a bot** / **Leave room**.
- Host mid-round: **End the round now** / **Abort the game**.

The sheet SHALL be dismissible by tapping a backdrop or by swiping down (or, at minimum, a sticky Cancel button).

#### Scenario: Quit sheet renders the right options

- **WHEN** a non-host taps Quit on the mobile UI mid-round
- **THEN** the bottom sheet contains exactly two buttons — "Take over with a bot" and "Leave room" — with no host-only options

### Requirement: Mobile no-logs / no-legend surface

The mobile UI SHALL NOT include a `/logs` footer link. The mobile UI SHALL replace the desktop "Special cards & house rules" legend with a small **`?` icon** in the top bar; tapping it opens a sheet listing the three wild ranks and what the configured reverse rank is.

#### Scenario: No /logs link on mobile

- **WHEN** the mobile footer is rendered
- **THEN** no link to `/logs` appears

#### Scenario: Rules sheet opens from the ? icon

- **WHEN** the user taps the `?` icon in the mobile top bar
- **THEN** a sheet opens listing 2 (wild reset), 10 (burn), and the reverse rank as the three wilds
