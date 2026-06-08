## Context

The sticky action bar lives at `bottom: 0` with `position: fixed`. The page can scroll behind it — but no content currently reserves space for it. So a wrapped hand whose last row extends past the action bar's top edge is both *invisible* (under the bar) and *unreachable* (no padding gap). Even when you DO scroll, you don't know there's more to find.

Two cheap fixes solve both halves:

- **Bottom padding** on the game screen pushes the bottom of the document down, so when you scroll to the very bottom, the last hand row sits comfortably above the action bar's top edge.
- **A visibility-aware "↓ N more" pill** explicitly tells you (and lets you jump to) the off-screen rows.

The `IntersectionObserver` API is the right tool for "is the end of this list currently visible?" — it fires once when the sentinel crosses the threshold, no per-frame work.

## Goals / Non-Goals

**Goals:**
- Make off-screen hand rows discoverable and reachable.
- Show the user **how many cards** are below, not just "more."
- Tap the indicator to jump to the end.
- Stay invisible when the whole hand is on screen (the common case).

**Non-Goals:**
- A symmetric "↑ scroll up" indicator. The top bar gives orientation.
- Vertical scroll inside a fixed-height hand container. Page scroll is already familiar; we're enhancing it, not replacing.
- Auto-scroll on selection or on render — only on tap of the chip.
- Tablet/desktop. This is purely a mobile (`/m`) concern; the desktop UI doesn't wrap.

## Decisions

### Sentinel + IntersectionObserver, not a scroll listener
**Choice:** Append an `<span id="m-hand-end-sentinel">` after the last hand card. An `IntersectionObserver` toggles the hint chip when the sentinel's intersection with the viewport changes.
**Why:** Cheap. Browser fires the callback only at transitions — no 60 Hz polling. Handles dynamic content (sort toggle, broadcasts adding cards) for free because the sentinel always stays at the end.

### "↓ N more" not just "↓ more"
**Choice:** The chip's label is the exact count of cards whose top edge is below the action bar's top edge.
**Why:** Concrete. If 3 cards are hidden, "↓ 3 more" tells you whether scrolling is worth the gesture vs. "is there anything down there at all?"

### Tap to jump to the end
**Choice:** Tapping the chip calls `sentinel.scrollIntoView({ block: "end", behavior: "smooth" })`.
**Why:** Faster than swiping; the chip is already a visible target.

### Anchored above the action bar, centered horizontally
**Choice:** `position: fixed; bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 8px); left: 50%; transform: translateX(-50%);`
**Why:** Above the action bar (so it doesn't overlap Play/Pickup), centered (so users see it without scanning).

### Pill shape, accent color, soft shadow
**Choice:** Rounded pill (~28px tall), `background: var(--accent)`, `color: var(--bg)`, `box-shadow: 0 4px 12px rgba(0,0,0,0.4)`.
**Why:** Visually distinct from the dark surface; reads as "interactive control" not "static label." High contrast for AAA.

### Bottom padding on `#m-game` matches the action bar
**Choice:** `padding-bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 12px);`
**Why:** Reserves space so the last hand row clears the action bar at the bottom of the document. The 12px buffer separates the last row from the bar visually.

### Compute count by iterating `.m-hand-card`
**Choice:** When the observer fires "not intersecting," walk the card list and count cards whose `getBoundingClientRect().top` exceeds the action bar's top edge. Cache the bar's top edge once per observer fire.
**Why:** Direct and correct. The IntersectionObserver tells us "stuff is off-screen"; counting cards tells us how many.

### Threshold: action-bar's top edge, not viewport bottom
**Choice:** A card is "hidden" if its `top` is below the action bar's top edge (which is `window.innerHeight - actionBarHeight`). Use the action-bar `getBoundingClientRect().top`.
**Why:** Cards trapped under the action bar are functionally hidden even though technically inside the viewport.

### Use a 50px rootMargin on the IntersectionObserver
**Choice:** Configure the observer with `rootMargin: "0px 0px -<action-bar-height + 12>px 0px"`.
**Why:** The observer fires when the sentinel crosses the action bar's top, not when it crosses the literal viewport bottom. Matches the "hidden under the bar" definition above.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Observer doesn't recompute if the sentinel is never re-attached on Sort | We re-append the sentinel inside `renderHand` after every render; the observer re-observes when it sees a fresh element. |
| Tap on the chip and on the action bar's edge could overlap | Chip sits 8 px above the bar with a horizontal center; the action bar buttons span ~50% each from the edges. The chip lives in the center gap. |
| Bottom padding breaks visual rhythm if hand fits in one row | The padding is below all hand content; an empty space at the bottom is fine — it lives below the action bar's top edge anyway. |
| Smooth-scroll on iOS sometimes overshoots | `scrollIntoView({ block: "end" })` is reliable across iOS and Android in current versions. Acceptable. |
| Stale chip count after broadcast adds cards | Observer fires on intersection-state changes; the count update only runs at those moments. If the count drifts slightly between renders we accept it — the chip's role is "tell me there's more," not "exact accounting." |

## Migration Plan

1. **HTML:** add `<div id="m-hand-scroll-hint" class="m-hand-scroll-hint" hidden>↓ more</div>` to `#m-game`, sibling of the action bar.
2. **CSS:** `#m-game { padding-bottom: ...; }`. Add `.m-hand-scroll-hint` style. Add `#m-hand-scroll-hint[hidden] { display: none !important; }` to the existing `[hidden]` override block.
3. **JS:**
   - Create a module-level `handEndObserver` (initialized once on `DOMContentLoaded`) with `rootMargin: "0px 0px -<actionBarHeight + 12>px 0px"` and a callback that toggles the hint and updates its label.
   - In `renderHand`, append `<span id="m-hand-end-sentinel">` to `#m-hand-row` after the cards, and `handEndObserver.observe(sentinel)`. The observer cleans up the old sentinel automatically because each `renderHand` rebuilds the DOM.
   - The chip's click handler smooth-scrolls the sentinel into view.
4. **CHANGELOG.md** entry.
5. Commit + push + CI + merge.

Rollback: revert the three static files. Engine + desktop unchanged.

## Open Questions

- Use `rootMargin` to define "hidden" or stick with viewport-bottom intersection? Recommendation: `rootMargin` — matches the "under the action bar" mental model.
- Should the chip auto-hide after a delay even if still over-scrolled? Recommendation: no — the chip is a help, not an annoyance. Visible only when relevant.
