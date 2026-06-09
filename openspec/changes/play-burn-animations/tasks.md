## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/play-burn-animations`.
- [x] 1.2 Confirm `view.last_actions[-1]` carries `burned` / `picked_up` / `finished_pid` / `player_pid` in the live server by tailing `/logs` while playing a round (no engine change needed).

## 2. Desktop CSS (`static/styles.css`)

- [x] 2.1 Add to `:root`: `--anim-burn: 300ms; --anim-pickup: 280ms; --anim-illegal: 200ms; --anim-celebrate: 350ms;`.
- [x] 2.2 Add `@keyframes burn-flash` (color + bounce) and `@keyframes burn-flash-color` (color only, for reduced-motion fallback). Confirm flash color (e.g., `var(--accent-warm)`) hits ≥ 7:1 against the pile-card background.
- [x] 2.3 Add `.pile-card.is-burning { animation: burn-flash var(--anim-burn) ease; }`.
- [x] 2.4 Add `@keyframes pickup-fade-shake` for the pile area, `@keyframes pickup-handglow` for the user's hand row.
- [x] 2.5 Add `.pile-area.is-pickup { animation: pickup-fade-shake var(--anim-pickup) ease; }` and `#hand-row.is-pickup { animation: pickup-handglow var(--anim-pickup) ease; }`.
- [x] 2.6 Add `@keyframes illegal-shake` and `.card.is-illegal { animation: illegal-shake var(--anim-illegal) ease; }`.
- [x] 2.7 Add `@keyframes winner-celebrate` and `#winner-name.is-celebrating { animation: winner-celebrate var(--anim-celebrate) ease; }`.
- [x] 2.8 Add the `@media (prefers-reduced-motion: reduce)` block. Inside, override each `.is-*` rule so transforms/shakes/bounces are removed. Color flash + gold glow may remain.

## 3. Desktop JS (`static/app.js`)

- [x] 3.1 Add `lastSeenActionIndex: -1, celebratedRoundId: null` to the initial `state` object.
- [x] 3.2 In `renderGame(view)`, after the existing phase-transition tracking, compute `const newest = (view.last_actions?.length ?? 0) - 1;`. If `view.phase === "playing"` AND `newest > state.lastSeenActionIndex`, call a new helper `dispatchActionAnimations(view.last_actions[newest], view)` (only for the latest entry; intermediate misses are not animated). Then `state.lastSeenActionIndex = newest;`.
- [x] 3.3 When `view.phase !== "playing"` AND the previous phase WAS `"playing"`, reset `state.lastSeenActionIndex = -1` and `state.celebratedRoundId = null`.
- [x] 3.4 Implement `dispatchActionAnimations(entry, view)`:
  - If `entry.burned`, call `flash(el, "is-burning", 300)` against `document.getElementById("pile-card")`.
  - If `entry.picked_up`, call `flash(document.querySelector(".pile-area"), "is-pickup", 280)`; if `entry.player_pid === state.pid`, also `flash(document.getElementById("hand-row"), "is-pickup", 280)`.
- [x] 3.5 Implement `flash(el, cls, durationMs)`: guard `!el`; `el.classList.add(cls)`; `el.addEventListener("animationend", () => el.classList.remove(cls), { once: true });` plus `setTimeout(() => el.classList.remove(cls), durationMs + 50)` as a fallback.
- [x] 3.6 Hook the illegal-shake: in the WS message handler where a `play` reject lands in `showError(msg)`, also iterate `document.querySelectorAll("#hand-row .selected, #table-row .selected, #face-up-row .selected")` (whichever surfaces currently carry `.selected`) and `flash(el, "is-illegal", 200)` on each.
- [x] 3.7 Hook the winner celebrate: in the game-over render branch, after the `#winner-name` text is set, check `state.celebratedRoundId !== <current-round-id>`. If true, `flash(winnerNameEl, "is-celebrating", 350)` and set `state.celebratedRoundId = <current-round-id>`. Use the index of the round-ending action (the `finished_pid`-bearing entry) as the round id; failing that, fall back to a stable identifier built from `view.last_actions[-1].player_pid + view.last_actions.length`.

## 4. Mobile CSS (`static/mobile.css`)

- [x] 4.1 Add the same `--anim-*` custom properties to `:root` (or duplicate-safe if the mobile CSS shares the root with desktop styles).
- [x] 4.2 Add the same `@keyframes` (or namespace them — `mobile-burn-flash` etc. — only if a name collision exists; otherwise reuse the desktop keyframes by including them once and applying them to mobile selectors).
- [x] 4.3 Add the four `.is-*` rules scoped to the mobile selectors (`#m-pile-card.is-burning`, `#m-pile.is-pickup`, `#m-hand-row.is-pickup`, `.card.is-illegal` if not already covered, `#m-winner-name.is-celebrating`).
- [x] 4.4 Verify the hand-row lift in pickup does NOT push any card under `#m-action-bar`. If geometry is tight, reduce the lift to 1 px on mobile.
- [x] 4.5 Add the `@media (prefers-reduced-motion: reduce)` block in `mobile.css`.

## 5. Mobile JS (`static/mobile.js`)

- [x] 5.1 Add `lastSeenActionIndex: -1, celebratedRoundId: null` to the mobile `state`.
- [x] 5.2 Add the same new-action edge detection in the mobile `renderGame(view)` and reset rules.
- [x] 5.3 Implement `dispatchActionAnimations(entry, view)` and `flash(el, cls, durationMs)` mirroring the desktop helpers but targeting `#m-pile-card`, `#m-pile`, `#m-hand-row`, `#m-winner-name`.
- [x] 5.4 Hook the illegal-shake into the mobile `showError` (or equivalent) for play rejects: query `#m-hand-row .selected` and shake each.
- [x] 5.5 Hook the winner celebrate in the mobile end-of-round panel render.

## 6. Manual smoke (desktop + mobile, reduced-motion off and on)

- [x] 6.1 Burn: play a 10. Confirm `#pile-card` flashes warm-accent and bounces once. On mobile, confirm `#m-pile-card` does the same.
- [x] 6.2 Burn (chain): play 4-of-a-kind. Confirm a single burn animation (we animate the newest entry only).
- [x] 6.3 Pickup (self): force a state where the user must pick up. Confirm the pile-area dips and the hand-row lifts + glows; on an opponent's pickup, only the pile dips.
- [x] 6.4 Illegal play: select a 6 against an 8 pile and click Play. Confirm the 6's card shakes red and the toast appears.
- [x] 6.5 Winner: end a round. Confirm the winner-name briefly grows + glows; refresh / re-broadcast does not re-fire.
- [x] 6.6 Open DevTools → Rendering → "Emulate CSS prefers-reduced-motion: reduce". Repeat 6.1–6.5; confirm no bounces / shakes / grow, but color flash and gold glow remain.
- [x] 6.7 Reconnect mid-round: disconnect WS during a long round, reconnect. Confirm the animation fires for the newest action only.
- [x] 6.8 Spam clicks: rapidly click cards / actions during animations. Confirm no animation leaks (no `.is-*` class lingers in DevTools).

## 7. Tests

- [x] 7.1 No unit-test framework is currently wired for the static UI. Spec scenarios stand as the assertions; manual smoke is the verification. If a Playwright harness lands later, port the scenarios.

## 8. Docs

- [x] 8.1 In `CHANGELOG.md` `## [Unreleased]`, add a `### Added` bullet: "Play & burn animations: pile flashes on burn, pickup sweeps toward your hand, illegal plays shake the selected card, the winner name celebrates. All animations respect `prefers-reduced-motion`."

## 9. Verify

- [x] 9.1 `black princess tests` (no Python changes, but rerun for tidiness).
- [x] 9.2 `pylint princess tests` — expect 10.00/10.
- [x] 9.3 `pytest -q` — expect green (no test changes).
- [x] 9.4 `openspec validate --specs --strict` and `openspec validate play-burn-animations --strict`.

## 10. Ship

- [x] 10.1 Commit: `play-burn-animations: Add burn/pickup/illegal/winner CSS animations on both surfaces`.
- [x] 10.2 Push the branch; open a PR with the template.
- [x] 10.3 Watch CI; fix any red.
- [x] 10.4 Squash-merge into main once green.

## 11. Wrap up

- [x] 11.1 Run `openspec status --change play-burn-animations` — confirm 4/4 artifacts done.
- [x] 11.2 `/opsx:archive play-burn-animations` after merge.
