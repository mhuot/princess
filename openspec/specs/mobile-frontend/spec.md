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
3. **Pile area** — three columns: a **left stats column** containing a **Deck** count (from `view.deck_count`) stacked above a **Discard** count (from `view.pile_size`); the **center pile card** (full-size, displaying the discard's top); and a **right stats column** containing the **Rule** indicator. Each stat SHALL render a small dim label above a larger accent-colored value. The Discard value SHALL always render — including `0` when the discard pile is empty.
4. **Your table** — face-up and face-down cards in a single mini-row (same as desktop layout, just smaller).
5. **Hand toolbar** — a small row above the hand containing a **Sort** toggle button (label flips between `Sort: rank` and `Sort: off`) and a **count** badge (`X cards`). `aria-pressed` reflects the sort state.
6. **Hand (multi-row wrapping)** — a flex row with `flex-wrap: wrap` and `justify-content: flex-start`. Each card is a button rendered with a fixed height of approximately 90 px and a width computed via `calc()` so that **5 cards fit per row at the default viewport width** (390px). Cards flow left-to-right, then wrap to a new row. There is no horizontal scrolling, no scroll-snap, no chevron edge indicators, and no gradient edge fades.
7. **Sticky action bar** — bottom of the viewport, always visible: **Play selected** (green) and **Pick up pile** (red). Tap targets ≥ 44 × 44 px.

Cards-per-row breakpoints SHALL be:

- `min-width: 480px` → 6 cards per row (`calc((100% - 30px) / 6)`).
- `360px ≤ width < 480px` (default) → 5 cards per row (`calc((100% - 24px) / 5)`).
- `width < 360px` → 4 cards per row (`calc((100% - 18px) / 4)`).

In all three modes, the resulting card width SHALL be ≥ 44 px so the tap target meets the accessibility floor.

The `#m-game` container SHALL reserve bottom padding equal to the action-bar height plus the safe-area inset plus a small buffer (`padding-bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 12px)`) so that when the page is scrolled to the bottom, the last hand row clears the action bar.

If the wrapped hand exceeds the available vertical space, the page SHALL scroll vertically; the sticky action bar SHALL remain visible at the bottom of the viewport. The frontend SHALL surface a **floating "↓ N more" indicator chip** when at least one hand card is hidden beneath the action bar's top edge:

- The chip SHALL be positioned `fixed`, anchored just above the action bar (vertically) and centered horizontally.
- The chip's label SHALL include the exact count of cards whose top edge is below the action bar's top edge.
- The chip SHALL be tappable; tapping it SHALL smooth-scroll the page so the last hand card becomes visible above the action bar.
- The chip SHALL be hidden (via the `hidden` attribute with a paired CSS `[hidden] { display: none !important; }` override) whenever every hand card is fully visible above the action bar.
- The implementation SHALL use an `IntersectionObserver` on a sentinel element appended at the end of `#m-hand-row` with a `rootMargin` that treats the action bar's top edge as the bottom of the observed area.

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

#### Scenario: Pile area shows Deck above Discard in the left stats column

- **WHEN** the player views the game with `deck_count: 12` and `pile_size: 4`
- **THEN** the left stats column shows two stacked stats — `Deck 12` on top and `Discard 4` below — both with the same label/value visual treatment

#### Scenario: Discard count renders 0 when pile is empty

- **WHEN** the discard pile has just been burned or is empty (`pile_size: 0`)
- **THEN** the discard stat reads `Discard 0` (not hidden, not blank)

#### Scenario: Discard count updates on broadcast

- **WHEN** the server broadcasts a new state with `pile_size` changed from 5 to 6
- **THEN** the next render of `#m-discard-count` displays `6`

#### Scenario: Five cards fit per row at default width

- **WHEN** the player has 5 cards in hand and the viewport is 390px wide
- **THEN** all 5 cards render in a single row with no wrap

#### Scenario: Hand wraps to two rows

- **WHEN** the player has 8 cards in hand and the viewport is 390px wide
- **THEN** the first 5 cards occupy the first row and the remaining 3 wrap to the second row, left-aligned

#### Scenario: Hand wraps to four cards per row on narrow viewport

- **WHEN** the viewport is 340px wide and the player has 6 cards in hand
- **THEN** 4 cards render on the first row and 2 wrap to the second row

#### Scenario: Hand uses six cards per row on tablet viewport

- **WHEN** the viewport is 600px wide and the player has 7 cards in hand
- **THEN** 6 cards render on the first row and 1 wraps to the second row

#### Scenario: No chevrons or edge fades

- **WHEN** the hand renders at any viewport width
- **THEN** no `#m-hand-prev` / `#m-hand-next` chevron buttons are present in the DOM and no left/right gradient fades are visible

#### Scenario: Very large hand causes page scroll

- **WHEN** the player has 20 cards in hand at viewport 390 × 844
- **THEN** the hand renders as 4 rows of 5 cards; the page scrolls vertically to reveal lower rows; the sticky action bar remains visible

#### Scenario: Scroll hint visible when cards are hidden under the action bar

- **WHEN** the player has 20 cards in hand at viewport 390 × 844 and the page is scrolled to the top
- **THEN** `#m-hand-scroll-hint` is visible and its label includes a number greater than zero (e.g., "↓ 5 more")

#### Scenario: Tap on scroll hint jumps to the end

- **WHEN** the user taps `#m-hand-scroll-hint`
- **THEN** the page smooth-scrolls so the last hand card is visible above the action bar; the chip's visibility is reassessed and hides if all cards are now visible

#### Scenario: Scroll hint hidden when the whole hand fits

- **WHEN** the player has 8 cards in hand at viewport 390 × 844
- **THEN** the entire hand fits above the action bar and `#m-hand-scroll-hint` is hidden (`hidden` attribute set)

#### Scenario: Bottom padding clears the last row of the action bar

- **WHEN** the player scrolls to the very bottom of the page with a 20-card hand
- **THEN** the last hand row sits fully above the action bar's top edge with at least 12 px of vertical breathing room

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

- **WHEN** the player scrolls the page or taps any card
- **THEN** the action bar at the bottom of the viewport remains visible and tappable

#### Scenario: Tap targets meet accessibility size

- **WHEN** any control (action button, hand card, sort button, opponent chip, top-bar button, scroll-hint chip) is rendered
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

### Requirement: Share room link (mobile)

The mobile UI SHALL include a **Share** affordance — typically a small icon button labelled `↗` with `aria-label="Share room link"` — in two places:

1. In the **mobile lobby**, positioned next to the room-code line.
2. In the **game-view top bar**, positioned alongside the existing room-code chip / Rename / Quit buttons.

Tapping either Share affordance SHALL build a deep-link URL of the form `<location.origin>/m/<state.code>` and attempt the following chain:

1. If `navigator.share` is available, call `navigator.share({ title: "Princess Card Game", text: "Join my Princess room <code>:", url: <link> })`. On success, no further confirmation is needed. On `AbortError` (user dismissal), return silently. On other errors, fall through to step 2.
2. Call `navigator.clipboard.writeText(<link>)`. On success, the **clicked button's own text glyph** SHALL temporarily change from `↗` to `✓` for approximately 1500 ms then revert. (No separate toast element is used; the previous attempt to flash a message inside `#m-lobby-error` was unreachable because `#m-lobby-error` lives inside `#m-landing` which is hidden once a room is created.)
3. On any failure of both steps, the operation SHALL be a silent no-op.

The existing tap-to-copy on the game-view room-code chip — which copies *just the code* (`state.code`) — remains in place for voice-dictation flows. The new Share button is additive.

#### Scenario: Mobile share invokes navigator.share

- **WHEN** the user taps the lobby Share button on a mobile browser with `navigator.share`
- **THEN** `navigator.share` is invoked with URL `<origin>/m/<state.code>` and no clipboard write occurs unless the share fails

#### Scenario: Mobile share falls back to clipboard with button-glyph flash

- **WHEN** the user taps a Share button on a browser without `navigator.share`
- **THEN** the URL `<origin>/m/<state.code>` is written to the clipboard, and the clicked button's text content changes from `↗` to `✓` for about 1500 ms before reverting

#### Scenario: Mobile share in game view top bar works

- **WHEN** the user taps the game-view top bar Share button while in a live round
- **THEN** the same share/clipboard chain runs against the URL `<origin>/m/<state.code>`; on the clipboard-fallback path, the game-view Share button (not the lobby one) flashes the `✓` glyph

#### Scenario: Code-only tap-to-copy still works

- **WHEN** the user taps the room-code *chip* (not the Share button) in the game-view top bar
- **THEN** only the bare code (e.g., `"AB12"`) is copied to the clipboard, not a URL

#### Scenario: Share button respects accessibility size

- **WHEN** the lobby or game-view Share button is rendered
- **THEN** its bounding box is at least 44 × 44 logical pixels
