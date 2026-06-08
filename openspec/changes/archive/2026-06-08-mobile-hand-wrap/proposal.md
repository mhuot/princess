## Why

The horizontally-scrolling row (from `mobile-hand-scroll-sort`) shows three large cards at a time and you swipe / tap chevrons for the rest. It works but two things rub:

1. **You can't see your hand at a glance.** With ten cards, eight live off-screen. To plan a multi-card play or look for same-rank groups, you scroll back and forth.
2. **The cards are bigger than they need to be.** A full-size card on mobile is ~120 × 130px. A tap target needs only ~44 × 44 px (the project's accessibility floor). The rest is decoration.

Wrap the hand to multiple rows instead. Smaller cards (~67 × 90px at iPhone 14 width), 5 per row, so a 10-card hand fits in two rows that are both fully on screen above the action bar. No chevrons, no horizontal swipe, no scroll-snap math. You can see everything you hold.

## What Changes

- **Hand row layout flips from horizontal-scroll to `flex-wrap: wrap`.** Cards flow left to right then wrap; rows stack vertically.
- **Smaller cards.** Card width derived via `calc((100% - <total gaps>) / 5)` so **5 cards fit per row at 390px**. At 480px+ the breakpoint pushes to 6 per row. At < 360px (narrow phones we don't formally target), 4 per row keeps tap targets ≥ 44 px.
- **Sort toolbar + count badge stay.** Useful regardless of layout.
- **Edge indicators removed.** No horizontal scroll → no left/right chevrons, no gradient fades. Drop the `‹`/`›` buttons from the HTML, the gradient pseudo-elements from the CSS, and the `updateEdgeIndicators` / `scrollHandBy` helpers from the JS.
- **`scroll-snap-*` props dropped.** Cards are static flex items now.
- **Big-hand vertical overflow.** If a hand grows beyond 2 rows (rare — typically only after a forced pickup with 10+ cards), the page itself scrolls vertically; the sticky action bar stays anchored at the bottom. No new container scroll for v1.
- **Selected state unchanged:** 4px accent border + ✓ glyph + slight `translateY(-6px)` lift. Wild ★ glyph unchanged. Legal-hint outline unchanged.

## Capabilities

### Modified Capabilities

- `mobile-frontend`: hand row layout changes from "horizontally scrolling, snap, with edge chevrons" to "wrapping multi-row of smaller cards, 5 per row at default width."

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/mobile.html` — remove the two chevron buttons (`m-hand-prev`, `m-hand-next`); the `#m-hand-wrap` div stays as a simple wrapper (no longer needs `position: relative` for chevrons, but harmless to keep).
  - `static/mobile.css` — `.m-hand-row` switches to `flex-wrap: wrap`, removes scroll-snap and overflow rules; `.m-hand-card` shrinks (~67 × 90 px, font-size ~1.05 rem); drop the `.m-hand-wrap::before/after` gradient rules and `.m-hand-edge` button styling.
  - `static/mobile.js` — drop `updateEdgeIndicators()`, `scrollHandBy()`, the scroll listener, and the chevron click handlers from `DOMContentLoaded`. `renderHand` no longer calls `updateEdgeIndicators()`.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Changed` bullet — note the layout change.
- **Out of scope:**
  - A container-level vertical scroll with its own "more below" indicator for huge hands. v1 just lets the page scroll.
  - User-configurable cards-per-row.
  - Adaptive card sizing based on hand count (e.g., shrinking further to fit 15 cards in 2 rows). 5/row is fixed.
  - Reordering by drag — Sort is still the only reorder mechanism.
