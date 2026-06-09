## Context

Princess's engine already does the hard work for us. Every entry in `view.last_actions` (a bounded list, newest at the end) is a structured dict carrying not just the text the status stack renders but also boolean flags: `burned: true` for a 10-burn OR a 4-of-a-kind chain-burn, `picked_up: true` when a player swept the pile, and a string `finished_pid: "<pid>"` when the play emptied a hand and crowned a winner. Both UIs already read this list and pick the rightmost entry for the active-line text + glyphs (`🔥`, `↑`, `👑`). What's missing is a *visual* response to those flags on the actual game surfaces.

The current renderer is a "state in → DOM out" loop. Every WebSocket broadcast triggers `renderGame(view)` which rebuilds whatever the active phase needs. That makes deciding "is this a new event?" a little delicate: every render fires whether the new state carries a new action or merely reflects an opponent's pre-lock-in choose-card click. If we naively triggered an animation on every render, the pile would flash whenever any peer toggled a selection. We need an edge detector.

The two surfaces (desktop `app.js` + `styles.css`, mobile `mobile.js` + `mobile.css`) are parallel but distinct codebases — they don't share JS. The design must specify the *behavior* once and let each surface implement against its own IDs.

## Goals / Non-Goals

**Goals:**
- Four event-driven animations: burn flash, pickup sweep, illegal-shake, winner celebrate.
- Animations fire ONCE per new `last_actions` entry, not per render.
- Animations are subtle (150–350 ms) — the game stays responsive.
- `prefers-reduced-motion` users get a fully usable game with no movement-based animation. Color changes and gentle glows are acceptable; transforms, shakes, and bounces are not.
- WCAG AAA contrast is preserved on every state — including mid-animation frames. The burn flash uses the existing `--accent-warm` (or equivalent) which is already AAA against the pile background; the winner glow stays inside the existing gold palette.

**Non-Goals:**
- Sound. Out of scope; a follow-up change.
- Animating routine plays. Only flagged events (burn / pickup / illegal / win) animate. Normal "play a 7" stays silent visually.
- Animating opponents' face-up plays. Out of scope.
- New engine flags. The four current flags + the existing WS error path are sufficient.
- Persisting animation preferences (an explicit toggle). `prefers-reduced-motion` is the single source of truth.

## Decisions

### Track the last-seen action by index
**Choice:** Add `state.lastSeenActionIndex = -1` to the initial state on both surfaces. On every `renderGame(view)`, compute `const newest = (view.last_actions?.length ?? 0) - 1`. If `newest > state.lastSeenActionIndex`, the render is processing a NEW action — inspect `view.last_actions[newest]` and dispatch the right animation. Then `state.lastSeenActionIndex = newest`. If `newest <= state.lastSeenActionIndex`, skip animation work entirely.

**Why:** Indices are monotonic per round and trivial to compare. We don't need a timestamp; the engine already deduplicates entries by appending only on real moves. Index resets to -1 on round end or rematch as part of the existing state reset.

**Reset:** `state.lastSeenActionIndex = -1` whenever the phase transitions out of `"playing"` (game-over → rematch → setup → playing again) so the first action of a new round animates correctly. The simplest place to hook this is the same phase-tracking we already added for `setupSelected` reset.

### Class toggling, removed on `animationend`
**Choice:** For each animation, JS adds a class (`is-burning`, `is-pickup`, `is-illegal`, `is-celebrating`) to the target element, then registers a one-shot `animationend` listener that removes the class. CSS owns all timing and easing.

**Why:** Pure CSS keyframes are the cheapest, most predictable way to animate. Removing the class on `animationend` keeps the DOM clean and lets the same animation fire again on the next event without a forced reflow trick.

**Fallback:** if `animationend` doesn't fire (e.g., a reduced-motion override that sets `animation: none`), a `setTimeout(remove, durationMs + 50)` cleans up. Belt + suspenders.

### Burn flash targets the pile card; the new pile slides in naturally on next render
**Choice:** When the newest action has `burned: true`, JS adds `.is-burning` to `#pile-card` (desktop) / `#m-pile-card` (mobile) IF a pile-card element exists at the moment of the render. The keyframe runs ~300 ms: a quick color flash (default `var(--card-bg)` → `var(--accent-warm)` → `var(--card-bg)`) plus a single bounce (translateY 0 → -8px → 0). The new pile state, which the next state broadcast will deliver (or which the same broadcast already reflects on a chain-burn), simply replaces the element through the normal render — there's no special "exit" animation. The flash IS the punctuation.

**Why:** Doing a true "old card flies off / new card slides in" choreography would require holding the old element while inserting the new — way more JS. The flash + bounce reads as a burn punch without that complexity.

### Pickup sweep is a two-element pulse, not a path animation
**Choice:** When the newest action has `picked_up: true`, JS adds `.is-pickup` to BOTH the `.pile-area` (desktop) / `#m-pile` (mobile) AND the user's hand-row container (`#hand-row` / `#m-hand-row`) — but only if the picked-up player is the user (`view.last_actions[newest].player_pid === state.pid`). The pile-area animation fades opacity briefly with a small shake; the hand-row animation lifts 2px and adds a 1500-ms accent border glow that fades.

If the picker is an *opponent*, the pile-area still fades briefly (so everyone sees something happened to the pile) but the user's own hand is left alone.

**Why:** A true path animation (cards visually flying from the pile to the hand row across the page) is technically possible but adds a lot of geometry-math + DOM-cloning code for very little gain. The fade + complementary hand-row pulse delivers the same "you swept the pile" feedback in two simple CSS rules.

### Illegal-shake hooks into the WS error path
**Choice:** The existing `showError(msg)` is the canonical "play was rejected" landing point. We add a hook: at the moment of `showError` from a `play` reject, JS also adds `.is-illegal` to every card element currently carrying `.selected`. The keyframe is a 200-ms red-tinted shake (`translateX` -3 → +3 → -3 → 0). On `animationend` the class is removed.

**Why:** The toast already tells the user what they did wrong. Reacting on the card itself ties cause to effect. The hook is one line at the existing error site.

**Edge case:** if the user clears their selection before the error round-trips (rare; network is local), there's nothing to shake. That's fine — the toast still appears.

### Winner celebrate is one-shot on first game-over render
**Choice:** In the game-over panel branch, the winner name `<span>` is rendered with the class `.is-celebrating`. The keyframe is a 350-ms grow (scale 1.0 → 1.08 → 1.0) + soft gold drop-shadow. JS removes the class on `animationend`. A `state.celebratedRoundId` (or simply the action index that triggered the win) gates against re-firing on subsequent game-over re-renders within the same round.

**Why:** Game-over re-renders on every state broadcast post-end (e.g., when the host clicks Rematch). The user shouldn't see the winner glow re-fire every time someone takes an action in the dying-rounds-of-the-round. Gate it once.

### `prefers-reduced-motion` rules
**Choice:** Every keyframe block is paired with a `@media (prefers-reduced-motion: reduce)` rule that:
- For `burn-flash`: keeps the brief color flash, drops the bounce (`animation: burn-flash-color 300ms ease;` instead of the bounce variant).
- For `pickup-sweep`: drops the shake; the opacity dip and hand-row border glow remain (no transform).
- For `illegal-shake`: replaces shake with a brief red border (no movement). The toast still appears.
- For `winner-celebrate`: drops the grow; the gold drop-shadow stays as a static halo for ~500 ms then fades.

**Why:** WCAG and the project's existing AAA stance require this. Color and glow are not motion; they're acceptable. Transforms, shakes, and bounces are exactly the motion `prefers-reduced-motion` is meant to suppress.

### Animation durations live in CSS custom properties
**Choice:** `:root` gets `--anim-burn: 300ms; --anim-pickup: 280ms; --anim-illegal: 200ms; --anim-celebrate: 350ms;`. Keyframes reference these via `animation-duration: var(--anim-burn)`.

**Why:** Easy tuning. Easy to override en-bloc for reduced-motion or for future "performance mode" if we ever add one.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Animation fires on a re-render of an action the user already saw (e.g., reconnect mid-round delivers the full `last_actions` list) | The index reset rule says we reset on phase-OUT-of-playing only. A reconnect during playing keeps `state.lastSeenActionIndex` and only animates entries that exceed it. If the index lags (because we never saw earlier entries), the renderer will fire animations for every "new-to-us" entry in sequence — which is actually the correct UX for a reconnect; the user gets a quick rundown of what they missed. |
| `animationend` listener leaks if we forget to make it `{ once: true }` | Always use `addEventListener("animationend", handler, { once: true })`. Documented in the task list. |
| Burn flash fires on the *new* pile card (after the burn cleared the pile) instead of the burned card | When `burned: true` is processed, by the time we render we may already see the post-burn state — which on a `10♠` burn is "no pile top" (deck refill rebuilds it). In practice the engine reports the burn in the same `last_actions[-1]` as the play that caused it, and the rendered pile in that snapshot is the burning card itself. We animate whatever pile element exists at the moment of the new-action detection; if there's no pile element (e.g., a chain-burn that cleared the whole pile and the next state hasn't placed a new card), we no-op and skip the flash for that entry. Acceptable. |
| `prefers-reduced-motion` users see a flash of color they can't suppress | The color flash is opt-in by virtue of the user opening the page; it's not motion. If a user *also* dislikes color changes they can install browser-level overrides. We are not adding a separate toggle. |
| Animations stack visually if two flagged events arrive back-to-back (e.g., a 10-burn that finishes the round → both `burned: true` and `finished_pid` set on the same entry) | Both animations target different elements (`#pile-card` vs winner-name in `#game-over`). They run in parallel, which is fine — the visual story is "burn → win." |

## Migration Plan

1. **Desktop CSS:** add the four keyframes, the four target-element rules, and the `prefers-reduced-motion` overrides to `static/styles.css`. Add the duration custom properties to `:root`.
2. **Desktop JS:** in `static/app.js`, add `lastSeenActionIndex: -1` and `celebratedRoundId: null` to `state`. In `renderGame(view)`, after the existing phase tracking, run the new-action edge check and dispatch the right class-toggle helper. Add the `prefers-reduced-motion` MediaQueryList guard for any code-side branching (the CSS handles most of it; JS just needs to know whether to add classes at all if we want to skip them entirely — actually we still add the classes and let CSS decide what to do, so JS is media-query-agnostic). Hook the illegal-shake helper into the existing `showError` path for play rejects.
3. **Mobile mirror:** parallel changes in `static/mobile.js` + `static/mobile.css` against `#m-pile-card`, `#m-pile`, `#m-hand-row`, and the mobile winner-name slot.
4. **CHANGELOG:** `## [Unreleased]` `### Added` bullet.
5. **Verify:** manual smoke (10-burn, 4-of-a-kind, pickup, illegal play, win condition) on desktop + mobile, with reduced-motion on and off (DevTools "Emulate CSS prefers-reduced-motion: reduce").
6. Commit + push + CI + merge.

Rollback: pure-additive CSS keyframes + one JS state field + a handful of class-toggle calls. Revert the static-file diff and we're back to text-only event signals.

## Open Questions

- Should the pickup sweep ALSO play for opponents when *they* pick up (the pile flashes, but their hand-row isn't on our screen)? **Resolved:** yes for the pile-area fade (everyone sees something happened), no for the hand-row (we don't render opponents' hand rows in detail). Captured in the spec.
- Should illegal-shake also play for `pickup` errors (e.g., "can't pick up: it's not your turn")? **Resolved:** no — there's no specific "selected card" to shake on a pickup attempt. The toast is enough.
- Should the chain-burn that fires multiple `burned: true` entries on the same play burn multiple times? **Resolved:** we animate the newest entry only; the chain-burn shows as a single visual burn punctuation. The status stack still records the chain in text.
