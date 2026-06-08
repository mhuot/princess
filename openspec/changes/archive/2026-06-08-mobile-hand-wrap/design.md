## Context

The `mobile-hand-scroll-sort` change introduced a horizontally-scrolling hand with snap and chevron indicators. It's a familiar phone-UI pattern but it's a poor fit for a card-game hand where seeing the whole thing at once matters more than having pretty individual cards. Players using it report scrolling back and forth to "remember" what they have.

A wrapping multi-row layout was an alternative considered in the original mobile-ui spec. We're switching now that we've felt the trade-off in practice.

The constraints:

- **Tap target ≥ 44 × 44 px** (accessibility floor; in the mobile-frontend spec).
- **Sticky action bar at the bottom**, ~80px tall including the safe-area inset.
- **Top half of the screen is "metadata"** (top bar, status, opponents, pile, table). At 844px tall iPhone 14 with a 56px top bar and ~270px above the hand, we have roughly 350px of vertical space for the hand area before it hits the action bar.

350px / 90px-tall cards = ~3.8 rows. A 10-card hand at 5/row needs 2 rows — comfortably fits. A 15-card hand needs 3 rows — still fits. A 20-card hand needs 4 rows — bumps against the action bar; that's where the page-scroll fallback kicks in.

## Goals / Non-Goals

**Goals:**
- See the whole hand at once for the common case (3–10 cards).
- Tap targets still ≥ 44 × 44 px.
- Keep the **Sort** toolbar and the **count** badge (useful regardless of layout).
- Drop horizontal scroll plumbing entirely (no chevrons, no fades, no snap math, no scroll listener).

**Non-Goals:**
- A container-level vertical scroll with a "more below" indicator. Pages already scroll natively; we lean on that for rare 20+ card hands.
- Auto-resizing cards to always fit the hand into 2 rows. Cards stay a fixed size; row count flexes.
- Configurable cards-per-row preference. Fixed at 5 (default), 4 (narrow), 6 (wider).
- Drag-to-reorder. Sort remains the only reorder mechanism.
- Touching desktop or setup-grid layouts. Those stay as-is.

## Decisions

### 5 cards per row at default width
**Choice:** `flex: 0 0 calc((100% - 24px) / 5)` with `gap: 6px` between cards. At 390px viewport minus 32px of container padding = 358px usable. 5 cards × 67px + 4 gaps × 6px = 359px. Fits.
**Why:** 67px wide × ~90px tall is plenty for the rank+suit and well above the 44×44 tap target. Five cards per row means a 10-card hand fits in two rows that are both visible above the action bar.

### Breakpoints: 4 / 5 / 6 cards per row
**Choice:**
- `< 360px` → 4 cards per row (`calc((100% - 18px) / 4)`, gap 6px) — keeps cards at ≥ 60px even on narrow phones.
- `360–479px` → 5 cards per row (default).
- `≥ 480px` → 6 cards per row (`calc((100% - 30px) / 6)`).
**Why:** Matches the existing breakpoint structure from `mobile-hand-scroll-sort`. The math is simple; the visual is predictable.

### Card aspect ratio ~3:4 (e.g. 67 × 90)
**Choice:** Set `height: 90px` explicitly so the card is unambiguously playing-card-shaped at this size.
**Why:** Width comes from flex math (varies by viewport). Locking height keeps the aspect tidy.

### Remove the chevron buttons and edge fades
**Choice:** Delete `#m-hand-prev`, `#m-hand-next`, `.m-hand-edge*` CSS, and `.m-hand-wrap::before/after` gradient pseudo-elements.
**Why:** Pure cleanup. Nothing depends on them in the new layout; leaving dead UI elements is worse than removing.

### Keep `#m-hand-wrap` as a no-op container
**Choice:** The HTML wrapper `<div id="m-hand-wrap">` stays even though it no longer needs `position: relative` for chevrons.
**Why:** Touching less HTML; the `[hidden]` override in CSS already covers `#m-hand-wrap[hidden]`. Harmless.

### Drop the `scroll` listener and `updateEdgeIndicators` / `scrollHandBy`
**Choice:** Delete the helpers and their listener registrations.
**Why:** No horizontal scroll means nothing to listen to.

### `flex-wrap: wrap` with `justify-content: flex-start`
**Choice:** Cards align to the left, last row may be partial.
**Why:** Predictable; left-aligned reads naturally. A center-aligned partial row would draw the eye to whatever's "near the middle" — not what we want.

### Selected lift survives wrap
**Choice:** `.m-hand-card.selected { transform: translateY(-6px); }` stays. The wrap container's natural gap accommodates the small lift without overlapping the next row.
**Why:** Visual continuity with the rest of the UI.

### Page scrolls for huge hands; no extra container scroll
**Choice:** Let the natural page scroll handle 20+ card hands.
**Why:** Saves complexity. A page scroll is the universally-understood phone gesture for "more below"; a container-internal scroll is sometimes confusing on iOS. The sticky action bar stays put either way.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Smaller cards are harder to read at a glance | We keep rank + suit at font-size ~1.05 rem; the layout is still legible. If user reports, we can nudge dimensions in a follow-up. |
| Huge hands (20+) push the action bar relationship awkwardly when the page scrolls | The action bar is fixed; page scroll just exposes more hand rows. Tested in DevTools. |
| `flex-wrap` plus `gap` has minor sub-pixel rounding | The `(100% - 24px) / 5` math ensures rounding only affects the last few pixels per row; cards never overflow the row. |
| Edge cases with empty hand (deck/pile drained) | `renderHand` already hides the toolbar + wrap when `me.hand.length === 0`. No change. |
| Some users may miss the snap feel | Sort by rank gives the same grouping; the wrap layout makes finding cards visual rather than tactile. |

## Migration Plan

1. **HTML:** delete `<button id="m-hand-prev">` and `<button id="m-hand-next">`. Keep `<div id="m-hand-wrap">`. Keep the toolbar.
2. **CSS:** rewrite `.m-hand-row` to drop `overflow-x`, `scroll-snap-type`, `touch-action`, `padding: 8px 0 12px;` becomes `padding: 0;`. Add `flex-wrap: wrap`. Bump `gap` to 6px. Resize `.m-hand-card` (height 90px, font-size 1.05rem; width via `calc`). Delete `.m-hand-edge*` and `.m-hand-wrap::before/after` rules.
3. **JS:** delete `updateEdgeIndicators` and `scrollHandBy`. Remove the scroll listener and chevron click handlers from `DOMContentLoaded`. Remove the trailing `updateEdgeIndicators()` call inside `renderHand`.
4. `CHANGELOG.md` `### Changed`.
5. Commit + push + CI + merge.

Rollback: revert the three static files. Engine + desktop unchanged.

## Open Questions

- Should a hand with 4 or fewer cards center horizontally on the row? Recommendation: no — left-align is more predictable and matches Sort intent.
- Do we need a hover-style indicator for *which* legal-hint cards are part of a same-rank group? Recommendation: not in v1; Sort already groups them visually.
