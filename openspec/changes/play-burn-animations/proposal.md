## Why

The game currently feels static. The engine already emits richly-flagged action entries — every `last_actions` item carries `burned: true` for a 10-burn or 4-of-a-kind chain, `picked_up: true` when a player swept the pile, and `finished_pid: <pid>` when a play emptied a hand and crowned a winner — but the UIs treat those flags as text-only signals. A burn renders a 🔥 glyph in the status stack and that's it; no flash on the pile card. A pickup updates two numbers (deck/discard) and a name in the ticker; nothing animates between the pile and the player's hand area. An illegal play attempt fires `showError` as a toast but the *card the user actually clicked* doesn't react. The 👑 winner-name in the game-over panel is the most exciting moment in the game and it just sits there.

The fix is small and entirely client-side: subtle CSS animations triggered by class-toggling, driven off the same `last_actions[-1]` entry the status stack already consumes. JS only needs to detect "is this a NEW entry since the last render?" — it already has `state.lastSeenActionTs` or equivalent rendering bookkeeping (track an index if not). Every animation respects `prefers-reduced-motion`. Durations stay short (150–350 ms) so the game remains responsive.

## What Changes

- **Desktop (`web-frontend`) and mobile (`mobile-frontend`)** both gain four CSS-keyframe animations, named consistently across the two surfaces so engineers can reason about them once:
  - `burn-flash` — when the newest `last_actions` entry has `burned: true`, the pile card SHALL briefly flash an accent (warm) color and bounce up before the next state broadcast slides the new pile card in. Duration ~300 ms.
  - `pickup-sweep` — when the newest entry has `picked_up: true`, the pile area SHALL fade-out + slight shake while the player's hand row gets a quick "in-take" pulse (a 1px lift + subtle border-glow). Duration ~280 ms.
  - `illegal-shake` — when the WebSocket returns an error in response to a `play` message (the existing `showError` path), the user's currently-selected card(s) SHALL shake red for ~200 ms before the toast fades.
  - `winner-celebrate` — in the end-of-round panel, the winner-name `<span>` SHALL animate a small grow (1.0 → 1.08 → 1.0) plus a soft gold glow on first render. Duration ~350 ms.
- **Event-driven, not state-driven:** JS SHALL track the last-seen `last_actions` entry (e.g. by index, length, or a small monotonic stamp emitted by the engine if available). Animations SHALL fire only when a NEW entry appears — not on every state broadcast. Re-renders triggered by an opponent's selection toggle (no new action) SHALL NOT replay any animation.
- **`prefers-reduced-motion` is mandatory:** every keyframe block SHALL be paired with an explicit `@media (prefers-reduced-motion: reduce)` override that disables the transform/bounce (the color flash and glow MAY remain, but no movement and no shake).
- **No server change.** No new `last_actions` flags. No new sounds (a future change can layer audio on the same hooks).
- **No new DOM elements.** Animations target existing IDs / classes (`#pile-card`, `.pile-area`, `#m-pile-card`, the user's hand row container, the currently-selected card buttons, the winner-name `<span>` inside `#game-over`/`#m-game-over`).

## Capabilities

### Modified Capabilities

- `web-frontend`: gains a **Play & burn animations** requirement covering the four animation hooks (burn flash, pickup sweep, illegal shake, winner celebrate) and the new-action-edge detection rule, including the `prefers-reduced-motion` carve-out.
- `mobile-frontend`: gains a **Play & burn animations** requirement that mirrors the desktop behavior on mobile elements (`#m-pile-card`, `#m-hand-row`, `#m-winner-name`).

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/app.js` — track the last-seen action index on `state` (e.g. `state.lastSeenActionIndex = -1`). On render, if `view.last_actions.length - 1 > state.lastSeenActionIndex`, inspect the newest entry and class-toggle the appropriate target element(s). Remove the class on `animationend` (or via a `setTimeout` matched to the keyframe duration). Wire the illegal-shake hook into the existing WS error handler that calls `showError`.
  - `static/styles.css` — four `@keyframes` blocks (`burn-flash`, `pickup-sweep`, `illegal-shake`, `winner-celebrate`) plus the four target-element rules (`.pile-card.is-burning`, `.pile-area.is-pickup`, `#hand-row.is-pickup`, `.card.is-illegal`, `#winner-name.is-celebrating`). One `@media (prefers-reduced-motion: reduce)` block disabling transforms and shake.
  - `static/mobile.js` — same bookkeeping and class-toggling logic against the mobile IDs.
  - `static/mobile.css` — parallel keyframe + target-element rules scoped to the mobile selectors; parallel reduced-motion block.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Added` bullet ("Play & burn animations: pile flashes on burn, pickup sweeps toward your hand, illegal plays shake the selected card, the winner name celebrates. All animations respect `prefers-reduced-motion`.").
- **Depends on:** none beyond main.
- **Out of scope:**
  - Sound effects (a separate proposal can add audio on the same JS hooks; this change deliberately stops at visual).
  - Animating the deck card drawing into a player's hand at end-of-turn refill. The flagged events (`burned` / `picked_up` / `finished_pid`) are the focused trigger set.
  - Animating opponents' face-up plays. Out of scope; if a future change wants opponent-side flourishes it can extend this requirement.
  - Server-side animation hints (e.g., engine telling the client a specific easing). The client picks all timing.
