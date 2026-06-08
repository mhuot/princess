## Context

The fan-out hand from the `mobile-ui` change uses absolute positioning + `transform: rotate(angle) translateY(lift)` per card to approximate a real hand. It looked nice in mockups but in practice:

- A 6-card hand already shows visible distortion at the edges.
- The rank/suit on a rotated card is harder to read at small sizes.
- Tap targets are rectangular but the visual is angular — when two adjacent cards overlap, users sometimes tap the wrong one.
- 10+ cards crowd badly.

A horizontally scrolling row is the dominant pattern on phones for "more content than fits on screen" — image carousels, story rails, Apple Music tracklists. Native scroll-snap gives the carousel feel for free.

## Goals / Non-Goals

**Goals:**
- A hand row where every card is full-size, oriented straight, easy to read.
- ~3 cards visible at iPhone 14 width with clean snapping when you swipe.
- Two affordances for "more cards exist": gradient fade at the edges AND tappable chevron buttons.
- A sort toggle so the player can group same-rank cards quickly.

**Non-Goals:**
- Preserving the fan-out look for nostalgia. The change replaces it entirely.
- Drag-to-reorder. Sort is rank-asc only.
- Persisting sort across page refresh.
- Multi-axis sort (rank then suit). Rank-asc, ties broken stably.

## Decisions

### Replace, don't toggle
**Choice:** The mobile hand is *only* the scrolling row from this point on. No setting to switch back to the fan.
**Why:** Two layouts means two sets of bugs and two regressions surfaces. The fan-out was a v1 design; the scroll-row is the v2.

### `scroll-snap-type: x mandatory` + `scroll-snap-align: start`
**Choice:** Apply scroll-snap to the container with `x mandatory` and align children to `start`. Each card becomes a snap stop.
**Why:** Native, no JS. Survives keyboard/momentum scrolling. Smooth on iOS Safari and Chrome Android.

### Card sizing: `min-width: calc((100% - 32px) / 3)` and `width: calc((100% - 32px) / 3)`
**Choice:** Compute card width so 3 fit at the container width minus gaps. Use `calc()` with the parent container's width (not `100vw`), since the container is padded.
**Why:** Adapts to actual hand container width, not the viewport. If the container shrinks (e.g., tablet sidebar), cards shrink proportionally.

### Edge indicators: gradient fade + tappable chevrons
**Choice:** Two layers:
1. A subtle `linear-gradient(to right, var(--surface) 0, transparent 24px)` overlay on each edge (pseudo-elements), only visible when there's more content.
2. Two chevron buttons (`‹`/`›`) anchored at the edges that tap-scroll by one card width.
**Why:** Visual fade for at-a-glance; tap target for users who haven't realized the row is scrollable.

### Update indicators with the `scroll` event
**Choice:** Listen on the hand container's `scroll` event. Compute `atStart = scrollLeft <= 4` and `atEnd = scrollLeft + clientWidth >= scrollWidth - 4`. Toggle CSS classes on the indicators.
**Why:** Cheap (passive listener, single integer comparison). The 4px tolerance handles sub-pixel rounding.

### Sort: toggle button, default ON, rank-asc, suits stable
**Choice:** Above the hand: `<button id="m-sort-btn" aria-pressed="...">Sort: rank</button>` toggling to `Sort: off`. The view's `hand` array is sorted in JS before rendering. We track an `originalIndex` per card so the play action submits the original (server) index.
**Why:** Default ON because most users will want sorted cards. Aria-pressed reflects state for screen readers.

### Hand count in the toolbar
**Choice:** Render a small `<span>X cards</span>` next to the sort button.
**Why:** With horizontal scroll, you can't see all cards at once. A count fixes that.

### Selected-card lift survives scroll
**Choice:** The `.selected` style still uses `translateY(-6px)`; in a scrolling row this lifts the card slightly above the row. Tap target unchanged.
**Why:** Visual continuity with the rest of the UI (selected cards always lift).

### Setup grid unchanged
**Choice:** Setup phase keeps the 2×3 grid. The scroll-row + sort applies only to the playing-phase hand.
**Why:** 6 setup cards always fit on screen; no scroll or sort needed. Different problem.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Snap fights with momentum scroll on iOS | `mandatory` can feel jerky if cards are large; tested at 3-visible widths it's fine. If user reports, fall back to `proximity`. |
| Sort button below the action bar gets covered by safe-area inset | The toolbar sits *above* the action bar but inside the scroll-able section. The action bar uses `env(safe-area-inset-bottom)`; the hand row sits above it. Tested. |
| Edge indicators flicker on narrow scroll values | 4px tolerance in the scroll listener; CSS transitions on opacity. |
| Sort toggle resets on every broadcast (e.g., bot plays a card) | Store `state.sortHand: true/false`; persist within the page session. Default true. |
| Scrolling AND tapping on iOS sometimes triggers both | `touch-action: pan-x` on the row container limits to horizontal pan; tap inside a card is unaffected. |

## Migration Plan

1. **HTML:** rename `m-hand-fan` to `m-hand-row` (or keep the id; rename is cosmetic). Add `<div id="m-hand-toolbar">` with sort button + count. Add `<button id="m-hand-prev" class="m-hand-edge prev">‹</button>` and `<button id="m-hand-next" class="m-hand-edge next">›</button>` inside the hand container.
2. **CSS:** delete the fan-out rules (`.m-hand-fan { position: relative; height: 140px; ... }`, `.m-hand-card { position: absolute; transform-origin: ...; transition: transform 0.15s ... }`). Add `.m-hand-row` (flex, horizontal scroll, snap, no wrap), bigger `.m-hand-card` width via `calc()`, `.m-hand-edge` chevron styling, `.m-hand-row::before/::after` gradient fades.
3. **JS:** drop the angle/lift math from `renderHand`. Render plain flex items. Add `state.sortHand: true`. Add `applySort(cards)` that returns `[{c, originalIndex}, ...]` sorted by rank then by `originalIndex` (stable). Wire the sort button and chevron buttons. Add `updateEdgeIndicators()` and attach it to the row's `scroll` event.
4. **Docs:** CHANGELOG `### Changed` bullet.
5. Commit + push + CI + merge.

Rollback: revert the three static files. Engine, server, desktop untouched.

## Open Questions

- None.
