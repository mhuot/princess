## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-discard-count`.

## 2. HTML

- [ ] 2.1 In `static/mobile.html`, locate the pile area's leftmost `.m-pile-stat` block (Deck). Wrap it in a column wrapper and add a second stat below for Discard:

  ```html
  <div class="m-pile-stat-col">
    <div class="m-pile-stat">
      <span class="m-stat-label">Deck</span>
      <span id="m-deck-count" class="m-stat-value">0</span>
    </div>
    <div class="m-pile-stat">
      <span class="m-stat-label">Discard</span>
      <span id="m-discard-count" class="m-stat-value">0</span>
    </div>
  </div>
  ```

## 3. CSS

- [ ] 3.1 In `static/mobile.css`, replace the existing `.m-pile-stat span:last-child` selector with an explicit `.m-stat-value` class:

  ```css
  .m-stat-value { font-size: 1.2rem; font-weight: 700; color: var(--accent); }
  ```

  Remove the `.m-pile-stat span:last-child { ... }` rule.

- [ ] 3.2 Add the column wrapper:

  ```css
  .m-pile-stat-col {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    align-items: center;
  }
  ```

## 4. JS

- [ ] 4.1 In `static/mobile.js`, in `renderPile(view)`, add a line to write the discard count:

  ```js
  $("m-discard-count").textContent = String(view.pile_size || 0);
  ```

  Add it adjacent to the existing `$("m-deck-count").textContent = String(view.deck_count);` line.

## 5. Docs

- [ ] 5.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Added`:
  - "Mobile pile area now shows a **Discard** count below the Deck count (sourced from `view.pile_size`). Easier to judge whether picking up the pile is a small concession or a 12-card disaster. [mobile-discard-count]"

## 6. Verify

- [ ] 6.1 `black princess tests` (no Python; tidy).
- [ ] 6.2 `pylint princess tests` → 10.00/10.
- [ ] 6.3 `pytest -q` → green.
- [ ] 6.4 `openspec validate --specs --strict` and `openspec validate mobile-discard-count --strict`.
- [ ] 6.5 Manual smoke at DevTools 390 × 844:
  - Start a round, confirm the left stats column shows `Deck N` and `Discard 0`.
  - Play a few cards; confirm `Discard` increments.
  - Trigger a burn (play a 10); confirm `Discard 0` after burn.

## 7. Ship

- [ ] 7.1 Commit: `mobile-discard-count: Show Discard count below Deck count in pile area`.
- [ ] 7.2 Push the branch; open a PR.
- [ ] 7.3 Watch CI; auto-merge once green.

## 8. Wrap up

- [ ] 8.1 `openspec status --change mobile-discard-count` → 4/4 done.
- [ ] 8.2 `/opsx:archive mobile-discard-count` after merge.
