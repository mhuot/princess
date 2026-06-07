## Why

The project shipped with a "7-under" rule by mistake — the actual house rule is **5-under** (when the pile top is a 5, the next card must be UNDER 5). Beyond fixing the default, the rule's anchor rank should be configurable per room. Different friend groups play with different reverse ranks; the engine should treat the rank as data, not a constant.

Right now the engine hard-codes `REVERSE_CARD = 7` and `GameConfig.seven_on_seven` is the only knob. Both need to be parameterized.

## What Changes

- **Engine:** drop the `REVERSE_CARD = 7` module constant. Add `GameConfig.reverse_rank: int` (default **5**, valid 3–14) that controls which rank triggers the under rule. Rename `GameConfig.seven_on_seven` to `GameConfig.same_on_reverse` so the toggle generalizes. Update `is_legal_rank()` and `under_seven_active()` (renamed `under_reverse_active()`) to consult `config.reverse_rank` instead of the constant.
- **Frontend:** the rule indicator, the collapsible legend, the lobby "House rules" panel, and every tooltip currently reading "7"/"under 7"/"7-on-7" become **dynamic** — they read the rank from `view.config.reverse_rank` and the toggle name from `same_on_reverse`. The lobby panel's checkbox becomes:
  - **Reverse rank:** dropdown of legal ranks (3, 4, 5, 6, 7, 8, 9, J, Q, K, A) with 5 as the default.
  - **Allow same rank on reverse:** checkbox (was "Allow 7 on 7").
  - (Special-card rank entries for **2** and **10** remain pinned because they're wild — the dropdown excludes 2.)
- **Spec scenario names** in `game-engine` and `web-frontend` that hard-code "7" get parameterized (e.g. "7-on-7 → "same-on-reverse"). Existing 7-under examples become "reverse-rank examples (default 5)".
- **README + CHANGELOG:** every "7-under" reference becomes "**5-under** (configurable: see house rules)". CHANGELOG gets an `## [Unreleased]` entry naming the rule fix + new toggle.
- **`openspec/config.yaml` context:** the "house rules" paragraph names 5 as the default reverse rank, not 7.
- **Tests:** rename `test_seven_*` → `test_reverse_*` where appropriate; update assertions to use the configurable rank. Existing tests that exercise "8 illegal on 7" become "8 illegal on 5" by default; add a parameterized test exercising a non-default rank (e.g. K) to prove the config flows through.

This is a **breaking change** to the wire shape of `GameConfig` — old clients sending `seven_on_seven` get an unknown key (silently ignored) and inherit the new default. Acceptable because the project has no persistent rooms and no external API consumers.

## Capabilities

### Modified Capabilities

- `game-engine`: parameterize the reverse rule via `GameConfig.reverse_rank` and `GameConfig.same_on_reverse`; remove the `REVERSE_CARD` constant.
- `web-frontend`: rule indicator, legend, and lobby House-rules panel render dynamically from `view.config.reverse_rank` / `same_on_reverse`.
- `repository-meta`: README "House rule" section names the new default (5) and notes that the rank is configurable.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/game.py` — `GameConfig` field rename + new field, `is_legal_rank` + `under_seven_active` (renamed) consult config, `_choose_starter` no longer excludes a hard-coded 7.
  - `static/index.html` — lobby `<input type=checkbox>` for seven-on-seven becomes a `<select>` for reverse rank + a renamed checkbox. Card tooltip + legend rebuild from config.
  - `static/app.js` — `isLegalRank`, `renderLegend`, `renderConfigPanel`, `saveConfig`, `renderPile` rule indicator, `specialCardInfo`.
  - `static/styles.css` — minor: dropdown styling matches existing checkbox styling.
  - `tests/test_game.py` — rename + update assertions; add cross-rank parameterized test.
  - `tests/test_server.py` — config-endpoint test sends the new fields.
- **Affected APIs:**
  - `GameConfig.to_dict()` shape changes: `{"seven_on_seven": bool}` → `{"reverse_rank": int, "same_on_reverse": bool}`. `from_dict()` still silently drops unknown keys.
- **Affected dependencies:** none.
- **Docs touched:** `README.md` (rule callout + features list), `CHANGELOG.md` (`[Unreleased]`), `openspec/config.yaml` (context block).
- **Depends on:** all four archived changes plus the synced specs from each. No conflict with `show-last-three-moves` (still mid-apply at the frontend boundary; this change does not touch the status stack).
