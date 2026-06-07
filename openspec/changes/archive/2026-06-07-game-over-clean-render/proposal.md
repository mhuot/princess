## Why

When a round ends, the frontend should show ONLY the winner panel. In practice, the play surface (opponents row, pile area, status stack with a stale "— Your turn." suffix) can stay visible at the same time as the winner panel, producing a screenshot like "bot played KS — Your turn." sitting directly above "Mike won the round!".

Two compounding bugs cause it:

1. **`hidden` attribute silently overridden by author CSS.** Our CSS sets `display: flex` on `.status-stack` and `.pile-area`. The browser's UA rule `[hidden] { display: none; }` is lower-priority than author CSS, so when `renderGame` sets `$("status-stack").hidden = true`, nothing actually hides — `display: flex` wins.
2. **`renderStatus` never runs in the `game_over` branch.** `renderGame`'s game-over early-return hides things but doesn't refresh the stack content. The DOM stays frozen at the previous (mid-round) broadcast — last_actions[-1] from before the winning play, plus the "— Your turn." suffix that's only computed when `!view.game_over`.

End result: the user sees the stale stack as if the round is still live, alongside the winner panel that says someone won. Particularly confusing when the bot's last action wasn't actually the final one — the winning player's move sits in `view.last_actions[-1]` but never renders.

## What Changes

- **CSS:** add explicit `[hidden]` overrides for every element that the frontend hides via the `hidden` attribute when game-over fires (`#opponents`, `.pile-area`, `.legend`, `#status-stack`, `#setup-area`, `#you-area`). Pattern: `<selector>[hidden] { display: none !important; }`. The `!important` is justified because the `hidden` attribute is the contract — author CSS that sets `display` shouldn't silently break it.
- **Frontend behavior:** in `renderGame`'s game-over branch, surface the winning action prominently inside the winner panel:
  - Render the **newest** entry from `view.last_actions` as a single line under the winner subtitle, formatted with the same glyphs (`🔥` / `↑` / `👑 <name>`) used in the status stack.
  - This makes Mike's "flipped <X> 👑 Mike" line *the* thing you read after "Mike won the round!", not a hidden artifact.
- **Spec scenarios:** the existing game-over panel requirement gains scenarios for "play surface fully hidden" and "winning action shown in panel".

## Capabilities

### Modified Capabilities

- `web-frontend`: tighten the end-of-round rendering — play surface hidden by CSS, winning action displayed in the panel.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/styles.css` — six `[hidden]` overrides; one new `.winner-final-action` block.
  - `static/app.js` — small block in `renderResults(view)` (already called from the game-over branch) to render the newest `last_actions` entry into a new `<p id="winner-final-action">` slot in the winner panel.
  - `static/index.html` — add `<p id="winner-final-action" class="winner-final-action"></p>` inside `#game-over`, between the winner subtitle and the results list.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` — `### Fixed` bullet.
- **Out of scope:** any engine change. The engine already records the winning action correctly (`finished_pid` set on the last entry of `view.last_actions`). This is purely a frontend rendering bug.
