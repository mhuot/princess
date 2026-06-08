## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-ui`.

## 2. Server routes

- [ ] 2.1 In `princess/server.py`, add `@app.get("/m")` returning `FileResponse(STATIC_DIR / "mobile.html")`.
- [ ] 2.2 Add `@app.get("/m/{code}")` (same response) so the phone-shortcut URL `/m/AB12` works.
- [ ] 2.3 (Optional) `tests/test_server.py::test_mobile_routes_serve_mobile_html` — assert both routes return 200 and content includes a marker (`<title>Princess Card Game — mobile</title>` or similar) that is NOT in the desktop `index.html`.

## 3. Mobile HTML skeleton (`static/mobile.html`)

- [ ] 3.1 Boilerplate: `<!doctype html>`, `<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">`, `<title>Princess — mobile</title>`, `<link rel="stylesheet" href="/static/mobile.css">`, `<script src="/static/mobile.js" defer></script>`.
- [ ] 3.2 `<section id="m-lobby">` — name input, Create button, code input, Join button, seat list slot, sticky **Start game** button (host).
- [ ] 3.3 `<section id="m-game">` — top bar, opponents strip, pile area, your table, fan-out hand container, sticky action bar with Play / Pickup.
- [ ] 3.4 `<section id="m-setup">` — 2×3 choose grid, sticky Lock-in.
- [ ] 3.5 `<section id="m-game-over">` — same DOM shape as desktop game-over (`#winner-name`, `#winner-subtitle`, `#winner-final-action`, `#results`, `#rematch-btn`, `#new-game-btn`, `#rematch-note`).
- [ ] 3.6 `<dialog id="m-quit">` — bottom sheet for quit options.
- [ ] 3.7 `<dialog id="m-rules">` — rules sheet (three wilds).

## 4. Mobile CSS (`static/mobile.css`)

- [ ] 4.1 Base reset + color tokens (reuse the existing `--bg`, `--ink`, `--accent` palette by copying the `:root` block, or by adding a small CSS variable file shared at run time).
- [ ] 4.2 Top bar layout (sticky top, dark background, white text, big tap targets ≥ 44px).
- [ ] 4.3 Opponents strip (horizontal scroll, hide scrollbar, avatar circles).
- [ ] 4.4 Pile + rule (centered, slightly larger card).
- [ ] 4.5 Your table (mini-card row, similar to desktop's mini layout).
- [ ] 4.6 Fan-out hand container — `position: relative; height: 140px;` with each `.m-hand-card` `position: absolute` and JS-applied `transform` per index.
- [ ] 4.7 Sticky action bar at bottom — Play (green) + Pickup (red), 50/50 width split, 56px tall.
- [ ] 4.8 Setup 2×3 grid (CSS grid).
- [ ] 4.9 Game-over panel full-screen (`position: fixed; inset: 0;` with the winner panel centered).
- [ ] 4.10 Quit/rules bottom sheets — `<dialog>` styled to slide up from bottom (transform translateY, animated unless `prefers-reduced-motion`).
- [ ] 4.11 `[hidden]` overrides for every element styled with explicit `display`. Mirror the lesson from `game-over-clean-render`.

## 5. Mobile JS (`static/mobile.js`)

- [ ] 5.1 Initial `state` object: pid, code, isHost, socket, phase, view, selectedIndices (Set), setupSelected (Set), seatWasHuman (Set).
- [ ] 5.2 Routing: on load, parse `location.pathname` for `/m/<code>` and prefill the code input.
- [ ] 5.3 Lobby handlers: createRoom, joinRoom, addBot, startGame.
- [ ] 5.4 WebSocket: connect, route message types (`lobby` / `state` / `error`).
- [ ] 5.5 `renderLobby` — mobile lobby with seats, host buttons.
- [ ] 5.6 `renderSetup` — 6 cards in 2×3 grid; tap-to-toggle; Lock-in button.
- [ ] 5.7 `renderGame` — phase routing (setup vs playing vs game_over), with phase-transition reset of `setupSelected` (same trick as desktop).
- [ ] 5.8 `renderOpponents` — horizontal strip with mini avatars/turn dot.
- [ ] 5.9 `renderPile` — centered pile card + rule indicator + deck count.
- [ ] 5.10 `renderHand` — **fan-out arc**. Iterate hand indices, compute angle and translate per card, render as buttons with `data-idx`. Selected indices get an extra negative translateY and a `.selected` class.
- [ ] 5.11 `renderTable` — mini face-up + face-down row.
- [ ] 5.12 Tap handlers: card tap → toggle in `selectedIndices` (must share rank); Play → POST WS `play`; Pickup → POST WS `pickup`.
- [ ] 5.13 `renderResults` — mobile winner panel.
- [ ] 5.14 Quit sheet handlers: same logic as desktop (host: End round / Abort; non-host: Take-over / Leave).
- [ ] 5.15 Rename inline (lobby seat row) + Rename button (top bar in game).
- [ ] 5.16 Rules sheet open/close.

## 6. Docs

- [ ] 6.1 README — add a short "On a phone? Visit `/m` for a touch-friendly UI." sentence in the Quick start section.
- [ ] 6.2 CHANGELOG `## [Unreleased]` `### Added` — bullet describing the new mobile route + UI features (fan-out, sticky action bar, bottom-sheet quit, no logs/legend).

## 7. Verify locally

- [ ] 7.1 `black princess tests`
- [ ] 7.2 `pylint princess tests` — 10.00/10.
- [ ] 7.3 `pytest -q` — green.
- [ ] 7.4 `openspec validate --specs --strict` and `openspec validate mobile-ui --strict`.
- [ ] 7.5 Manual smoke: open `/m` in DevTools at 390×844 portrait. Create a room, add a bot, start the game. Confirm fan-out cards, sticky action bar, opponents strip, rules sheet, quit sheet, winner panel. Watch for tap-target ≥ 44px and no horizontal overflow.

## 8. Ship

- [ ] 8.1 Commit: `mobile-ui: Add /m route with fan-out hand and bottom-sheet UX`.
- [ ] 8.2 Push the branch; open a PR with the template.
- [ ] 8.3 Watch CI; auto-merge once green.

## 9. Wrap up

- [ ] 9.1 `openspec status --change mobile-ui` → 4/4 done.
- [ ] 9.2 `/opsx:archive mobile-ui` after merge.
