## Why

The mobile fan-out arc is pretty but hard to actually *read* — overlapping cards crowd the edges, the rank/suit on a rotated card is harder to scan, and the tap target is rectangular but the visual is angular. With 10+ cards the overlap gets dense.

A horizontally scrolling row of full-size cards is simpler: tap targets stay flat, every card is identical size and oriented straight, you swipe to see more. Three cards visible at the iPhone 14 width is a good balance — large enough to read clearly, sees more than a one-card carousel.

Also missing today: a **Sort** affordance on mobile. Desktop has it. With a hand of 8–12 cards, sorted-by-rank is essential for spotting same-rank groups (key to playing legal multi-card stacks and triggering four-of-a-kind burns).

## What Changes

- **Replace the fan-out arc with a horizontally scrolling row** of full-size cards.
  - Visible cards: **3** at viewport ≥ 360px wide (4 at 480px+, 2 below 360px). Card sized so 3 fit cleanly with the existing 8px gap.
  - `scroll-snap-type: x mandatory` + `scroll-snap-align: start` on each card so swiping snaps to whole-card increments.
  - Tap a card to select (same multi-rank semantics as before); selected cards still get the 4px accent border + bottom-left ✓ glyph + slight lift.
- **Edge indicators** for more cards off-screen.
  - Left and right chevron buttons (`‹` / `›`) that fade in/out based on `scrollLeft` and `scrollWidth`. Tappable: tapping advances the scroll by one card width.
  - Subtle gradient fade on the left/right edges of the hand container reinforces the "more here" cue.
- **Sort button** added to a new small toolbar above the hand row.
  - Toggle between **Sort: rank** (default) and **Sort: off** (deal order). Same client-side sort as desktop (rank ascending, suits stable). Server indices are preserved internally so plays go to the right card.
  - The toolbar also shows a small hand count ("X cards").
- **Setup phase grid is unchanged.** It stays 2×3.
- **Spec rewrite:** the "Game view layout (mobile)" requirement currently mandates fan-out arc with `transform: rotate(angle) translateY(lift)` per card, capped at ±25°. This change removes those clauses and replaces them with the scrolling-row rules.

## Capabilities

### Modified Capabilities

- `mobile-frontend`: replace the fan-out arc hand layout with a horizontally scrolling row; add a sort toolbar with edge indicators.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/mobile.html` — add `<div id="m-hand-toolbar">` (sort button + count) above the hand container; add left/right indicator buttons. The `<div id="m-hand-fan">` becomes `<div id="m-hand-row">` (or we can keep the id and just swap the layout — naming change is optional, kept consistent in tasks).
  - `static/mobile.css` — drop the fan-out rules (`.m-hand-fan`, the absolute-positioned `.m-hand-card` with transform). Add `.m-hand-row` (flex, horizontal scroll, snap), bigger `.m-hand-card` (`min-width: calc((100vw - 4 * 8px) / 3)` roughly), and edge-indicator styling.
  - `static/mobile.js` — `renderHand` switches from absolute-positioned `transform: rotate(…)` to plain flex items. Add `applySort()` for sort toggle; add `updateEdgeIndicators()` listener on the scroll container; wire the chevron buttons to programmatic scroll.
- **Affected APIs:** none. Engine and server unchanged.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Changed` (this is a behavior change to the mobile UI introduced in `mobile-ui`).
- **Depends on:** none beyond main.
- **Out of scope:**
  - Reordering cards by drag (only sort toggle, not manual rearrangement).
  - Auto-scroll to a selected card off-screen (the user is the one who tapped it; if they tapped it, it was visible).
  - Persisting sort preference across sessions.
  - Sort options beyond on/off (no "by suit" mode).
