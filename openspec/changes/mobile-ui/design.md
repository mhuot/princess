## Context

The desktop UI lives at `/` and is dense — flex rows with full-size cards, a configuration panel, a footer link to a logs viewer. On a phone it shrinks but doesn't transform: cards still flow horizontally and wrap, the legend takes a whole screen of vertical space, and the lobby's House-rules `<select>` is a tiny dropdown.

A separate `/m` route is the cleanest way to ship a hand-tuned layout without polluting the desktop CSS with viewport overrides. Backend is unchanged — the WebSocket protocol already speaks JSON state; either frontend can render it.

## Goals / Non-Goals

**Goals:**
- A native-feeling phone layout: fan-out hand at the bottom, sticky action bar, big tap targets.
- One-thumb operation: action buttons within thumb reach (bottom 30% of the screen).
- Read at a glance: opponents collapsed, status condensed to a single line, pile + rule centered.
- Reuse the existing WebSocket protocol and broadcast shape — no new server features other than two static-page routes.
- 390px portrait minimum width (iPhone 14). Slightly wider (393, 414, 430) should look the same, just with more breathing room.

**Non-Goals:**
- Touch gestures beyond tap (no drag, no swipe, no long-press). Tap to select, tap Play. v1 ergonomics.
- Auto-redirect by user-agent. Users pick `/m` themselves.
- House rules editing on mobile. Host uses desktop for setup; mobile is for play.
- Bot removal on mobile.
- Landscape orientation (portrait only; landscape is acceptable but not polished).
- Tablet-specific layout (≥ 768px); mobile UI either falls through or pads. Address in a follow-up if a user complains.
- Same-file responsive CSS on the desktop UI. The desktop UI doesn't change.

## Decisions

### Two new routes, one new HTML
**Choice:** `GET /m` → `static/mobile.html`. `GET /m/{code}` → `static/mobile.html` (frontend reads the code from `location.pathname` like `/room/{code}` does today).
**Why:** Mirrors the desktop pattern (`/`, `/room/{code}`). The shortcut URL for a friend is `<host>/m/AB12`.

### Separate `mobile.{html,css,js}` files, no shared CSS with desktop
**Choice:** Fresh files. Some JS helpers (postJSON, badge, rankLabel, glyph rules) can be duplicated rather than refactored into a shared module — the project doesn't have a build step so a "shared.js" would just be a third script tag.
**Why:** Hard separation prevents cross-contamination. The desktop CSS uses opinions (fixed card width, flex rows) that fight a small viewport; rewriting from scratch is faster than overriding.
**Trade-off:** ~150 lines of duplicated helpers. Acceptable for v1.

### Fan-out arc via CSS transforms
**Choice:** Render each hand card as a positioned `<button>` inside a relatively-positioned container. Each card gets `transform: rotate(<angle>deg) translateY(<lift>px)` based on its index in the hand. The lift centers on the middle of the arc; the rotation increases linearly toward the edges.
**Why:** Pure CSS, no canvas. Tap targets stay rectangular (no SVG hit-testing complexity). The selected state adds an extra negative translateY to "pop" the card up.
**Trade-off:** A wide hand (10+ cards) crowds the edges. We cap the angle at ±25° and let cards overlap heavily past N=7.

### Tap-to-select, tap Play, no drag
**Choice:** Touch interaction is exclusively tap. Tapping a card toggles selection (multi-rank cards stack like the desktop UI). Tapping Play submits.
**Why:** Drag-to-play is a v2 polish; tap-to-select is a robust v1.

### Sticky bottom action bar
**Choice:** A `position: fixed` (or `sticky`) row at the bottom of the viewport with two buttons: Play (green, primary) and Pick up (red). The fan-out container sits *above* the bar; the cards' arc bottom is roughly 80px above the screen bottom so the bar never overlaps a selected card.
**Why:** Action affordance always in thumb reach. Survives keyboard popup (renames use a sheet, not an inline input).

### Opponents as a horizontal strip
**Choice:** A single-row scrolling strip at the top. Each opponent is a 56-wide card showing avatar (initial circle), name (truncated), hand count, and a thin border that lights up when it's their turn.
**Why:** Reclaims vertical space for the pile + hand.

### Status as a one-line ticker
**Choice:** Newest entry from `view.last_actions` shown as a single line under the opponents strip. Tap to expand into the full 3-entry stack.
**Why:** A 3-line stack steals real estate on a 667-tall screen. One line + tap-to-expand is enough.

### Modal for rules (`?` in the top bar)
**Choice:** A small `?` icon next to the room code. Tapping it opens a `<dialog>` listing the three wilds (2, 10, reverse) and what the reverse rank currently is.
**Why:** Discoverable, doesn't take vertical space when not used.

### Setup phase: 2×3 grid (not fan-out)
**Choice:** During setup the 6 choose cards render in a 2×3 grid. Tap to select up to 3; 4th tap replaces the oldest.
**Why:** Fan-out for setup would be cute but harder to read. A grid is unambiguous. Same rules as desktop.

### Winner panel reuses desktop's renderer shape
**Choice:** The mobile winner panel has the same DOM structure (`#game-over` with `#winner-name`, `#winner-subtitle`, `#winner-final-action`, `#results`, `#rematch-btn`) as desktop. The mobile CSS styles them larger.
**Why:** One renderer, one set of test cases.

### Quit modal: bottom sheet, not centered dialog
**Choice:** On mobile the quit modal slides up from the bottom as a sheet. Same options (Take over with bot / End round / Abort / Leave).
**Why:** Bottom-sheet pattern is familiar on phones; centered dialogs feel desktop-y.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Fan-out hand looks cramped with 10+ cards | Cap rotation angle and let cards overlap heavily; tap target is the topmost card. |
| ~150 lines of duplicated helpers between app.js and mobile.js | Acceptable for v1; revisit if we add a build step. |
| User accidentally visits `/m` on desktop | The mobile UI works on desktop too — it just looks small. They can navigate to `/` if they prefer. |
| The two UIs drift apart as features land | The change template's "Docs touched" line will remind authors; reviewers also check. Mobile UI lives behind `/m` so missing a feature isn't broken, just absent. |
| Keyboard popup on a rename covers the bottom action bar | Renames use a bottom-sheet modal; the input is inside the sheet, the sheet auto-scrolls. |
| Pinch-zoom on the fan-out arc looks weird | Disable user-scalable in the viewport meta for the mobile page only. |

## Migration Plan

1. Server: two new GET routes returning `static/mobile.html`.
2. Frontend: write `mobile.html`, `mobile.css`, `mobile.js`. Build the page section-by-section: lobby → setup → game (with fan-out) → winner → quit sheet.
3. Smoke: run the server, hit `/m` on a phone (or a 390px-wide DevTools emulation), create a room, play a round.
4. Docs: README mobile URL note; CHANGELOG `### Added`.
5. Commit + push + CI + merge.

Rollback: delete the three static files and revert the two server routes. The desktop UI is untouched.

## Open Questions

- Should the mobile page also be linked from the desktop footer (e.g., "📱 mobile")? Recommendation: yes, footer link is one line and self-explanatory.
- What about a way for the host to send the `/m/<code>` URL to a friend? Recommendation: tap-to-copy on the room code in the top bar (mobile) and a small Share button (mobile + desktop) — punt to follow-up.
