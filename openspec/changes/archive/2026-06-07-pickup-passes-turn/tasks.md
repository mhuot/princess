## 1. Pre-conditions

- [x] 1.1 Confirm `baseline-princess-card-game` has been archived (so `openspec/specs/game-engine/spec.md` exists) — if not, archive it first or fold this delta into the baseline before archiving.

## 2. Regression tests (write first; they may already pass)

- [x] 2.1 In `tests/test_game.py`, add `test_pickup_advances_to_next_player_two_player` covering `Game.pickup` in a 2-player game and asserting `current_idx == 1`.
- [x] 2.2 Add `test_face_down_illegal_pickup_advances_turn` covering `Game._play_face_down` with an illegal blind reveal and asserting `current_player.pid == "p1"` afterward.
- [x] 2.3 Add `test_pickup_skips_finished_player` covering a 3-player game where `p1` is already finished; assert pickup by `p0` sets `current_player.pid == "p2"`.
- [x] 2.4 In `tests/test_ai.py` (or a new `tests/test_bot_pickup.py`), add a test that constructs a room-like scenario where a bot's `decide()` returns a play the engine will reject (e.g., by mutating the game state mid-decision is hard — instead, exercise `Game.pickup` directly with a bot pid and assert the turn advances). The bot path can be covered by an integration test if the unit test is awkward.

## 3. Run the tests

- [x] 3.1 Run `pytest tests/test_game.py -k pickup` and confirm green.
- [x] 3.2 Run the full suite (`pytest`) and confirm no other tests regress.

## 4. Fix engine if any regression test fails

- [x] 4.1 If `test_pickup_advances_to_next_player_two_player` fails, inspect `Game.pickup` — ensure it calls `self._advance_turn()` after clearing the pile. _(N/A — test passed; engine already complied.)_
- [x] 4.2 If `test_face_down_illegal_pickup_advances_turn` fails, inspect `Game._play_face_down` — ensure the illegal-reveal branch advances the turn. _(N/A — test passed.)_
- [x] 4.3 If `test_pickup_skips_finished_player` fails, inspect `Game._advance_turn` — ensure the loop skips `finished` players. _(N/A — test passed.)_
- [x] 4.4 If the bot path test fails, inspect `Room.run_bots` — ensure the force-pickup fallback routes through `Game.pickup` (which advances the turn) and not a path that retains the bot as current. _(N/A — `Game.pickup` exercised directly with a "bot" pid; turn advanced as expected.)_

## 5. Optional clarifying touch-ups (only if helpful)

- [x] 5.1 Add a one-line comment in `Game.pickup` reading `# Pickup ends the picker's turn — see game-engine spec.` to keep the rule discoverable from the code.
- [x] 5.2 Add the same comment in `Game._play_face_down` just above the illegal-reveal `_advance_turn()` call.

## 6. Spec + change wrap-up

- [x] 6.1 Verify the MODIFIED requirement in `openspec/changes/pickup-passes-turn/specs/game-engine/spec.md` resolves cleanly against the archived baseline. _(verified via `openspec validate pickup-passes-turn --strict`)_
- [x] 6.2 Run `openspec status --change pickup-passes-turn` and confirm all artifacts are done. _(4/4 artifacts complete)_
- [x] 6.3 Archive this change via `/opsx:archive` once tests are green and reviewer sign-off is in.
