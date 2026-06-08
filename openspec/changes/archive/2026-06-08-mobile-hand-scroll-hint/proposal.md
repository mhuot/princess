## Why

After `mobile-hand-wrap`, a hand of ≤ ~15 cards fits in the viewport above the sticky action bar. Bigger hands (the user just hit one after a forced pickup) extend past it — but with **no visual cue** the user can't tell whether the action bar is covering more cards or the row simply ends. Two compounding gaps:

1. **No bottom padding** on the game screen, so the last hand row can be trapped *behind* the action bar even when scrolled — you can't reach it.
2. **No "more below" indicator** to tell the user there's a row off-screen worth scrolling to.

Fix both. Small change, big readability win.

## What Changes

- **Add bottom padding to `#m-game`** equal to `var(--m-action-h)` + safe-area inset + ~12 px buffer so the **last hand row clears the action bar** when scrolled into view.
- **Add a floating "↓ N more" hint chip** that:
  - Sits `position: fixed`, anchored just above the action bar (`bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 8px)`), centered horizontally.
  - Becomes visible only when the **last hand card is not currently visible** in the viewport (the row extends below the action bar's top edge).
  - Displays `↓ N more` where N is the count of hand cards entirely below the viewport.
  - Tappable: tapping it smooth-scrolls to the end of the hand row.
  - Hides when the user scrolls enough that all cards are visible.
- **Implementation via `IntersectionObserver`** on an invisible sentinel element appended at the end of `#m-hand-row` — fires only when the sentinel's intersection state changes (cheap, no scroll listener spam).

## Capabilities

### Modified Capabilities

- `mobile-frontend`: "Game view layout (mobile)" gains the bottom-padding clause and the overflow-indicator clause + scenarios.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/mobile.html` — add `<div id="m-hand-scroll-hint" hidden>↓ more</div>` near the bottom of `#m-game` (sibling of the action bar) and an `<span id="m-hand-end-sentinel">` to be appended programmatically.
  - `static/mobile.css` — `#m-game { padding-bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 12px); }`. Style for `.m-hand-scroll-hint` (pill, accent background, soft shadow, ≥ 44 px tap target). `[hidden]` override added if needed.
  - `static/mobile.js` — `renderHand()` appends `#m-hand-end-sentinel` to `#m-hand-row` after the cards; an `IntersectionObserver` (set up once on `DOMContentLoaded`) toggles `#m-hand-scroll-hint`'s `hidden` based on the sentinel's visibility; computes the "N more" count by counting cards whose bounding rect's `top` exceeds the action bar's top; tap on the chip calls `scrollIntoView({block: 'end', behavior: 'smooth'})` on the sentinel.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Changed` (or `### Added`) bullet.
- **Out of scope:**
  - A "↑ scroll up" hint when scrolled past the top (the top bar/status are usually enough orientation).
  - Vertical-only container scroll inside `#m-hand-wrap`. Page scroll is the chosen mechanism.
  - Auto-scrolling to the selected card if it's off-screen.
