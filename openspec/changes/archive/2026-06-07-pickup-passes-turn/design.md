## Context

Pickup happens in three places in the engine:

1. **`Game.pickup(pid)`** — voluntary pickup invoked when a human or bot decides not to (or can't) play. Already calls `_advance_turn()` after clearing the pile into the player's hand.
2. **`Game._play_face_down(player, idx, card)`** — when face-down is the active source and the blind reveal is illegal. Picks up the pile plus the revealed card and calls `_advance_turn()`.
3. **`Room.run_bots()`** — when the bot's `decide()` returns an action the engine rejects, the server force-calls `self.game.pickup(current.pid)`. This routes through path (1).

`_advance_turn()` cycles `current_idx` forward, skipping any player marked `finished`, so the next active player gets the turn. The engine assigns `current_idx` from this; `view_for()` exposes the picker as no-longer-current and the next player as current.

The frontend renders `view.current_pid` and the rule indicator from the pile top — both fall out for free once the engine advances correctly.

## Goals / Non-Goals

**Goals:**
- Make the rule unambiguous in the spec: pickup ends the picker's current turn; the next non-finished player plays the next card on the empty pile.
- Hold every pickup path to the same rule — including the face-down illegal-flip path and the bot force-pickup fallback.
- Catch regressions cheaply via three new tests.

**Non-Goals:**
- Penalty turns (e.g., picker also skips their next turn) — not part of the house rules.
- Pickup-only-some-cards variants. The pile is taken whole.
- UI changes. The current status line already names the next player; no new affordances needed.

## Decisions

### Codify in spec, verify in tests, only change code if a regression surfaces
**Choice:** Treat the change primarily as documentation + tests. Touch `princess/game.py` only if a regression test fails.
**Why:** Static reading shows all three pickup paths already advance the turn. Writing the spec and tests first prevents accidental rework and gives us a fail-fast signal if any path drifts.

### MODIFY the baseline `game-engine` requirement, don't add a new one
**Choice:** Edit the existing **Voluntary pickup** requirement to add scenarios, rather than introducing a parallel requirement.
**Why:** A new requirement would fragment the rule. The MODIFIED delta preserves the rule's single home and keeps the spec searchable.

### Three test cases, not one
**Choice:** Add separate regression tests for each pickup path: voluntary `pickup()`, face-down illegal flip, and bot force-pickup fallback.
**Why:** The three paths use different code routes; one test wouldn't catch a regression in another path. The tests are cheap.

### Skip-over-finished verification with a 3-player test
**Choice:** Add a test where one player is finished and verify pickup skips them.
**Why:** `_advance_turn()` already handles this, but the scenario isn't covered today — and "the next player" needs to mean "the next active player" so the rule survives end-game shrinkage.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Baseline change not yet archived when this is applied — MODIFIED delta can't be resolved | Apply this change after archiving baseline, or fold the deltas into the baseline pre-archive. |
| Some future change introduces "play again on pickup" as a house-rule toggle | A new toggle would override this requirement; document the dependency in that change's proposal. |
| Tests pass but a UI path lets the picker click "Play selected" after pickup | UI already gates buttons on `view.you.your_turn`, which is server-derived. Out of scope but worth a manual smoke test. |

## Migration Plan

1. Land this change after `baseline-princess-card-game` is archived.
2. Run the new tests; expect green if the existing engine already advances correctly.
3. If any test fails, the failure pinpoints the broken path — fix in `princess/game.py`.
4. Archive this change.

Rollback is trivial: revert the spec MODIFICATION and the test additions.
