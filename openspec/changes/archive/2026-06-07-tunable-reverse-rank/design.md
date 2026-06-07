## Context

The engine treats one rank as special-and-named ("reverse") via the `REVERSE_CARD = 7` constant. Every legality decision, the `GameConfig.seven_on_seven` toggle, the pile-top check in `under_seven_active()`, and the frontend's rule indicator all bake the number 7 into the code path. Changing the rank means changing the constant and many string-literal "7"s in the UI.

The fix is to move the rank into `GameConfig` and let everything downstream read it. The frontend already reads `view.config` for the existing seven-on-seven toggle; the same plumbing works for a rank.

## Goals / Non-Goals

**Goals:**
- Make the reverse rank a per-room config knob (default 5).
- Make the "same-on-reverse" allowance a generic toggle, decoupled from the literal number 7.
- Update every user-visible mention of the rank to read dynamically from the config.
- Update README + CHANGELOG so the front-door description matches reality.
- Keep the engine's wild cards (2 reset, 10 burn) untouched — those rules are not currently configurable and don't need to be.

**Non-Goals:**
- Generalize the wild reset (2) or burn (10) into config knobs. They've never been variant rules in this project; if they ever need to change, that's a follow-on change.
- Backward-compatibility shim for the old `seven_on_seven` key. Rooms have no persistence; old clients that send the old key will just inherit the new default.
- Multi-rank reverse (e.g. "both 5 and 7 trigger under"). Out of scope; one rank.
- Renaming the spec files or capabilities. We MODIFY existing requirements in place.

## Decisions

### Field names: `reverse_rank` (int) + `same_on_reverse` (bool)
**Choice:** `reverse_rank` carries an integer rank (2–14, but constrained to 3–14 because 2 is wild). `same_on_reverse` is the generic boolean that replaces `seven_on_seven`.
**Why:** Reads cleanly as code (`if rank == config.reverse_rank`). The boolean's name no longer lies if someone sets `reverse_rank = K`.
**Alternative considered:** "Reverse" as a card label (`config.reverse = "5S"`) — over-precise; the rule cares about rank only.
**Trade-off:** `reverse_rank = 2` would be incoherent (2 is wild). The setter validates against `3 <= rank <= 14` and falls back to 5 on invalid input.

### Default = 5
**Choice:** `GameConfig.reverse_rank: int = 5`. The user's actual house rule.
**Why:** Self-documenting; fixes the original bug.

### `under_seven_active()` → `under_reverse_active()`
**Choice:** Rename the helper. Internally checks `top_rank() == self.config.reverse_rank`.
**Why:** Method name follows the rule, not a magic number.

### Frontend rank labels use the existing `_RANK_LABEL` map
**Choice:** The pile area's rule indicator and the legend use the existing `J/Q/K/A` substitution for ranks ≥ 11. Dropdown options show the same labels.
**Why:** Reuses the engine's source of truth for rank text. No duplication on the client.

### Dropdown excludes 2 and 10 (and J/Q/K/A?)
**Choice:** The dropdown lists 3, 4, 5, 6, 7, 8, 9, J, Q, K, A. Default selection: 5. (Excludes 2 — wild reset — and 10 — burn — because picking them would create rule conflicts. The engine validates redundantly.)
**Why:** Keeps the picker honest. Even if someone curl-POSTs `reverse_rank = 2`, the engine rejects (falls back to 5) and the UI never offers it.

### Engine validates incoming config; falls back silently
**Choice:** `GameConfig.from_dict()` validates `reverse_rank ∈ {3, 4, 5, 6, 7, 8, 9, J(11), Q(12), K(13), A(14)}`. Invalid → drop to the field's default (5). No exception bubbles to the server.
**Why:** Matches the existing forward-compatibility behavior (unknown keys silently ignored). A bad value should never crash a room.

### Spec deltas: MODIFY in place, don't introduce parallel requirements
**Choice:** Each of the three affected capabilities (`game-engine`, `web-frontend`, `repository-meta`) gets a MODIFIED requirement that supersedes the existing "7-under" worded one. Sync produces a single canonical version per requirement.
**Why:** Avoids spec drift where two requirements describe the same behavior with different wording.

### Frontend tooltips: still call out the *specific* rank a player is hovering
**Choice:** The hover tooltip on a card of rank R says "Reverse — next card must be UNDER R" only when R equals the room's `reverse_rank`. Otherwise the standard label tooltip applies.
**Why:** A 7 in a 5-under room isn't reverse; tooling shouldn't lie.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Old `seven_on_seven` config in test fixtures + URLs break silently | `from_dict()` already ignores unknown keys; new defaults are sane. Tests that asserted `seven_on_seven` get updated. |
| User picks `reverse_rank = 10` and breaks the burn rule | Dropdown excludes 10; server-side validation falls back to default if someone bypasses the UI. |
| Frontend "5-under (or another 5)" reads awkwardly for ace-reverse rooms | Pluralization isn't an issue — using the rank label keeps copy stable: "play UNDER A (or another A)". Acceptable. |
| 7 was a fun visual anchor in the README; switching to 5 loses some of that | The README still has the card art row; the rule callout just names 5 instead of 7. Same energy. |
| `show-last-three-moves` is mid-apply (engine done, frontend pending) and also touches `game-engine` spec | Different requirements; this change MODIFIES the legality rule, that change MODIFIES the player-scoped view. No overlap. Land either order. |
| CI fails because we forgot a string-literal "7" somewhere | Grep for `\b7\b` in `static/` and `princess/` before pushing; allow only intended matches (rank-7 cards, not the rule). |

## Migration Plan

1. Engine: add `reverse_rank` + `same_on_reverse` to `GameConfig`; drop `seven_on_seven`. Validate in `from_dict()`.
2. Engine: remove `REVERSE_CARD` constant; rename `under_seven_active` → `under_reverse_active`; update `is_legal_rank` to use `self.config.reverse_rank`.
3. Tests: rename + update assertions; add a parameterized test that exercises a non-5 rank.
4. Frontend: dynamic rule indicator + tooltip + legend + lobby panel (replace checkbox with select + new checkbox).
5. Docs: README rule callout, CHANGELOG `[Unreleased]`, `openspec/config.yaml` context.
6. Commit per task, push, watch CI green.

Rollback: revert the engine change; the frontend tolerates the absence of `reverse_rank` by defaulting to 5 in its dynamic rendering.

## Open Questions

- Should the rank dropdown include face cards? Default proposes yes (J–A). Confirm if 11–14 feels excessive. Leaning yes — better to allow the variant than not.
- Should we add a "no reverse rule" option (disable entirely)? Cleaner: treat `reverse_rank = 0` (or `None`) as off. Punting unless asked; out of scope for the current ask.
