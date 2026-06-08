## Why

The mobile pile area shows the deck count and the discard's top card, but not **how many cards are in the discard pile**. That number matters strategically:

- "Picking up = N cards in your hand" is a real decision. Without the count you can't judge whether the pile is worth the gamble (a small pile = trivial pickup; a 12-card pile = pain).
- Four-of-a-kind burn potential — if the pile is small, your matching plays are likely to hit pile-rank streaks; if the pile is huge, it's been a hot round.
- Long pickup chains feel arbitrary without seeing the pile grow then drop.

The engine sends `view.pile_size` already (used today only to enable/disable the **Pick up** button). Adding it to the readout costs one DOM node and one render call.

## What Changes

- **Add a `Discard` count display** to the mobile pile area, in the **same left column as the deck count, directly below it**. Label + value pair, same visual treatment as the existing deck stat.
- Update the JS to write `view.pile_size` into the new node on every render.
- No engine change. Desktop unchanged.

## Capabilities

### Modified Capabilities

- `mobile-frontend`: "Game view layout (mobile)" pile-area clause adds the discard count below the deck count.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/mobile.html` — split the leftmost `.m-pile-stat` into two stacked stats (Deck + Discard) inside a column wrapper.
  - `static/mobile.css` — minor: a column wrapper for the two stats; the existing label and value rules apply to both. Replace the `:last-child` selector with an explicit `.m-stat-value` class so both numbers get the accent treatment.
  - `static/mobile.js` — `renderPile(view)` adds `$("m-discard-count").textContent = String(view.pile_size || 0);`
- **Affected APIs:** none — `view.pile_size` already exists.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Added` bullet.
- **Out of scope:**
  - Adding the same readout to the desktop UI (desktop already shows pile size as `#pile-size` muted text below the pile card; the mobile choice is to keep it in the left stats column).
  - Showing the historical max pile size or the recent burn count.
  - Animating the count when it changes.
