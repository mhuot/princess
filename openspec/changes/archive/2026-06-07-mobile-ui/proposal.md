## Why

The current UI is designed for desktop — opponents in a flex row, full-size cards in your hand, a logs link in the footer, a House rules `<select>` in the lobby. On a phone the cards shrink and the layout still works but it doesn't feel like a card game; nothing leans into touch.

Ship a parallel mobile UI at `/m` so a player on a phone gets a layout designed for one thumb: fan-out hand at the bottom, sticky action bar, full-screen pile, opponents collapsed to a strip. The desktop UI at `/` stays exactly as-is; this is opt-in by URL.

## What Changes

- **New route `GET /m`** that serves a new `static/mobile.html`. Same backend, same WebSocket protocol, same room codes. The desktop UI is untouched.
- **New frontend bundle** at `static/mobile.{html,css,js}`, designed for **390px wide minimum** (iPhone 14 portrait).
- **Hand renders as a fan-out arc**: each card rotated and translated so they overlap like real cards in a hand. Tap to select (lifts the chosen card vertically); tap again to deselect. The 7th+ card increases the overlap rather than the arc width.
- **Sticky bottom action bar** with two buttons: **Play** (green) and **Pick up** (red). Always visible above the fan, never covered by the keyboard.
- **Opponents collapsed to a strip** at the top: each opponent is a single row with name + hand count + (bot) tag + current-turn dot. Mini faceировать-up + face-down cards shown smaller.
- **Pile and rule indicator centered** in the middle third of the screen.
- **Top bar** with the room code (tap to copy), a status line (newest of `last_actions`), a small **Quit** button, and a small **Rename** button.
- **Setup phase** on mobile shows the 6 choose cards as a 2×3 grid (no fan-out); tap to select, third tap on a 4th replaces oldest. Lock-in is a sticky bottom button.
- **Winner panel** identical to desktop's `#game-over` markup (reused via the same renderer pattern).
- **No lobby House-rules config on mobile.** The host configures from desktop. Mobile users see a read-only summary of the reverse rank. Mobile users can: create a room, join a room, see seats, rename themselves, leave/take-over-as-bot. Bots can be added from mobile (single Add bot button); bot removal stays desktop-only for v1.
- **No logs viewer link.** `/logs` still works but isn't surfaced.
- **No legend on mobile.** A small `?` tap-to-show-rules sheet covers it: tapping the `?` opens a modal with the wild ranks (2, 10, reverse) explained.

## Capabilities

### New Capabilities

- `mobile-frontend`: a parallel UI at `/m` tailored for one-thumb play on phones (390px+ portrait), with fan-out hand, sticky action bar, and a compact opponents strip. Shares all backend endpoints and WebSocket messages with `web-frontend`.

### Modified Capabilities

- `room-server`: add the `GET /m` route returning `static/mobile.html`. Optionally: `GET /room/{code}` already serves `index.html`; we add a `GET /m/{code}` shortcut that serves `mobile.html` with the room code prefilled. No new room semantics.
- `repository-meta`: README quick-start mentions the mobile URL: "On your phone, use <http://your-host:8000/m> instead of `/`."

## Impact

- **Affected code:**
  - `princess/server.py` — two new GET routes (`/m`, `/m/{code}`).
  - `static/mobile.html`, `static/mobile.css`, `static/mobile.js` — new files. Significant code (~600–800 lines JS, ~400–600 lines CSS, ~150 HTML).
  - `README.md` — short mobile-URL note.
  - `CHANGELOG.md` — `### Added` bullet.
- **Affected APIs:** none changed; two new GET routes.
- **Affected dependencies:** none.
- **Docs touched:** README, CHANGELOG.
- **Depends on:** none beyond main.
- **Out of scope for v1:**
  - Auto-redirect by user-agent (always opt-in).
  - Bot **remove** on mobile (host-only desktop affordance stays).
  - House-rules config on mobile.
  - PWA / install-to-home-screen.
  - Landscape orientation polish (only portrait is targeted).
  - Tablet-size adjustments (768px+ falls through to desktop polish or shows mobile UI at a wider max-width — accept either; tighten in a follow-up).
  - Drag-and-drop play (tap-to-select only).
