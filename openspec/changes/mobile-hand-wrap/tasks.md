## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-hand-wrap`.

## 2. HTML

- [ ] 2.1 In `static/mobile.html`, remove the two chevron buttons (`#m-hand-prev` and `#m-hand-next`) from inside `#m-hand-wrap`. The `<div id="m-hand-wrap">` stays as a simple wrapper. The hand row `<div id="m-hand-row">` stays.

## 3. CSS

- [ ] 3.1 In `static/mobile.css`, rewrite the `.m-hand-row` rule:
  - Drop `overflow-x: auto`, `scroll-snap-type: x mandatory`, `-webkit-overflow-scrolling: touch`, `touch-action: pan-x`, `padding: 8px 0 12px;`.
  - Add `flex-wrap: wrap`, `justify-content: flex-start`.
  - Bump `gap` to 6px.
  - Use `padding: 4px 0;` (or `0` — minimal).

- [ ] 3.2 In `static/mobile.css`, resize `.m-hand-card`:
  - Set `flex: 0 0 calc((100% - 24px) / 5)` (5 per row default).
  - Set `height: 90px`.
  - Bump `font-size` to `1.05rem` (down from 1.4 to suit the smaller width).
  - Drop `scroll-snap-align: start`.
  - Keep `.selected`, `.selected::before`, `.special::after`, `.red`, `.legal-hint` rules.

- [ ] 3.3 In `static/mobile.css`, delete the `.m-hand-wrap::before`, `.m-hand-wrap::after`, `.m-hand-wrap.has-prev::before`, `.m-hand-wrap.has-next::after` rules (gradient fades).

- [ ] 3.4 In `static/mobile.css`, delete the `.m-hand-edge`, `.m-hand-edge.prev`, `.m-hand-edge.next`, `.m-hand-wrap.has-prev .m-hand-edge.prev`, `.m-hand-wrap.has-next .m-hand-edge.next` rules (chevron styling).

- [ ] 3.5 Update the responsive breakpoints:
  - `@media (min-width: 480px) { .m-hand-card { flex: 0 0 calc((100% - 30px) / 6); } }` (6 per row).
  - `@media (max-width: 359px) { .m-hand-card { flex: 0 0 calc((100% - 18px) / 4); } }` (4 per row).

## 4. JS

- [ ] 4.1 In `static/mobile.js`, delete `updateEdgeIndicators()` and `scrollHandBy()` function definitions.

- [ ] 4.2 In the `DOMContentLoaded` listener, remove the four event-listener registrations for `m-hand-row.scroll`, `m-hand-prev.click`, and `m-hand-next.click`. Keep the `m-sort-btn.click` listener.

- [ ] 4.3 In `renderHand(view)`, remove the trailing `updateEdgeIndicators()` call. Everything else (build items, sort, append) stays the same.

## 5. Docs

- [ ] 5.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Changed`:
  - "Mobile hand now **wraps to multiple rows** of smaller cards (5 per row at iPhone 14 width) instead of horizontally scrolling. The whole hand is visible at a glance; large hands push the page scroll. Edge chevrons, gradient fades, and scroll-snap are gone. The **Sort: rank / off** toggle and hand-count badge stay. [mobile-hand-wrap]"

## 6. Verify

- [ ] 6.1 `black princess tests` (no Python; tidy).
- [ ] 6.2 `pylint princess tests` → 10.00/10.
- [ ] 6.3 `pytest -q` → green (no test changes).
- [ ] 6.4 `openspec validate --specs --strict` and `openspec validate mobile-hand-wrap --strict`.
- [ ] 6.5 Manual smoke at DevTools 390 × 844:
  - Start a round. Hand renders as a single row of up to 5 cards.
  - Add a bot scenario where you have to pick up the pile so your hand grows to 8+ cards. Confirm cards wrap to a second row, both fully visible.
  - Tap a card → lifts; tap another same-rank card → both selected; play → engine receives correct server indices.
  - Toggle Sort → cards reorder; same-rank groups visibly cluster.
  - Resize DevTools to 340 px → 4 cards per row. Resize to 600 px → 6 per row.

## 7. Ship

- [ ] 7.1 Commit: `mobile-hand-wrap: Wrap hand to multiple rows of smaller cards`.
- [ ] 7.2 Push the branch; open a PR.
- [ ] 7.3 Watch CI; auto-merge once green.

## 8. Wrap up

- [ ] 8.1 `openspec status --change mobile-hand-wrap` → 4/4 done.
- [ ] 8.2 `/opsx:archive mobile-hand-wrap` after merge.
