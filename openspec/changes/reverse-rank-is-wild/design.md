## Context

After `tunable-reverse-rank`, the engine knows about three special ranks:

- **2** — always legal, resets the pile semantically (the next legal play is anything `≥ 2`, which is everything).
- **10** — always legal, burns the pile.
- **Reverse rank** (default 5) — must satisfy `≥ pile top` to be played, *and* activates the under-rule when it lands. A boolean `GameConfig.same_on_reverse` controls whether the rank is legal on itself.

The asymmetry is awkward: 2 and 10 are wild, but the reverse rank — also a "named" rule card — isn't. The user wants the reverse rank to join the wild family.

## Goals / Non-Goals

**Goals:**
- The reverse rank is **always legal**, regardless of pile top.
- The under-rule still fires when the card lands.
- The rule set gets *simpler* (one fewer config knob).
- Frontend wording matches reality: the reverse rank is described alongside the other two wilds.

**Non-Goals:**
- Touching 2 (reset) or 10 (burn) semantics.
- Adding a "reverse is sometimes wild" toggle. The choice is binary and we pick wild.
- Migrating archived spec / changelog text. They describe the historical state correctly.
- A formal deprecation period for `same_on_reverse` in client UI. We remove it now; the field is silently dropped on the wire for forward compat.

## Decisions

### Drop `same_on_reverse` entirely
**Choice:** Remove the field from `GameConfig`. `from_dict()` silently ignores the key if a client still sends it.
**Why:** Wild semantics make reverse-on-reverse always legal. Keeping the field as a no-op invites confusion.
**Alternative:** Keep the field as a no-op with a deprecation marker. Rejected — adds dead surface area for no current consumer.

### `is_legal_rank` branch order: special ranks first, then under-rule
**Choice:** Check `rank in {2, 10, reverse_rank}` for unconditional legality before the under-rule branch.
**Why:** Same shape as today's 2/10 branch — extends it with the configured rank. Reads as one logical "is this a wild?" check.

### Frontend: keep the indicator suffix, drop the lobby checkbox
**Choice:** The rule indicator still says `"play UNDER <R> (or another <R>)"` (always true now). The lobby loses the `Allow same rank on reverse` checkbox.
**Why:** The indicator's job is to tell the player at the moment of choice what's legal. Knowing another R is legal is *useful information*, even though it's now constant. Removing the lobby checkbox removes a knob that has no effect.

### Tooltip wording: name both behaviors
**Choice:** For a card of `rank == reverse_rank`, the tooltip reads `"Wild + Reverse — always legal; next play must be UNDER <R>."`
**Why:** The card has two effects and a player hovering needs to see both.

### Legend wording: "always legal"
**Choice:** The reverse entry in the "Special cards & house rules" legend reads `"Reverse — always legal; the next card must be UNDER <R>."`
**Why:** Mirrors the 2 and 10 entries' "always legal" phrasing for consistency.

### No new tests of "reverse on reverse" — it's covered by the wild branch
**Choice:** The single new test `test_reverse_rank_is_wild` (parameterized over a few pile tops: K, 7, 3, empty) is enough. Drop the existing `test_same_on_reverse_*` tests since the behavior they covered is now subsumed.
**Why:** A focused test on the wild branch covers the only thing that changed.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Players accustomed to the strict mode get a softer rule | Surfaced in CHANGELOG + README; the rule is the default for the project anyway. |
| Hidden assumption somewhere uses `config.same_on_reverse` and silently breaks | Grep before pushing. Both `princess/` and `static/` need to be clean of the symbol. |
| Old serialized client config (in localStorage, if any future change introduces it) still sends `same_on_reverse` | `from_dict` ignores unknown keys — already covered. |
| The frontend's legacy fallback path (`view.under_seven`) still uses the OLD field name | Untouched; this change doesn't break the alias. |

## Migration Plan

1. Engine: edit `GameConfig` (drop `same_on_reverse`), `is_legal_rank` (add the wild branch), `from_dict` (drop validation of the dropped field).
2. Engine tests: replace `test_same_on_reverse_*` with `test_reverse_rank_is_wild` (parameterized).
3. Server tests: update `test_config_updates_reverse_rank` to only send `reverse_rank` and assert the same shape.
4. Frontend JS: `isLegalRank` adds the wild branch; `renderConfigPanel`/`saveConfig` drop the checkbox; legend + tooltip wording.
5. Frontend HTML: remove the `<input id="cfg-same-on-reverse">` row.
6. Docs: README rule section, CHANGELOG `[Unreleased]`, `openspec/config.yaml` context.
7. Commit + push + green CI + merge.

Rollback: revert the engine change. The frontend's wild-branch in `isLegalRank` is a strict superset; reverting just the engine without the frontend would mean the client thinks a 5 is legal on a K but the server rejects → user sees an error toast. So roll back together if needed.

## Open Questions

- None.
