# Changelog

All notable changes to Princess Card Game will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Deep links (`/room/<code>` and `/m/<code>`) now **auto-join** the room. First-time visitors see a focused name-only form (Join button stays disabled until a non-empty trimmed name is typed; the name is `trim()`-ed before save and send). Returning visitors auto-join with the name cached in `localStorage`. Page refreshes restore the seat via a `sessionStorage` sentinel; if the sentinel goes stale (unknown pid / evicted seat), the WS closes silently and we re-run the tier chain. [deep-link-auto-join]
- Phones are auto-redirected from `/` and `/room/<code>` to `/m` and `/m/<code>`. Override with `?desktop=1` or the **View desktop site** link in the mobile lobby. The reverse-path **Mobile site** link lives in the desktop footer. UA detection uses the standard `Mobi` substring check; tablets (which omit `Mobi`) stay on the desktop UI. [mobile-ua-redirect]

### Changed

- Mobile hand now **wraps to multiple rows** of smaller cards (5 per row at iPhone 14 width) instead of horizontally scrolling. The whole hand is visible at a glance; very large hands push the page scroll. Edge chevrons, gradient fades, and scroll-snap are gone. The **Sort: rank / off** toggle and hand-count badge stay. [mobile-hand-wrap]
- Mobile opponent chips now show each opponent's **face-up cards** inline (with the ★ glyph on wild ranks), matching the desktop UI. Public information is now visible without leaving the play screen. [mobile-opponent-face-up]
- Mobile hand is now a horizontally-scrolling row of full-size cards (3 visible at iPhone 14 width) with snap-to-card scrolling, tappable left/right chevron indicators when more cards exist off-screen, and a **Sort: rank / off** toggle plus a hand-count badge. Replaces the fan-out arc from the original mobile UI. [mobile-hand-scroll-sort]

### Fixed

- Mobile Share button now visually confirms the clipboard copy by flashing the `↗` glyph to `✓` for 1.5s. The previous `Link copied!` toast was rendered into `#m-lobby-error` — an element inside `#m-landing` that gets hidden the moment a room is created, so it was always invisible from the user's perspective. Caught by automated Playwright smoke test. [mobile-share-toast-fix]
- End-of-round panel now hides the play surface completely. The `hidden` attribute is silently overridden by author CSS that sets `display: flex`/`block`, so paired `[hidden] { display: none !important; }` rules now enforce the attribute. The winner panel also surfaces the round-ending action (same 🔥/↑/👑 glyphs the status stack uses) so you can see the winning play directly under the winner's name. [game-over-clean-render]
- Setup phase no longer carries selections across rematches or reconnects — `state.setupSelected` is reset on every transition INTO `phase: "setup"` (peer-triggered re-renders during setup keep your in-progress picks intact). The `.selected` style is also visually distinct from the wild-rank ★ badge: selected cards now wear a 4px accent border and a bottom-left ✓ glyph (opposite the wild ★ in the top-right). Choose-card buttons carry `aria-pressed` for screen-reader users. [setup-no-auto-preselect]

### Added

- Every lobby and the mobile game-view top bar gain a **Share** affordance. Tapping it opens the OS share sheet (`navigator.share`) on capable mobile browsers, or copies the room URL (`/room/<code>` on desktop, `/m/<code>` on mobile) to the clipboard with a transient **Copied!** confirmation. The code-only tap-to-copy on the mobile game-view room chip stays unchanged for voice-dictation flows. [share-room-link]
- Mobile pile area now shows a **Discard** count below the Deck count (sourced from `view.pile_size`). Easier to judge whether picking up the pile is a small concession or a 12-card disaster. [mobile-discard-count]
- Mobile hand surfaces a floating **↓ N more** indicator chip when one or more hand cards are hidden beneath the sticky action bar (typically a 16+ card hand after a forced pickup). Tap the chip to smooth-scroll to the end of the hand. `#m-game` reserves bottom padding so the last row clears the action bar at the bottom of the page. [mobile-hand-scroll-hint]
- When the host clicks **Start game** alone in a room, a friendly prompt offers a one-tap path: **Add 1 bot**, **Add 2 bots**, **Add 3 bots**, or **Back to lobby**. Confirming adds the bots sequentially then starts the round. No prompt if any other seat is already filled. Both desktop and mobile. [solo-start-bot-prompt]
- **Mobile UI** at `/m` (and `/m/<code>` for direct join). Tap-only, fan-out hand at the bottom, sticky Play/Pickup action bar, opponents strip, bottom-sheet quit modal, `?` rules sheet, dedicated rename sheet. 390px portrait minimum (iPhone 14). Shares all REST + WebSocket endpoints with the desktop UI; the desktop UI at `/` is unchanged. [mobile-ui]
- Host can **remove a bot seat** from the lobby via a per-row Remove button (`POST /api/rooms/{code}/remove_bot`). Lobby-only; host-only. [lobby-rename-and-remove-bots]
- Any seated player can **rename themselves** at any time — inline input on their own row in the lobby, or a Rename button in the game header during a round (`POST /api/rooms/{code}/rename`). [lobby-rename-and-remove-bots]

### Changed

- Reverse-rank house rule now defaults to **5**, not 7. The rank itself is now configurable per room from the lobby's House rules panel (legal ranks: 3, 4, 5, 6, 7, 8, 9, J, Q, K, A — wild ranks 2 and 10 are excluded). [tunable-reverse-rank]
- `GameConfig` gains `reverse_rank: int` (default 5). [tunable-reverse-rank]
- **The reverse rank is now a wild card**: always legal regardless of pile top, joining 2 (reset) and 10 (burn) as the third unconditional wild. The under-rule still fires when it lands. [reverse-rank-is-wild]
- Frontend rule indicator, hover tooltip, and "Special cards & house rules" legend now render the rank dynamically based on the room config. The legend lists three wilds; the hover tooltip on a reverse-rank card reads `"Wild + Reverse — always legal; next play must be UNDER <R>."`. [reverse-rank-is-wild]

### Removed

- `GameConfig.seven_on_seven` — replaced by `reverse_rank`. [tunable-reverse-rank]
- `GameConfig.same_on_reverse` — subsumed by the wild rule (reverse-on-reverse is always legal because the reverse rank is wild). The lobby's "Allow same rank on reverse" checkbox is gone. Legacy clients sending either key are silently dropped. [reverse-rank-is-wild]
- `princess.game.REVERSE_CARD` module constant — the value now lives in `GameConfig.reverse_rank`. [tunable-reverse-rank]

## [0.1.0] — 2026-06-07

Initial release. Everything below was shipped via OpenSpec changes archived under [`openspec/changes/archive/`](openspec/changes/archive/).

### Added

**Game engine** (`princess/game.py`)

- 2–4 player climbing card game on a standard 52-card deck.
- Each player dealt 3 face-down + 3 face-up + 3 hand (or 3 face-down + 6 "choose" + 0 hand when the swap phase is enabled).
- Play source priority hand → face-up → face-down.
- Rank-based legality: played rank ≥ pile top unless a special applies.
- **2** is wild reset (always legal; next play unrestricted).
- **10** burns the pile and the same player plays again.
- **7** forces the next play to be UNDER 7 — the project's defining house rule.
  - **7-on-7 toggle** (`GameConfig.seven_on_seven`) defaults to true.
- **Four of a kind** in a row on the pile burns it.
- Hand auto-refills from the deck after every play.
- Voluntary pickup of the whole pile; turn always passes to the next non-finished player.
- Face-down "blind" plays: revealed → tested; illegal flips force pickup of pile + revealed card.
- Game over when only one player still holds cards; `finished_order` tracks Princess (winner) through last place.
- New `Game.end_round()` — host-driven early termination ranking remaining players by ascending hand size.
- Per-room configuration via `GameConfig`; unknown keys silently ignored for forward compatibility.

**AI bot** (`princess/ai.py`)

- Heuristic decider: plays the lowest legal non-special card, hoards 2s and 10s.
- Completes four-of-a-kind burns when pile + hand allow.
- Blind random pick on face-down plays.
- Swap-phase auto-pick: chooses the top 3 highest-rank cards from the choose pile.

**Server** (`princess/server.py` + `princess/rooms.py`)

- FastAPI + WebSockets, in-memory `RoomRegistry`, 4-char alphanumeric room codes.
- REST endpoints: create / join / bot / config / start / rematch / abort / leave / end_round.
- WebSocket `/ws/{code}/{pid}` carries `play`, `pickup`, and `set_face_up` actions.
- Bot turn loop with safety cap (30 actions when a connected human is waiting; 1000 when only bots remain).
- Force-pickup fallback on any rejected bot action; exception fallback for bot crashes.
- 100-name SFW bot-name roster with no in-room duplicates.
- Per-room rule config (`seven_on_seven`).
- Host-only end-of-round, abort, rematch, and `convert_to_bot` flag on `/leave`.
- Orphan room cleanup: rooms with no connected sockets for `ROOM_IDLE_TIMEOUT_SECONDS` (default 300) are evicted on the next request tick.

**Frontend** (`static/`)

- Vanilla HTML + CSS + JS single-page app, served from `/`.
- Lobby with create / join / host-rules panel / add-bot / start.
- Setup-phase UI: 6 choose cards, pick 3, "Lock in" button.
- Game view: opponents row, pile area with rule indicator, your-table (face-up + face-down in one mini-row), hand, action buttons.
- Sort-hand toggle (rank then suit, client-side; server indices preserved).
- "Quit & return to lobby" opens a contextual modal — non-host: take over with bot / leave; host: end round / abort.
- "(bot)" / "(now a bot)" tag on opponents during play and in the lobby.
- End-of-round panel: winner name in big gold type, finishing order, rematch button (host).
- Hover tooltip on every card naming the rank and the rule (for 2, 7, 10).
- Collapsible "Special cards & house rules" legend; dynamically reflects the active config.
- WCAG AAA color palette, skip link, ARIA labels and roles, keyboard focus rings, `prefers-reduced-motion`.

**Logs** (`princess/logging_config.py`)

- In-memory FIFO ring buffer (2000 entries, drops oldest). No filesystem writes.
- Stdout mirror at configured `LOG_LEVEL` (default INFO).
- Per-room logger namespaces (`princess.room.<code>`) — grep-friendly.
- REST: `GET /api/logs?since=&limit=`, `GET /api/logs/download` (text attachment), `DELETE /api/logs`.
- In-browser `/logs` viewer with live 2s tail, autoscroll, download, clear.
- Instrumented points: room lifecycle, WebSocket connect/disconnect/crash, every play and pickup (success + rejection), bot decisions with pile-top and hand, bot loop safety cap.

**Repository meta** (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `NOTICE`, `.github/`, `openspec/config.yaml`)

- Apache 2.0 license + per-file headers.
- GitHub Actions workflows: `tests.yml`, `lint.yml`, `openspec.yml`.
- PR + issue templates.
- OpenSpec config populated with project context (Python 3.14, 7-under, Princess-only naming) and atomic-commit + docs-sync rules.

### Tests

- 105 pytest tests covering engine, AI, server endpoints, room/registry, logging buffer, and the WebSocket round-trip.

[Unreleased]: https://github.com/mhuot/princess/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mhuot/princess/releases/tag/v0.1.0
