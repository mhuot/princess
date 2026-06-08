## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/solo-start-bot-prompt`.

## 2. Desktop UI

- [ ] 2.1 In `static/index.html`, add a `<dialog id="solo-start-modal">` with: `<h3>You're alone in the room.</h3>`, a short body line, three primary buttons (`id="solo-add-1"`, `id="solo-add-2"`, `id="solo-add-3"`) labelled "Add 1 bot" / "Add 2 bots" / "Add 3 bots", and a secondary button `id="solo-cancel"` labelled **Back to lobby** (the host stays in the lobby; no API call).
- [ ] 2.2 In `static/styles.css`, reuse the existing modal styles. If a centered `.modal` style block exists, the new dialog inherits; otherwise add a small block.
- [ ] 2.3 In `static/app.js`:
  - Add `async function addBotsThenStart(n)`: loop `n` times calling `postJSON("/api/rooms/<code>/bot", {host_pid: state.pid})` sequentially; if any fails, show via `showError("lobby-error", ...)` and return without starting. After the loop, call `await postJSON("/api/rooms/<code>/start", {host_pid: state.pid})`.
  - Wire `#solo-add-1`, `#solo-add-2`, `#solo-add-3` clicks to `addBotsThenStart(1|2|3)` followed by `solo-start-modal.close()`.
  - Wire `#solo-cancel` ("Back to lobby" label) to close the modal — no other side effects.
  - Modify the existing **Start game** click handler (or `startGame()`) to: read `state.lastRoom?.seats.length` (the latest lobby snapshot); if `=== 1`, `solo-start-modal.showModal()`; else proceed with the existing POST. (If the code uses a different state shape for the seats, use that — the gist is "latest broadcast's seat count".)
- [ ] 2.4 Audit: confirm `state.lastRoom` (or equivalent) is updated by `renderLobby(room)`. If not, set it inside `renderLobby` so the click handler can read it. Names vary; use the existing variable.

## 3. Mobile UI

- [ ] 3.1 In `static/mobile.html`, add a `<dialog id="m-solo-sheet" class="m-sheet">` containing the same title/body and three buttons (`id="m-solo-add-1"`, `id="m-solo-add-2"`, `id="m-solo-add-3"`) plus an `id="m-solo-cancel"` button labelled **Back to lobby** and styled with `.m-cancel`.
- [ ] 3.2 In `static/mobile.js`:
  - Add `async function mAddBotsThenStart(n)` mirroring the desktop helper. Use `showError(msg)` (the mobile helper) on failure.
  - Wire `m-solo-add-1`/`2`/`3` clicks to call `mAddBotsThenStart(n)` then `$("m-solo-sheet").close()`.
  - Wire `m-solo-cancel` to close the sheet.
  - Modify the existing `startGame()` (the mobile button-click handler) to: read `state.lastRoom?.seats.length`; if `=== 1`, `$("m-solo-sheet").showModal()`; else proceed with the existing `POST /start`.
- [ ] 3.3 Audit: ensure mobile's `renderLobby(room)` writes `state.lastRoom = room` (or equivalent) so the guard has fresh data.

## 4. Smoke (no automated test)

- [ ] 4.1 Restart the server. On desktop: create a room (just you), click **Start game**. Confirm the modal opens. Click **Add 2 bots**. Confirm two bots appear in the lobby briefly, then the round starts in setup.
- [ ] 4.2 On desktop: create a room, click **Add bot** once, then **Start**. Confirm the modal does NOT open and the round starts.
- [ ] 4.3 On desktop: open the modal, click **Back to lobby**. Confirm no API calls, lobby unchanged.
- [ ] 4.4 On mobile (DevTools 390×844): same three smoke paths through the bottom sheet.
- [ ] 4.5 Optional: temporarily set `MAX_PLAYERS = 2` in `princess/rooms.py`, try **Add 3 bots** on a solo room — confirm the second POST returns 409, the lobby-error slot shows the message, and `/start` is NOT called. Restore the original cap.

## 5. Docs

- [ ] 5.1 In `CHANGELOG.md` `## [Unreleased]`, add a `### Added` bullet:
  - "When the host clicks Start game alone in a room, a prompt offers a one-tap path to Add 1/2/3 bots and start. No change for already-seated rooms. Both desktop and mobile UIs."

## 6. Verify

- [ ] 6.1 `black princess tests`.
- [ ] 6.2 `pylint princess tests` — 10.00/10.
- [ ] 6.3 `pytest -q` — green (no test changes needed).
- [ ] 6.4 `openspec validate --specs --strict` and `openspec validate solo-start-bot-prompt --strict`.

## 7. Ship

- [ ] 7.1 Commit: `solo-start-bot-prompt: Prompt host to add bots when starting alone`.
- [ ] 7.2 Push the branch; open a PR with the template.
- [ ] 7.3 Watch CI; auto-merge once green.

## 8. Wrap up

- [ ] 8.1 `openspec status --change solo-start-bot-prompt` → 4/4 done.
- [ ] 8.2 `/opsx:archive solo-start-bot-prompt` after merge.
