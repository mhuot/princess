## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/setup-no-auto-preselect`.

## 2. Frontend behavior

- [ ] 2.1 In `static/app.js`, add `phase: null` to the initial `state` object.
- [ ] 2.2 In `renderGame(view)`, before any other work, capture the previous phase: `const wasPhase = state.phase; state.phase = view.phase;`.
- [ ] 2.3 If `view.phase === "setup"` AND `wasPhase !== "setup"` AND `!view.you.ready`, call `state.setupSelected.clear()`. This catches rematch and any re-entry into setup.
- [ ] 2.4 In `renderSetup(view)`, when building each choose-card button via `makeFaceCard(c)`, also set `aria-pressed` based on whether `state.setupSelected.has(idx)`. (The current code adds the `.selected` class conditionally; mirror the same logic for the ARIA attribute.)
- [ ] 2.5 Audit `toggleSetupSelect(idx)` — the existing implementation already re-renders, which will re-set `aria-pressed` correctly. No change beyond the audit.

## 3. Frontend styling

- [ ] 3.1 In `static/styles.css`, find the `.choose-row .selected` or equivalent (currently scoped under `#choose-row .selected` or the generic `.card.selected` — confirm by grep). Bump the border from 3px to 4px solid `var(--accent)`. Strengthen the lift to `translateY(-6px)`.
- [ ] 3.2 Add `.selected::after { content: "✓"; position: absolute; bottom: 2px; left: 4px; font-size: 0.65rem; color: var(--accent-strong); font-weight: 900; }` (or the closest equivalent slot — confirm `.card` is `position: relative` so the absolute child anchors correctly).
- [ ] 3.3 Verify the `prefers-reduced-motion` block already suppresses translates; if not, add `.card.selected { transform: none; }` under the media query.

## 4. Manual smoke (no server tests — pure client behavior)

- [ ] 4.1 Restart the server (any sub-process running `python -m princess`), open the page, hard-refresh.
- [ ] 4.2 Create a room, add a bot, start the game. Confirm zero choose cards appear with a `✓` or `.selected` border at the moment the setup view renders.
- [ ] 4.3 Select 3, lock in, play a round, end the round, click Rematch. Confirm the new setup again renders zero selections.
- [ ] 4.4 With the page open mid-setup with 2 selections, kill and restart the server (`lsof -ti:8000 | xargs kill`, then `python -m princess`). Reload the page — the user joins fresh (no pid persistence yet), so the selection legitimately resets. Spec scenario "reconnect preserves in-session selection" only applies if the page tab is still alive; if your test framework spins up a new tab, the reset is expected.
- [ ] 4.5 Tab through the choose cards with the keyboard, listen for "pressed" / "not pressed" announcements (VoiceOver or NVDA). Confirm `aria-pressed` flips on selection.

## 5. Tests

- [ ] 5.1 (Optional) Add a tiny Playwright or jsdom test if the project picks one up later. For v1, the spec scenarios are the assertions; manual smoke is the verification.

## 6. Docs

- [ ] 6.1 In `CHANGELOG.md` `## [Unreleased]`, add a `### Fixed` section if one doesn't exist, with the bullet: "Setup phase no longer carries selections across rematches or reconnects. The `.selected` style is also visually distinct from the wild-rank ★ badge (selected = bottom-left ✓ glyph + thicker border)."

## 7. Verify

- [ ] 7.1 `black princess tests` (no Python changes, but rerun for tidiness).
- [ ] 7.2 `pylint princess tests` — expect 10.00/10.
- [ ] 7.3 `pytest -q` — expect green (no test changes).
- [ ] 7.4 `openspec validate --specs --strict` and `openspec validate setup-no-auto-preselect --strict`.

## 8. Ship

- [ ] 8.1 Commit: `setup-no-auto-preselect: Reset setup selection on phase entry + distinguish selected from wild badge`.
- [ ] 8.2 Push the branch; open a PR with the template.
- [ ] 8.3 Watch CI; fix any red.
- [ ] 8.4 Squash-merge into main once green.

## 9. Wrap up

- [ ] 9.1 Run `openspec status --change setup-no-auto-preselect` — confirm 4/4 artifacts done.
- [ ] 9.2 `/opsx:archive setup-no-auto-preselect` after merge.
