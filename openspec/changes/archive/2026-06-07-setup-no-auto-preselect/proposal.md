## Why

In the setup phase, the user observed cards appearing pre-selected for human seats — i.e., the choose pile renders with one or more cards already marked as picked before the human has clicked anything. Humans should always start setup with zero selections; the host clicked Start, the deal happened, the human's job is to pick three from six. Anything that visually says "we picked some for you" undermines the choice.

A quick code read shows the engine doesn't auto-pick face-up for humans (only `seat.is_bot == True` triggers `_auto_pick_bot_face_up`), and `renderSetup` only highlights indices in `state.setupSelected`, which starts empty. The bug is likely one of:

- **State leakage across rounds:** `state.setupSelected` persists across rematches in some path; if it wasn't cleared after the previous lock-in, indices from the prior round would highlight cards in the new deal.
- **Visual collision:** the gold ★ corner badge on wild-rank cards (2, 10, reverse rank) is being read as "selected" — especially on a smaller screen where the lift + border of the actual selected state isn't obvious.

This change addresses both: explicitly reset `state.setupSelected` whenever the phase transitions into setup, and tighten the selected-vs-special visual distinction so they can't be confused.

## What Changes

- **Frontend behavior change (defensive reset):** when `renderGame()` routes into the setup branch (`view.phase === "setup"`), it SHALL reset `state.setupSelected` to an empty Set if the player is not currently locked in (`!view.you.ready`). This kills any leftover state from a prior round, a stale view, or a refresh.
- **Frontend visual change (tighten selected state):** the `.selected` style on choose cards SHALL be visually distinct from the gold ★ wild badge — a thicker accent border, a clear lift, and a separate "selected" overlay (e.g., a small "✓" or "Picked" tag in the opposite corner from the wild ★). Keyboard users see the same selected indicator via `aria-pressed` on the card buttons.
- **Frontend spec scenarios:** add scenarios under the existing setup-phase rendering requirement that explicitly assert "no card is marked selected on initial render" and "selection is cleared on phase transition into setup."
- **Server unchanged:** the engine and server already do the right thing; no API change.
- **Docs:** no doc surface change beyond the CHANGELOG (`Fixed` bullet).

## Capabilities

### Modified Capabilities

- `web-frontend`: tighten the setup-phase rendering requirement — explicit empty-on-render and reset-on-phase-transition rules; selected and wild visuals must not collide.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/app.js` — `renderGame()` resets `state.setupSelected` on setup entry when `!view.you.ready`; `renderSetup()` already iterates `state.setupSelected` (no change needed beyond reading the freshly-emptied Set).
  - `static/styles.css` — sharpen `.choose-row .selected` (thicker border, clearer lift) and add a `.selected::before` or `::after` ✓ glyph in the corner opposite the wild ★.
  - Optional: small `aria-pressed` toggle on each choose card button for screen-reader clarity.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` gains a `### Fixed` bullet ("Setup phase no longer renders any card as preselected; reset on phase transition.").
- **Depends on:** none beyond main.
- **Out of scope:** changing the auto-pick behavior for bots (still on); adding a "skip setup" host option (separate change if desired); persisting the user's selection across page refresh.
