## Why

The pickup-pile rule was specified loosely in the baseline ("advance the turn") and the user observed (or fears) ambiguous behavior in play: after a player picks up the pile, the **next** player — not the picker — should play the first card on the now-empty discard pile. This change tightens the spec and adds regression coverage so the engine, the bot loop, and the face-down "illegal flip" path can never accidentally let the picker keep playing.

A quick code-read suggests the existing engine already advances the turn correctly on every pickup path. Treat this change as a "codify + verify" pass: write the explicit requirements, add tests that would fail if a regression slipped in, and confirm there's no hidden case (e.g., burns, replays, or bot-fallback pickups) where the picker stays current.

## What Changes

- Tighten the `game-engine` spec's pickup behavior to explicitly say the **next non-finished player** becomes current and plays the first card on the fresh empty pile.
- Add spec scenarios for:
  - Voluntary `pickup()` from hand context (already covered, kept).
  - The face-down illegal-flip path that picks up pile + revealed card.
  - The bot's force-pickup fallback when `decide()` returns an action the engine rejects.
  - A pickup that leaves only finished players between the picker and the next active player (turn must skip them).
- Add regression tests covering the same scenarios.
- Add a single defensive engine assertion or comment if any path is found that does not advance the turn (none expected — see Design).

Not a breaking change for clients, since the wire protocol and state shape are unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `game-engine`: tighten the **Voluntary pickup** requirement and add scenarios for face-down illegal pickup and bot force-pickup fallback.

## Impact

- **Affected code:** `princess/game.py` (`pickup`, `_play_face_down`) — likely no logic changes; possibly a clarifying comment. `tests/test_game.py` gains regression cases.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Depends on:** baseline-princess-card-game change being archived first so the MODIFIED requirement can resolve cleanly. If still unarchived at apply time, fold the deltas into the baseline before archiving.
