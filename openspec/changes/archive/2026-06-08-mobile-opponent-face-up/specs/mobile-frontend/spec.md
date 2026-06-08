## MODIFIED Requirements

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
