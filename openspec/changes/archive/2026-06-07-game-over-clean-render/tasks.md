## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/game-over-clean-render`.

## 2. CSS: enforce `[hidden]`

- [ ] 2.1 In `static/styles.css`, add explicit `[hidden]` overrides for every element that the JS hides via the `hidden` attribute. Concretely:

  ```css
  #opponents[hidden],
  .pile-area[hidden],
  .legend[hidden],
  #status-stack[hidden],
  #setup-area[hidden],
  #you-area[hidden],
  #game-over[hidden] {
    display: none !important;
  }
  ```

- [ ] 2.2 Verify visually after applying: refresh a live page, set `view.game_over` via dev tools, confirm only the winner panel remains.

## 3. HTML: add winning-action slot

- [ ] 3.1 In `static/index.html`, inside `#game-over`, between `#winner-subtitle` and `#results`, add `<p id="winner-final-action" class="winner-final-action"></p>`.

## 4. CSS: style the winning-action line

- [ ] 4.1 In `static/styles.css`, add a `.winner-final-action` rule (e.g. centered, slightly muted color, font-size ~1rem). Prepend a subtle "→" via `::before` for visual distinction, or skip the glyph — design preference.

## 5. JS: populate the winning-action line

- [ ] 5.1 In `static/app.js` `renderResults(view)`, after setting `#winner-name` and `#winner-subtitle` but before iterating `view.finished_order`, populate `#winner-final-action`:
  - Read `view.last_actions?.[view.last_actions.length - 1]` (or null).
  - If null, set `textContent = ""`.
  - Otherwise, build the text the same way `renderStatus` builds an entry: start with `entry.text`, append `🔥` if `entry.burned`, `↑` if `entry.picked_up`, and ` 👑 <name>` if `entry.finished_pid` (look up via `view.players`).
  - Set the result as `#winner-final-action` `textContent`.

## 6. Docs

- [ ] 6.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Fixed`:
  - "End-of-round panel now hides the play surface completely (CSS `[hidden]` overrides enforce the `hidden` attribute against author `display` rules). The winning action is also surfaced inside the winner panel with the same glyphs (🔥/↑/👑) the status stack uses, so you can see Mike's winning move directly under 'Mike won the round!'."

## 7. Verify locally

- [ ] 7.1 `black princess tests` (no Python changes, but rerun for tidiness).
- [ ] 7.2 `pylint princess tests` — expect 10.00/10.
- [ ] 7.3 `pytest -q` — expect green (no test changes).
- [ ] 7.4 `openspec validate --specs --strict` and `openspec validate game-over-clean-render --strict`.
- [ ] 7.5 Manual smoke: restart the server, play a round, win. Confirm the play surface is fully hidden; the winner panel includes a line like "Mike flipped 4D 👑 Mike" between the subtitle and the results list.

## 8. Ship

- [ ] 8.1 Commit: `game-over-clean-render: Enforce hidden + show winning action in panel`.
- [ ] 8.2 Push the branch; open a PR.
- [ ] 8.3 Watch CI; auto-merge once green.

## 9. Wrap up

- [ ] 9.1 Confirm `openspec status --change game-over-clean-render` → 4/4 done.
- [ ] 9.2 `/opsx:archive game-over-clean-render` after merge.
