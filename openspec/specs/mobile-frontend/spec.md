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
2. **Opponents strip** — single horizontal row, scrolls if needed; each opponent chip SHALL render, in vertical order: name + (bot) tag + **session badges** (this change), current-turn / finished indicator, a **face-up cards row** showing the cards in `view.players[i].face_up` as small mini cards (about 22 × 32 px), and a counts line reading `hand N · down N`. Face-up cards whose rank equals `2`, `10`, or `view.config.reverse_rank` SHALL render with the wild `★` corner glyph. When an opponent has zero face-up cards remaining, the face-up row SHALL collapse to no extra height.
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

Each opponent chip's name line — and the calling user's own name wherever it renders in the play view — SHALL append inline session-scoreboard badges sourced from the top-level `scoreboard` field on the broadcast envelope:

- When `scoreboard[pid]["princess_wins"] > 0`, append `· Princess <N>` inline after the name and any `(bot)` tag.
- When `scoreboard[pid]["last_places"] > 0`, append `· Last <N>` after the Princess badge (or directly after the name if no Princess badge is present).
- When both counters are `0`, render no badges (the chip's name line stays clean).

Badges SHALL use the same accent color family as the wild `★` glyph. Badges SHALL render in a smaller font size than the player's name so the chip's existing horizontal density isn't broken; the chip's `min-width` does not need to grow because the badge text is short.

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

#### Scenario: Opponent chip name shows Princess badge when wins exist

- **WHEN** an opponent's scoreboard entry has `princess_wins == 2` and `last_places == 0`
- **THEN** the opponent's chip renders the name followed by `· Princess 2` inline (after any `(bot)` tag) in the wild-accent color, and shows no `Last` badge

#### Scenario: Opponent chip shows both badges when both counters > 0

- **WHEN** an opponent's scoreboard entry has `princess_wins == 1` and `last_places == 1`
- **THEN** the chip renders `<name> · Princess 1 · Last 1` inline

#### Scenario: Opponent chip with zero counters shows no badge

- **WHEN** an opponent's scoreboard entry has `princess_wins == 0` and `last_places == 0`
- **THEN** the chip renders the bare name with no `· Princess` or `· Last` suffix

### Requirement: Mobile lobby

The mobile lobby SHALL provide: name input, **Create new room** button, room-code input, **Join room** button. Once in a room, the lobby SHALL list seats with name + host/bot/offline tags. The caller's own seat SHALL be renameable via a bottom-sheet rename dialog (`#m-rename-sheet`) reachable from a Rename affordance accessible from the lobby and the game-view top bar.

The mobile lobby SHALL NOT include the House rules config controls. The current reverse rank SHALL be displayed as read-only text ("Reverse rank: 5"). The host on mobile SHALL be able to add a bot (single Add bot button) and Start the game; bot removal SHALL NOT be available on mobile (defer to desktop).

When the host taps **Start game** on the mobile lobby, the frontend SHALL inspect the most recent lobby broadcast's `room.seats.length`. If exactly **1** (the host is alone), the frontend SHALL open a bottom-sheet `<dialog id="m-solo-sheet" class="m-sheet">` titled "You're alone in the room." offering three primary actions — **Add 1 bot**, **Add 2 bots**, **Add 3 bots** — plus a **Back to lobby** button. On a primary action, the frontend SHALL sequentially `POST /api/rooms/{code}/bot` `N` times and then `POST /api/rooms/{code}/start`. On any `POST /bot` failure, the frontend SHALL surface the error via the existing lobby error helper and SHALL NOT post `/start`. If `seats.length >= 2`, the frontend SHALL skip the sheet and post `/start` directly.

The rename bottom sheet (`#m-rename-sheet`) SHALL behave as follows:

- Opening the sheet pre-fills `#m-rename-input` with the caller's current name.
- Tapping **Submit** posts to `/api/rooms/<code>/rename` with the caller's pid and the trimmed input value.
- **On a 2xx response**, the sheet SHALL `.close()`.
- **On any 4xx response** (including **409 Conflict** for a name collision and **422 Unprocessable Entity** for validation failure), the sheet SHALL remain open, the error SHALL surface via the existing mobile error helper (`showError(e.message)`), and `#m-rename-input` SHALL be re-focused and its contents programmatically selected so the user can immediately type a replacement value without re-tapping into the field.
- Tapping **Cancel** closes the sheet with no network call regardless of the input's contents.

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

#### Scenario: Rename sheet stays open on a 409 collision

- **WHEN** a player named "Pat" opens the rename sheet, types "Mike" (the host's name), and taps Submit
- **THEN** the POST returns 409, the mobile error helper surfaces `"name 'Mike' is already taken in this room"`, `#m-rename-sheet` remains open (`.close()` is NOT called), `#m-rename-input` is focused, and its value "Mike" is selected so the user can immediately type over it

#### Scenario: Rename sheet closes on successful rename

- **WHEN** a player opens the rename sheet, types a non-conflicting name, and taps Submit
- **THEN** the POST returns 200 and `#m-rename-sheet.close()` is called

#### Scenario: Rename sheet Cancel makes no network call

- **WHEN** the player opens the rename sheet, edits the input, and taps Cancel
- **THEN** the sheet closes and no `/rename` POST is sent

### Requirement: Mobile setup phase

When `phase == "setup"`, the mobile UI SHALL render the 6 choose cards as a **2×3 grid** (no fan-out). Tap to toggle selection; selecting a fourth replaces the oldest. The **Lock in selection** button SHALL be the sticky bottom action; it is enabled only when exactly three cards are selected.

The setup phase SHALL reset `state.setupSelected` on transition into setup (same rule as desktop, same trigger), and choose-card buttons SHALL carry `aria-pressed` for screen readers.

#### Scenario: Setup uses a 2×3 grid

- **WHEN** the mobile UI renders the setup phase
- **THEN** the 6 choose cards are laid out as 2 rows of 3 columns, not as a fan-out

### Requirement: Mobile end-of-round panel

When `view.game_over` is true, the mobile UI SHALL hide the game surface (top bar, opponents strip, pile, your table, fan-out hand, action bar) and render a full-screen winner panel with the same content shape as the desktop UI: kicker, winner name, subtitle, winning-action line (from `view.last_actions[-1]` with the same 🔥 / ↑ / 👑 glyphs), finishing order, **Session record line** (this change), **Play a rematch** (host), **Back to lobby**, and a "Waiting for host…" note for non-hosts.

The mobile UI SHALL enforce hiding via paired `[hidden] { display: none !important; }` CSS rules so the `hidden` attribute always wins (same lesson as the desktop fix).

The **Session record line** SHALL be sourced from the top-level `scoreboard` field on the WebSocket `state` envelope (the same field the room-server attaches alongside `view`). It SHALL display the calling user's entry only, in the form `Session record: Princess <P> · Last place <L> · <R> rounds`, where `<P>` is `princess_wins`, `<L>` is `last_places`, and `<R>` is `rounds_played`. When `last_places == 0` the `· Last place 0` segment MAY be elided. When `rounds_played == 0` the line SHALL be hidden entirely. The line SHALL render at a smaller font size than the finishing-order list to fit the narrow mobile column, but in the same accent color treatment used elsewhere in the panel so the eye groups it as session-context information.

#### Scenario: Mobile winner panel takes the full screen

- **WHEN** the game ends on mobile
- **THEN** none of the top bar, opponents strip, pile, table, or action bar is visible; only the winner panel is rendered

#### Scenario: Winning action with glyph

- **WHEN** the mobile winner panel renders for a round ended by Mike flipping his last card
- **THEN** a line `"Mike flipped <card> 👑 Mike"` appears between the winner subtitle and the finishing order list

#### Scenario: Mobile session record line rendered after rematches

- **WHEN** the calling user has played 4 rounds in this room and the broadcast `scoreboard[user_pid]` is `{"princess_wins": 3, "last_places": 1, "rounds_played": 4}`
- **THEN** the mobile winner panel contains a "Session record: Princess 3 · Last place 1 · 4 rounds" line below the finishing-order list, in a smaller font size than the finishing-order list

#### Scenario: Mobile session record line hidden when no rounds played

- **WHEN** the broadcast `scoreboard[user_pid]["rounds_played"] == 0` (defensive case)
- **THEN** the Session record line is absent from the mobile winner panel

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

### Requirement: "View desktop site" link

The mobile UI lobby footer area SHALL include a "View desktop site" link/button (`id="m-switch-to-desktop"`). Tapping it SHALL:

1. Set the cookie `princess_prefer_desktop=1; Path=/` so future requests to `/` are not redirected back to `/m`.
2. Navigate to `/`.

The link SHALL be styled as a small, low-emphasis text link (not a primary action) to avoid competing with the create/join controls.

#### Scenario: Desktop-switch link present

- **WHEN** the mobile lobby is rendered
- **THEN** an element with `id="m-switch-to-desktop"` is visible

#### Scenario: Tap sets the cookie and navigates

- **WHEN** the user taps `#m-switch-to-desktop`
- **THEN** the cookie `princess_prefer_desktop=1` is set on the document and the browser navigates to `/`

#### Scenario: Round trip stays consistent

- **WHEN** the user tapped "View desktop site" on `/m` and then taps "Mobile site" on `/`
- **THEN** the cookie is cleared, the browser navigates to `/m`, and refreshing `/` will redirect to `/m` based on UA

### Requirement: Auto-join from deep link (mobile)

When the mobile UI loads with `location.pathname` matching `/m/<code>`, the frontend SHALL apply the same three-tier auto-join chain as the desktop UI:

1. **Session sentinel:** `sessionStorage.princess_session` with matching `code` → reopen WS with stored `pid`. **On WebSocket close with `event.code === 4001`** (server signal that the stored pid or room is permanently gone), the frontend SHALL:
   1. Best-effort delete `sessionStorage.princess_session`.
   2. Reset the partially-seated DOM: hide `#m-room` and `#m-game` (toggle `hidden`), show `#m-landing`.
   3. Call `autoJoinFromUrl()` again **in the same page** — re-entering the chain, which now lands at tier 2 (saved name) or tier 3 (focused name view). The frontend SHALL NOT call `location.reload()` in this path.

   On a WebSocket close with `event.code !== 4001` (transient drop), the frontend SHALL NOT clear the sentinel and SHALL NOT re-run `autoJoinFromUrl()` — that path is owned by the separate `websocket-reconnect` change.
2. **Saved name:** `localStorage.princess_name` set → `POST /api/rooms/<code>/join` with that name.
3. **Focused name view:** a compact `<section id="m-focused-join">` showing a name input and a `Join room <code>` button. The standard `#m-landing` create/join controls SHALL be hidden while the focused view is active. The `#m-focused-join-btn` button SHALL be `disabled` while the trimmed value of `#m-focused-name` is empty. On submit, the name SHALL be `trim()`-med before save and send.

On a successful join or sentinel reconnect, the frontend SHALL persist:

- `localStorage.princess_name`
- `sessionStorage.princess_session` (`{code, pid, name}`)

On API failure at any tier, the frontend SHALL hide the focused view, show the standard `#m-landing` view with the code prefilled in `#m-code`, and surface the error via the existing mobile error helper.

The focused view SHALL look at home on a mobile viewport — full-width input and button, no extra chrome — and SHALL respect the 44 × 44 px tap target floor.

Storage writes (and deletions) SHALL be best-effort (private browsing, quota errors are swallowed silently).

#### Scenario: Mobile auto-join with saved name

- **WHEN** the user (with saved name) opens `https://<host>/m/AB12`
- **THEN** the join fires automatically and the seated mobile UI loads with no tap required

#### Scenario: Mobile focused view shown for new visitor

- **WHEN** a new visitor opens `https://<host>/m/AB12`
- **THEN** `#m-focused-join` is visible, the standard landing controls (`#m-create-btn`, `#m-join-btn`, etc.) are hidden, and the focused button reads `Join room AB12`

#### Scenario: Mobile focused submit saves name + joins

- **WHEN** the user types `Pat` in the focused view and taps Join
- **THEN** `localStorage.princess_name` becomes `"Pat"` and the room loads

#### Scenario: Mobile refresh restores via sentinel

- **WHEN** a seated mobile player refreshes their `/m/AB12` page
- **THEN** the frontend reuses the stored `pid` and restores the seat without creating a new join

#### Scenario: Mobile failure falls back to landing

- **WHEN** auto-join receives a 404 for an unknown room
- **THEN** `#m-focused-join` hides, `#m-landing` shows with `#m-code` prefilled and the error visible

#### Scenario: Mobile non-code path does not auto-join

- **WHEN** the user opens `https://<host>/m`
- **THEN** the standard landing controls show, no auto-join API call is made

#### Scenario: Mobile Join button is disabled with an empty name

- **WHEN** the mobile focused view is rendered with an empty `#m-focused-name`
- **THEN** `#m-focused-join-btn` is `disabled`; typing a non-whitespace character enables it; clearing the input back to empty (or to only spaces) disables it again

#### Scenario: Mobile name is trimmed before save and submit

- **WHEN** the user types `"  Pat  "` on the mobile focused view and taps Join
- **THEN** `localStorage.princess_name` is set to `"Pat"` and the POST body has `name: "Pat"`

#### Scenario: Mobile stale sentinel triggers in-page retry, not a reload

- **WHEN** the page loads `/m/AB12` with `sessionStorage.princess_session = {code: "AB12", pid: "stale", name: "Mike"}`, a saved `localStorage.princess_name = "Mike"`, and the server closes the WS with `code=4001` (either `reason="unknown_pid"` or `reason="unknown_room"`)
- **THEN** `sessionStorage.princess_session` is cleared, `#m-room` and `#m-game` are hidden, `#m-landing` is visible, no `location.reload()` is invoked, and the saved-name tier fires in the same page (succeeding if the room exists, or falling through to the standard `#m-landing` with the error visible if not)

#### Scenario: Mobile stale sentinel with no saved name lands on the focused view

- **WHEN** the page loads `/m/AB12` with a stale sentinel and `localStorage.princess_name` is empty, and the server closes with `code=4001`
- **THEN** the sentinel is cleared, the seated DOM is hidden, the mobile landing is restored, and `#m-focused-join` becomes visible (tier 3) — all without a page reload

#### Scenario: Mobile non-4001 close does not trigger the in-page retry

- **WHEN** a successfully-seated mobile player's WebSocket closes with `event.code === 1006`
- **THEN** the frontend does NOT clear `sessionStorage.princess_session` and does NOT re-enter `autoJoinFromUrl()` — the close is treated as transient

### Requirement: Play & burn animations (mobile)

The mobile frontend SHALL fire the same four CSS-keyframe animations as the desktop UI in response to flagged entries appearing in `view.last_actions`, scoped to the mobile DOM (`#m-pile-card`, `.m-pile-area`, `#m-hand-row`, `#m-winner-name`). Animations are triggered by JS class-toggling against existing mobile elements; all timing and easing live in CSS via `@keyframes`. Every animation SHALL respect `prefers-reduced-motion` through an explicit `@media (prefers-reduced-motion: reduce)` override that suppresses transforms, shakes, and bounces (color flashes and gentle glows MAY remain).

The mobile frontend SHALL maintain a `state.lastSeenActionIndex` (initialized to `-1`) and SHALL evaluate, on every render, whether `(view.last_actions?.length ?? 0) - 1 > state.lastSeenActionIndex`. Only when that condition holds SHALL any animation dispatch run. After dispatch, `state.lastSeenActionIndex` SHALL advance to the newest index. The index SHALL reset to `-1` whenever the phase transitions out of `"playing"`. Re-renders triggered by no-new-action broadcasts (an opponent's pre-lock-in selection toggle, a peer rename, a deck-count change without a play) SHALL NOT replay any animation.

Each animation SHALL add a one-shot class to its target element and SHALL remove that class on the `animationend` event (registered with `{ once: true }`), with a `setTimeout` fallback at `duration + 50ms` for cleanup safety.

The four animations are:

1. **Burn flash** — when `view.last_actions[newest].burned === true`, the frontend SHALL add `.is-burning` to `#m-pile-card`. The keyframe SHALL run ~300 ms and combine a brief warm-accent color flash with a single bounce (`translateY` 0 → ~ -8 px → 0). If no `#m-pile-card` exists at dispatch time, the dispatch SHALL be a silent no-op.

2. **Pickup sweep** — when `view.last_actions[newest].picked_up === true`, the frontend SHALL add `.is-pickup` to the mobile pile container `.m-pile-area`. The pile keyframe SHALL run ~280 ms with an opacity dip and a small shake (`translateX` ±2 px). Additionally, if the picked-up player is the user (`view.last_actions[newest].player_pid === state.pid`), the frontend SHALL add `.is-pickup` to `#m-hand-row`. The hand-row keyframe SHALL lift the row ~2 px and apply an accent border glow that fades within ~280 ms. The lift SHALL NOT cause any hand card to overlap the sticky action bar.

3. **Illegal-play shake** — when the WebSocket returns an error in response to a mobile `play` message (the existing mobile error toast path), the frontend SHALL add `.is-illegal` to every card element currently carrying `.selected` in `#m-hand-row`. The keyframe SHALL run ~200 ms with a red-tinted shake (`translateX` -3 → +3 → -3 → 0). The existing error toast behavior is unchanged.

4. **Winner celebrate** — when `view.game_over === true` and the mobile end-of-round panel renders, the winner-name `<span>` (`#m-winner-name`) SHALL receive `.is-celebrating`. The keyframe SHALL run ~350 ms with a small grow (`scale` 1.0 → 1.08 → 1.0) plus a soft gold drop-shadow. A `state.celebratedRoundId` (or equivalent gate keyed to the round-ending action index) SHALL ensure the animation fires only once per round.

Animation durations SHALL live in CSS custom properties on `:root` in `static/mobile.css` — `--anim-burn: 300ms`, `--anim-pickup: 280ms`, `--anim-illegal: 200ms`, `--anim-celebrate: 350ms`. WCAG AAA contrast SHALL be preserved at every mid-animation frame; the warm-accent flash color SHALL meet ≥ 7:1 contrast against the mobile pile-card background.

The `@media (prefers-reduced-motion: reduce)` override in `static/mobile.css` SHALL:

- Disable the burn bounce; the color flash MAY remain.
- Disable the pickup shake and hand-row lift; the opacity dip and the static border-glow fade MAY remain.
- Disable the illegal shake; a brief red border on the selected card MAY remain. The toast is unaffected.
- Disable the winner grow; the gold drop-shadow MAY remain as a brief static halo.

Animations SHALL NOT interfere with the mobile sticky action bar's tap targets — at no mid-animation frame SHALL `#m-action-bar` controls become obscured, mis-aligned, or smaller than the existing 44 × 44 px tap floor.

#### Scenario: Burn flash fires on mobile 10-burn

- **WHEN** a state broadcast arrives on the mobile UI where `view.last_actions[-1]` has `burned: true` and the index exceeds `state.lastSeenActionIndex`
- **THEN** `#m-pile-card` receives `.is-burning` for the keyframe duration, then loses it on `animationend`; `state.lastSeenActionIndex` advances

#### Scenario: Mobile burn flash does not fire on no-new-action broadcasts

- **WHEN** a state broadcast arrives where `view.last_actions.length` is unchanged
- **THEN** no class is added to `#m-pile-card`; no animation runs

#### Scenario: Mobile pickup sweep on the user's own pickup

- **WHEN** the user taps Pick up pile and the newest action has `picked_up: true` with `player_pid === state.pid`
- **THEN** both `.m-pile-area` and `#m-hand-row` receive `.is-pickup`; the hand-row animation does not push any card under the sticky action bar

#### Scenario: Mobile pickup sweep on opponent pickup

- **WHEN** an opponent picks up and the newest action's `player_pid !== state.pid`
- **THEN** `.m-pile-area` receives `.is-pickup`; `#m-hand-row` does NOT receive the class

#### Scenario: Mobile illegal-play shake on the selected card

- **WHEN** the user taps Play selected with a 6 selected against a pile top of 8 and the server rejects
- **THEN** the selected 6's card button in `#m-hand-row` receives `.is-illegal` for ~200 ms; the mobile error toast appears alongside

#### Scenario: Mobile winner celebrate fires once per round

- **WHEN** the mobile end-of-round panel first renders for a round and `#m-winner-name` receives `.is-celebrating`
- **THEN** the celebration animation runs; subsequent re-renders of the mobile game-over panel within the same round do NOT re-add the class

#### Scenario: Mobile reduced-motion user gets color flash but no bounce

- **WHEN** the user's mobile browser reports `prefers-reduced-motion: reduce` and a burn fires
- **THEN** `#m-pile-card` flashes the warm-accent color but does NOT bounce; no `translateY` is applied

#### Scenario: Mobile action index resets on round end

- **WHEN** a mobile round ends and the host triggers a rematch that transitions back into `"playing"`
- **THEN** `state.lastSeenActionIndex` is `-1` when the first new-round action arrives, so its animation fires correctly

#### Scenario: Mobile reconnect mid-round catches up

- **WHEN** the WebSocket reconnects mid-round and the new state's `last_actions` tail index exceeds the local `state.lastSeenActionIndex`
- **THEN** the renderer dispatches only the newest entry's animation, advances the index, and skips the intermediate entries

#### Scenario: Mobile prefers-reduced-motion overrides exist for all four animations

- **WHEN** `static/mobile.css` is parsed
- **THEN** the `@media (prefers-reduced-motion: reduce)` block contains overrides for each of `.is-burning`, `.is-pickup`, `.is-illegal`, and `.is-celebrating` that disable their transform/shake components

#### Scenario: Action bar tap targets remain accessible during animations

- **WHEN** any of the four animations is running at the moment the user taps `Play selected` or `Pick up pile`
- **THEN** the action-bar buttons remain at ≥ 44 × 44 px and the tap is delivered to the underlying control (animations target the pile, hand row, or winner panel — not the action bar itself)

### Requirement: WebSocket auto-reconnect (mobile)

When a WebSocket on the mobile UI that has already received at least one inbound message closes mid-session (the `state._wsGotMessage === true` branch of the close handler), the mobile frontend SHALL automatically attempt to reopen the connection using the SAME `pid` against the same `/ws/<code>/<pid>` URL, applying the same exponential-backoff schedule as the desktop UI.

**Backoff schedule.** The Nth attempt (N starting at 1) SHALL wait `min(2^(N-1), 16)` seconds before opening a new WebSocket — i.e., 1s, 2s, 4s, 8s, 16s, 16s, 16s, … . The attempt counter SHALL reset to 0 on every successful reconnect.

**Give-up threshold.** If either `attempt > 10` OR `Date.now() - firstCloseTs > 90_000`, the mobile frontend SHALL stop scheduling retries and enter the terminal `lost` state.

**Connection banner.** A single fixed-position element `<div id="m-conn-banner" role="status" aria-live="polite" hidden>` SHALL surface the connection state at the top of the viewport, respecting the top safe-area inset (`env(safe-area-inset-top)`):

- `live` state: `hidden`, text empty.
- `reconnecting` state: visible, text reads `Reconnecting…`. The mobile Play (`#m-play-btn`) and Pick-up (`#m-pickup-btn`) buttons SHALL be `disabled` while in this state.
- `reconnected` state: visible for approximately 1500 ms, text reads `Reconnected`. After the timeout the banner SHALL return to `live` and hide. Play and Pick-up are re-enabled (subject to normal turn rules) on entry to this state.
- `lost` state (terminal): visible, text reads `Disconnected — refresh to reconnect.`. Play and Pick-up remain `disabled`.

The banner SHALL meet WCAG AAA contrast (≥ 7:1 normal-text contrast) and SHALL respect `prefers-reduced-motion` for any optional fade animation. Because the banner is not interactive, it MAY render at less than 44 × 44 px.

**Tier-1 sentinel path unchanged.** When the close fires before any inbound message arrived (`state._wsGotMessage === false`), the existing `deep-link-auto-join` behavior SHALL apply (clear `sessionStorage.princess_session` and `location.reload()`). Auto-reconnect SHALL NOT engage on that path.

**Re-sync on reconnect.** After a successful reopen the mobile frontend SHALL render whatever the server's first inbound broadcast (`lobby` or `state`) describes. No client-side merging or stitching of pre/post-disconnect state SHALL be attempted.

**Timer hygiene.** The pending reconnect timer SHALL be cancellable; on a successful reopen or on entry to the terminal `lost` state, any outstanding timer SHALL be cleared.

**Sticky action bar interaction.** The mobile sticky action bar's Play and Pick-up buttons SHALL show their `disabled` visual treatment during reconnect (lower opacity, no tap feedback), matching the existing disabled state used when it is not the user's turn.

#### Scenario: Mobile banner appears on mid-session drop

- **WHEN** a mobile session has received at least one `state` broadcast and the WebSocket then closes (e.g., a signal blip on cellular)
- **THEN** within ≤ 1 second `#m-conn-banner` becomes visible with text `Reconnecting…`, and both `#m-play-btn` and `#m-pickup-btn` are `disabled`

#### Scenario: Mobile single-attempt recovery

- **WHEN** the first reconnect attempt succeeds and the server's first follow-up broadcast arrives
- **THEN** `#m-conn-banner` text reads `Reconnected`, the banner auto-hides ~1500 ms later, the action buttons re-enable (turn-rules permitting), and the internal attempt counter is back at 0

#### Scenario: Mobile backoff caps at 16 seconds

- **WHEN** the 6th, 7th, and 8th attempts are all needed
- **THEN** the delay before each is approximately 16 seconds (not 32, not 64)

#### Scenario: Mobile terminal state after 10 attempts

- **WHEN** 10 consecutive reconnect attempts have failed
- **THEN** `#m-conn-banner` text reads `Disconnected — refresh to reconnect.`, the banner stays visible, `#m-play-btn` and `#m-pickup-btn` remain `disabled`, and no further `setTimeout` for reconnect is scheduled

#### Scenario: Mobile terminal state after 90s wall clock

- **WHEN** the tab was backgrounded mid-disconnect and resumes after 95 seconds with the WebSocket still closed
- **THEN** on the next retry tick the mobile frontend recognizes that `Date.now() - firstCloseTs > 90_000`, enters the terminal `lost` state, and surfaces the "Disconnected — refresh to reconnect." banner without firing further attempts

#### Scenario: Mobile tier-1 sentinel reload is unaffected

- **WHEN** the user opens `/m/AB12` with a stale `sessionStorage.princess_session.pid` and the server closes the WebSocket immediately without sending any message
- **THEN** the existing tier-1 path fires (sentinel cleared, `location.reload()` invoked) and the new auto-reconnect logic does NOT run

#### Scenario: Mobile reconnect uses the same pid

- **WHEN** any auto-reconnect attempt is made on mobile
- **THEN** the new WebSocket URL equals the dropped URL — `/ws/<code>/<pid>` with the same `<pid>` — no new `POST /api/rooms/<code>/join` call is made

#### Scenario: Mobile banner respects top safe-area inset

- **WHEN** the mobile UI is rendered on a device with a top safe-area inset (e.g., iPhone with notch)
- **THEN** `#m-conn-banner` is positioned with `top: env(safe-area-inset-top)` so it does not overlap with the status bar

#### Scenario: Mobile action buttons re-enable on resync, not on raw open

- **WHEN** the new WebSocket opens but the server has not yet sent a broadcast
- **THEN** `#m-play-btn` and `#m-pickup-btn` remain `disabled`; they re-enable only after the first inbound message arrives (the server's resync of `lobby` or `state`)

#### Scenario: Mobile banner has accessible roles

- **WHEN** `#m-conn-banner` enters the `reconnecting` or `lost` state
- **THEN** the element carries `role="status"` and `aria-live="polite"` so screen readers announce the state change without interrupting the user

### Requirement: Mobile lobby links to Hall of Princesses

The mobile lobby (`/m`) SHALL include a "Hall of Princesses" link in the same switch row that holds the "View desktop site" affordance, pointing to `/leaderboard`. The link SHALL meet the 44 px × 44 px tap-target floor used by the rest of the mobile UI and render at WCAG AAA contrast.

#### Scenario: Link present in mobile lobby

- **WHEN** a user opens `/m` and views the lobby switch row
- **THEN** an anchor labeled "Hall of Princesses" pointing to `/leaderboard` is rendered

#### Scenario: Tap target meets minimum size

- **WHEN** the link is measured
- **THEN** its hit box is at least 44 px × 44 px

#### Scenario: Navigation works

- **WHEN** the user taps the link
- **THEN** the browser navigates to `/leaderboard`

