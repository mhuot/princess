## Context

The visible bug is two browser-level facts colliding:

1. `[hidden]` is a UA-level selector. Any author CSS that sets `display` at the same specificity wins, because author rules outrank UA rules. We have `display: flex` on `.status-stack`, `.pile-area`, and a handful of other elements set up before the `hidden` attribute mattered.
2. `renderGame` early-returns in the game-over branch without calling `renderStatus(view)`. The DOM keeps whatever the previous render produced, including the "— Your turn." suffix that's only computed when `!view.game_over`.

The engine itself is fine. `view.last_actions[-1]` contains the winning action with `finished_pid` set; the frontend just doesn't render it once the panel takes over.

## Goals / Non-Goals

**Goals:**
- After `game_over` flips true, the play surface is *gone* from the DOM render — no stale status entries, no half-visible opponents row.
- The winning action is the line you read directly under "Mike won the round!" — not buried in a hidden stack.

**Non-Goals:**
- Refactoring the game-over render path into a single function. The early-return pattern in `renderGame` is fine; we patch around its blind spots, not rewrite it.
- Showing the full history in the panel. One line — the action that ended it — is enough.
- Touching the engine. The bug isn't there.

## Decisions

### Use `[hidden] { display: none !important; }` rather than rewrite each element's display rule
**Choice:** Add `<selector>[hidden] { display: none !important; }` for the six elements the JS hides via the `hidden` attribute. Keep their normal `display: flex` / `display: block` rules untouched.
**Why:** Preserves the `hidden` attribute as the single hide/show contract. Other CSS rules can keep setting `display` however they like without interfering.
**Alternative:** Toggle CSS classes (`.hidden { display: none; }`) instead of the `hidden` attribute. Equivalent power, but it's a wider refactor and doesn't match the rest of the codebase, which uses `.hidden = true` everywhere.

### Surface the winning action in the panel, not by un-hiding the status stack
**Choice:** Add a single `<p id="winner-final-action">` inside `#game-over`. `renderResults` populates it from `view.last_actions[-1]`.
**Why:** The status stack is a *mid-round* affordance. The game-over panel should be self-contained — opening to the winner panel after a round shouldn't require keeping a separate widget visible.
**Trade-off:** The user can't scroll back through the last three actions in the panel. They can still see all three in the in-memory `/logs` viewer if they care.

### Format the winner-final-action line with the same glyphs as the status stack
**Choice:** Reuse the same glyph logic — `🔥` on `burned`, `↑` on `picked_up`, `👑 <name>` on `finished_pid`. The line's text is `entry.text` plus the glyphs.
**Why:** Visual consistency. Players already know what the glyphs mean from in-round status updates.

### `!important` is acceptable here
**Choice:** Use `!important` on the `[hidden]` overrides.
**Why:** The `hidden` attribute is a semantic contract — when JS sets it, the element should disappear. Author CSS that sets `display` on the same element shouldn't silently win. `!important` makes the contract enforceable across the codebase without auditing every other display rule.

### No engine change, no spec change for `game-engine`
**Choice:** The engine's `_apply_committed_cards` already records the winning entry with `finished_pid` set. The fix is purely in `web-frontend`. The `game-engine` spec stays as-is.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| `!important` could mask a future style bug | Justified because the `hidden` attribute is *the* semantic toggle. If someone needs different show/hide logic, they should use a class, not override `[hidden]`. |
| The winner-final-action line is empty when `last_actions` is empty (impossible-but-defensive) | `renderResults` reads `view.last_actions[-1]`; if missing, leaves the slot empty (no crash). |
| Reduced status-stack visibility means a user who didn't see the winning play live can't replay it from the panel | One-line winner-final-action *is* the replay. The full history lives in `/logs`. |

## Migration Plan

1. `static/index.html`: insert `<p id="winner-final-action" class="winner-final-action"></p>` inside `#game-over`, between `#winner-subtitle` and `#results`.
2. `static/styles.css`: add the six `[hidden]` overrides; add `.winner-final-action` styling (centered, slightly muted, prefixed with a subtle "→").
3. `static/app.js`: in `renderResults(view)`, populate `#winner-final-action` from `view.last_actions[-1]` with the same glyph logic as `renderStatus`.
4. `CHANGELOG.md`: `### Fixed` bullet.
5. Commit + push + CI + merge.

Rollback: revert the three files. No persistence, no schema implications.

## Open Questions

- None.
