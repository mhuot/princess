## Why

The reverse rank (default 5) currently has to satisfy normal rank legality to be played — i.e., a 5 is illegal on a K. But conceptually it's a special-rule card just like the 2 and the 10. The user wants the reverse rank to behave like any other wild: **always legal regardless of pile top**, with the existing side-effect (the next play must be UNDER that rank) intact.

This also simplifies the rule set. Today there are *two* dials around the reverse rank — `reverse_rank` (the integer rank itself) and `same_on_reverse` (whether the rank is legal on itself). The wild semantics make the second knob redundant: if 5 is always legal, then 5-on-5 is always legal, no checkbox needed.

## What Changes

- **Engine:** `Game.is_legal_rank(rank)` SHALL treat `rank == config.reverse_rank` as always legal, just like ranks 2 and 10. The under-rank rule still fires after the card lands (so the *next* play is constrained as today).
- **`GameConfig.same_on_reverse` is removed.** Its semantics are subsumed by the wild rule. `from_dict()` keeps ignoring the legacy key silently for forward-compatibility.
- **Frontend:**
  - Rule indicator: the suffix `"(or another <R>)"` becomes informational only — the rank's always-wild status means the suffix is always true. We keep the suffix in the indicator text because it's the player-relevant detail at the moment of choice.
  - Legend: the reverse entry now reads `"Reverse — always legal; the next card must be UNDER <R>."`
  - Lobby: remove the **Allow same rank on reverse** checkbox; keep only the **Reverse rank** dropdown. The config endpoint accepts (and silently drops) `same_on_reverse` for forward compat.
  - Hover tooltip on a reverse-rank card: `"Wild + Reverse — always legal; next play must be UNDER <R>."`
- **README + CHANGELOG:** clarify the reverse rank's wild status alongside the 2 and 10.
- **`openspec/config.yaml` context:** drop the same-on-reverse note; describe the reverse rank as the *third* wild.

## Capabilities

### Modified Capabilities

- `game-engine`: `is_legal_rank` makes the reverse rank wild; drops `GameConfig.same_on_reverse`.
- `web-frontend`: rule indicator wording, lobby panel (one fewer control), tooltip, and legend reflect the wild status.
- `repository-meta`: README section names the three wilds (2, 10, reverse rank).

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/game.py` — `GameConfig` field removal, `is_legal_rank` adds reverse-rank-is-wild branch, `from_dict` drops the validation of `same_on_reverse`.
  - `static/app.js` — `isLegalRank()` adds the wild branch; legend and tooltip text; `renderConfigPanel`/`saveConfig` drop the second control.
  - `static/index.html` — remove the `<input id="cfg-same-on-reverse">` row from the lobby.
  - `static/styles.css` — no change.
  - `tests/test_game.py` — drop `test_same_on_reverse_*`; add `test_reverse_rank_is_wild` (3 scenarios: reverse on K, reverse on 7, reverse on empty pile).
  - `tests/test_server.py` — update `test_config_*` to stop sending `same_on_reverse`.
  - `README.md`, `CHANGELOG.md`, `openspec/config.yaml`.
- **Affected APIs:**
  - `GameConfig.to_dict()` no longer emits `same_on_reverse`. Old clients ignoring extras don't break; new clients should drop it from their config dialogs.
- **Docs touched:** README, CHANGELOG, `openspec/config.yaml`.
- **Depends on:** archived `tunable-reverse-rank` (which introduced `reverse_rank`). No conflicts; this change MODIFIES the same three capabilities cleanly.
- **Out of scope:** changing the burn (10) or reset (2) semantics; adding a "no reverse rule at all" toggle (separate change if desired); the legacy `under_seven` alias in `view_for()` stays for one more release.
