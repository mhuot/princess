## Context

Setup-phase rendering is driven by `renderSetup(view)` in `static/app.js`, which reads `state.setupSelected` (a `Set<number>` of choose-pile indices) to decide which choose cards get the `.selected` class. The Set is initialized once at page load as `new Set()` and mutated by `toggleSetupSelect()` (add / remove / replace-oldest). It's cleared when `me.ready === true` (after a successful `set_face_up`).

That clear-on-ready hook covers the happy path — pick three, lock in, Set is emptied, opponents lock in, phase advances to `"playing"`. But there are at least two paths where the Set could hold stale indices when a fresh setup render fires:

1. **Rematch without a clean Set:** if the previous round's lock-in path was skipped (e.g. the host aborted mid-setup), the Set may still hold three indices when the rematch's fresh setup renders.
2. **Mid-setup phase re-entry:** if the WebSocket disconnects and reconnects mid-setup, the new state broadcast triggers a re-render. The Set survives the reconnect; the new render uses it.

A second source of "looks pre-selected" is a visual collision: wild-rank cards (2, 10, the configured reverse rank) wear a small gold ★ glyph in the top-right corner. The current `.selected` style adds a thicker border and a small upward translate — strong on a desktop monitor, weak on a phone. A user glancing at six cards, three of which carry a corner badge, can read the badge as "already picked."

## Goals / Non-Goals

**Goals:**
- The setup render never starts with any card marked selected.
- Selection is cleared whenever the player re-enters the setup phase (rematch, reconnect, abort + restart).
- The `.selected` visual is unmistakably different from the wild ★ glyph.

**Non-Goals:**
- Disabling the bot auto-pick. Bots still pick their face-up cards at game start.
- Persisting selection across page refresh. Out of scope.
- Adding a "remember my last pick" feature for humans. Out of scope.
- Touching the engine. The fix is entirely client-side.

## Decisions

### Reset the Set on phase transition, not on every render
**Choice:** `renderGame(view)` resets `state.setupSelected` when it routes into the setup branch IF the player is not currently `ready`. This catches the rematch and reconnect cases without blowing away in-progress selections during a normal setup render (which happens after every broadcast — currently the only state-change source during setup is a peer's lock-in).
**Why:** Resetting on every render would erase the user's selections every time a peer locks in. Resetting only on transition-into-setup is precise.

### Detect phase transition by tracking `state.phase`
**Choice:** Add `state.phase = null` initial. At the top of `renderGame(view)`, before any other work: `const wasPhase = state.phase; state.phase = view.phase;` Then if `wasPhase !== "setup" && view.phase === "setup"` AND `!view.you.ready`, clear `state.setupSelected`.
**Why:** Tracking the previous phase is the simplest way to detect a transition without adding more event hooks.

### Visual: bump border + add a "✓" overlay in the bottom-left
**Choice:** Selected choose cards get a thicker (3px → 4px) accent border, a stronger upward translate (4px → 6px), and a small "✓" glyph in the bottom-left corner (opposite the wild ★ which lives top-right). The ✓ is the dominant signal; border + lift are reinforcement.
**Why:** A glyph is unambiguous. Putting it opposite the wild badge means a card with both signals (e.g., a selected 5 in the choose pile) is visibly "both wild AND picked" — not confusing.

### `aria-pressed` toggle on each choose-card button
**Choice:** When rendering a selectable choose card, set `aria-pressed="false"` initially, and update to `"true"` when selected. Screen readers will announce the state.
**Why:** Currently the visual signal is the only signal; adding an ARIA attribute makes the selection state accessible without changing the DOM tree.

### Defensive Set reset in `lockInSetup()`
**Choice:** Already in place via `state.setupSelected.clear()` in `renderSetup` when `me.ready === true`. Keep it.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Phase tracking breaks if `state.phase` gets out of sync (e.g., a bug in another render path) | The transition logic is simple and reads only the view; worst case is a no-op reset, not a wrong-state render. |
| The "✓" glyph crowds small cards on mobile | The glyph is 0.55rem (matching the wild ★). At the smallest card size (54×78px) it still has ~10px of horizontal room. |
| A user expects their selection to survive a tab refresh | Out of scope; the existing behavior is "lose your selection on refresh," and this change doesn't alter it. |
| Screen-reader users get a verbose announcement (`"<rank> card — wild + reverse — selected"`) | The full description is already long; selection adds a single word. Acceptable. |

## Migration Plan

1. `static/app.js`: add `state.phase = null`; in `renderGame(view)`, track the transition and reset `state.setupSelected` on entry into setup when the user isn't already ready. Set `aria-pressed` on each choose-card button.
2. `static/styles.css`: bump `.choose-row .selected` border to 4px, lift to 6px, add a `::after` content `"✓"` positioned bottom-left.
3. `CHANGELOG.md`: `## [Unreleased]` gains a `### Fixed` bullet.
4. Commit + push + green CI + merge.

Rollback: revert the static-file changes; no server or persistence implications.

## Open Questions

- None — the only design call is the glyph position, settled as bottom-left.
