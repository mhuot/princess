## 1. Pre-conditions

- [ ] 1.1 Confirm main has the merged tunable-reverse-rank specs (it does — verified via `openspec validate --specs --strict`).
- [ ] 1.2 Branch: `git switch -c change/reverse-rank-is-wild`.

## 2. Engine

- [ ] 2.1 In `princess/game.py` `GameConfig`, remove the `same_on_reverse: bool` field. Keep `reverse_rank: int = 5`.
- [ ] 2.2 In `GameConfig.from_dict`, drop the handling of `same_on_reverse` (unknown keys are already silently ignored).
- [ ] 2.3 In `Game.is_legal_rank()`, extend the wild branch: legal if `rank in (WILD_RESET, BURN_CARD) or rank == self.config.reverse_rank`. The existing under-rule branch stays unchanged (`rank < self.config.reverse_rank`).
- [ ] 2.4 Verify `under_reverse_active()` is unchanged — it just checks whether the pile top equals the reverse rank.

## 3. Engine tests

- [ ] 3.1 Remove `test_same_on_reverse_legal_by_default` and `test_same_on_reverse_illegal_when_toggle_off` from `tests/test_game.py` (the second one referenced the now-gone field; the first is subsumed by the new wild test).
- [ ] 3.2 Add `test_reverse_rank_is_wild` parameterized over pile tops `[None, 5, 7, 13, 14]` and assert the reverse-rank card plays cleanly on each.
- [ ] 3.3 Update `test_reverse_rank_configurable` if it depended on `same_on_reverse` — it shouldn't, but double-check the parameterized cases (the `(reverse, top, attempt, expected_ok)` tuples that rely on `same_on_reverse` semantics need re-thinking).
- [ ] 3.4 Update `test_reverse_rank_invalid_coerces_to_default` to only assert `reverse_rank` (drop the assertion that `same_on_reverse is True`).
- [ ] 3.5 Update `test_legacy_seven_on_seven_key_ignored` similarly.

## 4. Server tests

- [ ] 4.1 In `tests/test_server.py::test_config_updates_reverse_rank`, drop `same_on_reverse` from the POST body and from the assertion (only `reverse_rank` should round-trip).
- [ ] 4.2 In `test_config_ignores_unknown_keys`, keep sending `same_on_reverse` (as part of the "unknown legacy" set) and assert it's NOT in the returned config.

## 5. Frontend JS

- [ ] 5.1 In `static/app.js`, in `isLegalRank(rank, view)`: extend the wild check to include `rank === reverseRankOf(view)`.
- [ ] 5.2 In `specialCardInfo(rank, view)`: when `rank === reverseRankOf(view)`, return `"Wild + Reverse — always legal; next play must be UNDER <R>."`
- [ ] 5.3 In `renderLegend(view)`: change the reverse entry body to `"Always legal; the next card must be UNDER <R>."` (drop the conditional `sameSuffix`).
- [ ] 5.4 In `renderConfigPanel(room)`: drop the same-on-reverse checkbox handling. Keep the reverse-rank dropdown handling.
- [ ] 5.5 In `saveConfig()`: drop `same_on_reverse` from the POST body. Just send `{ reverse_rank: <int> }`.
- [ ] 5.6 In the DOM-ready handler: remove the `addEventListener("change", saveConfig)` line for `cfg-same-on-reverse`.
- [ ] 5.7 In `renderPile()`: the rule indicator suffix `"(or another R)"` is now always shown — drop the `same_on_reverse` conditional in favor of a single string.

## 6. Frontend HTML

- [ ] 6.1 In `static/index.html`, remove the `<label class="rule-row">` row containing `<input type="checkbox" id="cfg-same-on-reverse" />`. Keep the row with the dropdown.

## 7. Docs

- [ ] 7.1 In `README.md`, in the reverse-rank section: drop the toggle sentence; list **three** wild ranks (2 / 10 / reverse rank) instead of two. Note that the reverse rank is always legal AND triggers the under-rule.
- [ ] 7.2 In `CHANGELOG.md` under `## [Unreleased]`, add bullets under `### Changed` ("Reverse rank is now always legal, like 2 and 10; the under-rule still fires when it lands") and `### Removed` ("`GameConfig.same_on_reverse` field; subsumed by the wild rule. Same-on-reverse lobby checkbox removed.").
- [ ] 7.3 In `openspec/config.yaml` `context:`, update the reverse-rank paragraph to call out the three wilds explicitly and drop the `same_on_reverse` mention.

## 8. Verify locally

- [ ] 8.1 `black princess tests`
- [ ] 8.2 `pylint princess tests` — expect 10.00/10.
- [ ] 8.3 `pytest -q` — expect green.
- [ ] 8.4 `openspec validate --specs --strict` and `openspec validate reverse-rank-is-wild --strict`.
- [ ] 8.5 Manual smoke: restart the server, open the lobby, see only the dropdown (no checkbox). Start a round. Play a 5 onto a K — succeeds. Play an 8 onto the resulting 5 — rejected.

## 9. Ship

- [ ] 9.1 One commit per task (or batched logical commits if scopes overlap), message `reverse-rank-is-wild: <task title>`.
- [ ] 9.2 Push the branch; open a PR using the template.
- [ ] 9.3 Watch CI; fix anything red.
- [ ] 9.4 Squash-merge into main once green.

## 10. Wrap up

- [ ] 10.1 Run `openspec status --change reverse-rank-is-wild` — confirm 4/4 artifacts done.
- [ ] 10.2 `/opsx:archive reverse-rank-is-wild` after merge.
