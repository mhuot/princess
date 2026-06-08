## MODIFIED Requirements

### Requirement: Game view layout (mobile)

The mobile game view SHALL stack vertically (top to bottom):

1. **Top bar** — room code (tap to copy), `?` rules icon, **Rename** button, **Quit** button, status ticker (single-line newest action).
2. **Opponents strip** — single horizontal row, scrolls if needed; each opponent chip SHALL render, in vertical order: name + (bot) tag, current-turn / finished indicator, a **face-up cards row** showing the cards in `view.players[i].face_up` as small mini cards (about 22 × 32 px), and a counts line reading `hand N · down N`. Face-up cards whose rank equals `2`, `10`, or `view.config.reverse_rank` SHALL render with the wild `★` corner glyph. When an opponent has zero face-up cards remaining, the face-up row SHALL collapse to no extra height.
3. **Pile area** — centered: deck count, discard pile top card (full-size), rule indicator below.
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
