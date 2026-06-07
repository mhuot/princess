## 1. Pre-conditions

- [x] 1.1 Confirm the `show-last-three-moves` change either landed or remains on a separate branch — this change does not touch the status stack, but the `game-engine` spec is now jointly modified by both.
- [x] 1.2 Branch from main: `git switch -c change/tunable-reverse-rank`.

## 2. Engine changes (`princess/game.py`)

- [x] 2.1 Remove the `REVERSE_CARD = 7` module constant.
- [x] 2.2 Add `GameConfig.reverse_rank: int = 5` and `GameConfig.same_on_reverse: bool = True`; drop `seven_on_seven`. Add validation in `from_dict()` — `reverse_rank` must be in `{3,4,5,6,7,8,9,11,12,13,14}`, otherwise coerce to 5.
- [x] 2.3 Rename `under_seven_active()` → `under_reverse_active()`; have it check `self.top_rank() == self.config.reverse_rank`.
- [x] 2.4 Update `is_legal_rank()`: replace the hard-coded `REVERSE_CARD` and `config.seven_on_seven` references with `self.config.reverse_rank` and `self.config.same_on_reverse`.
- [x] 2.5 `_choose_starter()` already excludes 2 and 10 (wild/burn). No change needed; the function does not care about the reverse rank.
- [x] 2.6 `public_state()` already emits `config.to_dict()` — confirm the new shape includes both `reverse_rank` and `same_on_reverse`.

## 3. Engine tests (`tests/test_game.py`)

- [x] 3.1 Rename `test_seven_forces_next_play_under_seven` → `test_reverse_rank_forces_next_play_under_default_5`; update assertions to use rank 5.
- [x] 3.2 Rename `test_seven_under_allows_lower_cards` similarly; use 3 on 5.
- [x] 3.3 Rename `test_seven_under_still_allows_10_burn` → `test_burn_legal_over_reverse_rank`; use 5 as pile top.
- [x] 3.4 Rename `test_seven_under_still_allows_2_reset` → `test_reset_legal_over_reverse_rank`; use 5 as pile top.
- [x] 3.5 Replace `test_seven_on_seven_legal_by_default` (if present) with `test_same_on_reverse_legal_by_default` exercising a 5 on a 5.
- [x] 3.6 Add `test_reverse_rank_configurable` — parameterized over a few non-default ranks (e.g., 4, 9, K) and asserts the engine respects whichever rank the config carries.
- [x] 3.7 Add `test_reverse_rank_invalid_coerces_to_default` — pass `{"reverse_rank": 10}`, expect 5.
- [x] 3.8 Add `test_legacy_seven_on_seven_key_ignored` — pass `{"seven_on_seven": false}`, expect defaults.

## 4. Server tests (`tests/test_server.py`)

- [x] 4.1 Find `test_config_updates_seven_on_seven` and rewrite as `test_config_updates_reverse_rank`. POST `{"reverse_rank": 13, "same_on_reverse": false}`. Assert the room's `game.config` reflects both values.
- [x] 4.2 Update `test_config_ignores_unknown_keys` to send the new fields plus an unknown one.

## 5. Frontend (`static/app.js`)

- [x] 5.1 In `isLegalRank()`: replace the 7-specific branch with `view.config.reverse_rank`; legal iff `rank < reverse_rank` (special cases: 2 and 10 always legal, `rank === reverse_rank` legal iff `view.config.same_on_reverse`).
- [x] 5.2 In `renderPile()`: render the rule indicator dynamically using `view.config.reverse_rank` (via a `_RANK_LABEL`-equivalent lookup in JS — add a small `rankLabel(rank)` helper if missing).
- [x] 5.3 In `renderLegend()`: replace the 7 entry's static text with `"Reverse — next card must be UNDER <R>"`. Add the same-rank-allowed suffix when `same_on_reverse` is true.
- [x] 5.4 In `specialCardInfo(rank, config)` (rename to accept config): return the reverse-rule string only when `rank === config.reverse_rank`. The 2 and 10 strings are unchanged.
- [x] 5.5 Audit every other call site that uses literal `7` for rule logic; update to use config.

## 6. Frontend (`static/index.html`, `static/styles.css`)

- [x] 6.1 Replace `<input id="cfg-seven-on-seven" type="checkbox">` (and its label) with two controls:
  - `<select id="cfg-reverse-rank">` with options for 3, 4, 5, 6, 7, 8, 9, J(11), Q(12), K(13), A(14). Default selected: 5.
  - `<input id="cfg-same-on-reverse" type="checkbox">` (default checked).
- [x] 6.2 Add CSS for the `<select>` matching the existing checkbox styling. Keep the layout in `#config-panel` consistent.
- [x] 6.3 In `renderConfigPanel(room)`: populate the dropdown with `room.config?.reverse_rank` (fallback 5); set the checkbox per `room.config?.same_on_reverse` (fallback true). Disable both when not host.
- [x] 6.4 Replace the `saveConfig` handler: collect both fields, POST `{"reverse_rank": <int>, "same_on_reverse": <bool>}`.
- [x] 6.5 Add event listeners for both `change` events (dropdown + checkbox).

## 7. Docs

- [x] 7.1 Update `README.md`: replace every "7-under" mention with "5-under (default)" and add a sentence noting per-room configurability. The card-art row stays as is (visual flavor).
- [x] 7.2 Append to `CHANGELOG.md` `## [Unreleased]`: a bullet under `### Changed` ("Reverse-rank rule now defaults to 5, was 7; configurable per room via House rules panel") and a bullet under `### Removed` ("`GameConfig.seven_on_seven` field; replaced by `reverse_rank` and `same_on_reverse`").
- [x] 7.3 Update `openspec/config.yaml` `context:` — change the house-rules paragraph to name 5 as the default and note configurability.

## 8. Verify locally

- [x] 8.1 `black princess tests`
- [x] 8.2 `pylint princess tests` — expect 10.00/10.
- [x] 8.3 `pytest -q` — expect green.
- [x] 8.4 `openspec validate --specs --strict` and `openspec validate tunable-reverse-rank --strict`.
- [x] 8.5 `python -m princess`; manual smoke: lobby dropdown changes the rule indicator; default game is 5-under; setting reverse rank to K mid-lobby and starting a new round makes K-on-K legal.

## 9. Commit + push (one commit per task in 2.x–7.x)

- [ ] 9.1 Commits per the project convention (`tunable-reverse-rank: <task title>`). Group small related edits when one task spans multiple files; do not flatten across tasks.
- [ ] 9.2 Push the branch.
- [ ] 9.3 Watch the three CI workflows (tests, lint, openspec). Fix any red.
- [ ] 9.4 Open a PR using the PR template; link this change folder; confirm the docs-touched section names `README.md`, `CHANGELOG.md`, and `openspec/config.yaml`.
- [ ] 9.5 Squash-merge into `main` once green.

## 10. Wrap up

- [ ] 10.1 Run `openspec status --change tunable-reverse-rank` and confirm 4/4 artifacts done.
- [ ] 10.2 `/opsx:archive tunable-reverse-rank` once merged and CI green.
