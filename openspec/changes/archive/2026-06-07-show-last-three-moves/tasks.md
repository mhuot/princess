## 1. Pre-conditions

- [x] 1.1 Confirm `baseline-princess-card-game` is archived (so the MODIFIED game-engine + web-frontend specs resolve cleanly). If not, archive it or fold this change in.

## 2. Engine: introduce bounded `last_actions`

- [x] 2.1 In `princess/game.py`, replace the `last_action: str` instance attribute with `last_actions: list[dict]` initialized to `[]`.
- [x] 2.2 Add a private helper `Game._record(text: str, *, actor_pid: str | None = None, burned: bool = False, picked_up: bool = False, finished_pid: str | None = None)` that appends to `last_actions` and pops the head when the list grows past 3.
- [x] 2.3 Replace every `self.last_action = "..."` site with a `self._record(...)` call carrying the appropriate flags. Sites: `_deal_with_swap` (deal), `set_face_up` (ready + deal-complete), `_apply_committed_cards` (play/burn/finish), `_play_face_down` (illegal flip + pickup), `pickup` (voluntary pickup).
- [x] 2.4 Update `Game.public_state()` to emit `"last_actions"` (the list) and a legacy `"last_action"` string equal to `last_actions[-1]["text"]` when non-empty, else `""`.

## 3. Engine tests

- [x] 3.1 In `tests/test_game.py`, add `test_last_actions_starts_empty_then_records_deal_complete` — fresh `swap_phase=True` game, after the last `set_face_up`, assert the list length is 1 and its `text` matches the deal-complete message.
- [x] 3.2 Add `test_last_actions_caps_at_three` — drive 4 play+pickup events in a row, assert `len == 3` and the first event is no longer present.
- [x] 3.3 Add `test_last_actions_burn_flag_on_ten` — play a 10, assert the newest entry has `burned == True`.
- [x] 3.4 Add `test_last_actions_burn_flag_on_four_of_a_kind` — complete a 4-of-a-kind across plays, assert `burned == True`.
- [x] 3.5 Add `test_last_actions_pickup_flag_voluntary` — voluntary pickup, assert `picked_up == True`.
- [x] 3.6 Add `test_last_actions_pickup_flag_face_down_illegal` — face-down illegal flip, assert `picked_up == True`.
- [x] 3.7 Add `test_last_actions_finished_pid_set` — final card play that finishes a player, assert `finished_pid == that player's pid`.
- [x] 3.8 Add `test_last_action_legacy_key_matches_newest_text` — assert `public_state()["last_action"] == last_actions[-1]["text"]`.

## 4. Update existing tests that reference `last_action`

- [x] 4.1 Grep `tests/` for `last_action`. Replace any assertions on the string with assertions on `last_actions[-1]["text"]` (or keep the legacy key — both work).
- [x] 4.2 Run the full pytest suite — expect green.

## 5. Frontend: status stack

- [x] 5.1 In `static/index.html`, rename `#status-line` to `#status-stack` (keeping it inside the same parent) and remove the old `aria-live` from the container; nested `.status-entry` elements will carry their own `aria-live` / `aria-hidden`.
- [x] 5.2 In `static/styles.css`, replace `.status-line` styling with `.status-stack` (column flex, gap) and `.status-entry` (rounded, accent border) with a `.status-entry.dim` variant for older entries. Use `prefers-reduced-motion` to skip any opacity transitions.
- [x] 5.3 In `static/app.js`, replace `renderStatus(view)` with one that:
  - Reads `view.last_actions` (array). Falls back to a single-element array constructed from `view.last_action` (string) when `last_actions` is missing.
  - Renders each entry into its own `.status-entry`. The newest carries `aria-live="polite"`, includes the turn suffix, and shows burn/pickup/finish glyphs based on flags. Older entries get `.dim` and `aria-hidden="true"`.
  - Glyph rules: `burned` → trailing 🔥; `picked_up` → trailing ↑; `finished_pid` → 👑 plus the finishing player's display name (look up via `view.players`).

## 6. Frontend smoke

- [x] 6.1 Start the server (`python -m princess`), play a hand against two bots, and confirm the status stack shows up to three entries during the bot turn chain.
- [x] 6.2 Pop the legend, change the 7-on-7 toggle, restart a round — confirm the deal-complete entry is the first line after each new round.
- [x] 6.3 Tab through with keyboard; confirm only the newest entry is announced by screen reader (use VoiceOver or NVDA).

## 7. Wrap up

- [x] 7.1 Run `openspec status --change show-last-three-moves` and confirm 4/4 artifacts done. _(verified)_
- [x] 7.2 Archive the change via `/opsx:archive` after smoke + spec review.
