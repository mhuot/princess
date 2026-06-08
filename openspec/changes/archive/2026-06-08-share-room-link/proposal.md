## Why

To play with a friend, the host has to (1) read the 4-character room code, (2) tell the friend the URL of the server, (3) read out the code, (4) hope the friend types it correctly. Today there is no copy-to-clipboard, no share-sheet hook, no QR code, nothing. On mobile the room code in the game view already supports tap-to-copy of *just the code*, but not the URL — so the friend still has to know where to type it.

Give every UI surface a one-click **Share** that produces a deep-link URL like `https://<host>/room/AB12` (or `/m/AB12` from mobile). On mobile, prefer the native Web Share API so the user gets the OS share sheet (Messages, WhatsApp, AirDrop). On desktop, fall back to clipboard copy with a transient "Copied!" confirmation.

## What Changes

- **Desktop:** add a small **Share** button next to the room code in the lobby. Clicking it copies the room URL (`location.origin + "/room/" + state.code`) to the clipboard and briefly flashes the button label to **Copied!**.
- **Mobile (lobby):** add a **Share** button next to the room-code line. Clicking it prefers `navigator.share({ title, text, url })` if available (`/m/<code>` URL); otherwise falls back to `navigator.clipboard.writeText(url)` with a brief toast/label flash.
- **Mobile (game-view top bar):** the existing tap-to-copy on the room-code chip is unchanged for *quick code-only copy* (it remains useful when a friend just wants to type the code). A new tiny **Share** affordance (icon or `↗`) appears next to the chip and routes to the same share/copy helper as the lobby button.
- **Share content:** for `navigator.share`, the payload is `{ title: "Princess Card Game", text: "Join my Princess room <code>:", url: <link> }`. For clipboard fallback, just the URL.
- **Visual confirmation:** the button text temporarily becomes **Copied!** for ~1.5s after a successful copy. If `navigator.share` was used, no toast is needed — the OS sheet IS the confirmation.

## Capabilities

### Modified Capabilities

- `web-frontend`: lobby gains a **Share** button next to the room code that copies the room URL to the clipboard with a transient confirmation.
- `mobile-frontend`: lobby and the game-view top bar gain a **Share** affordance that prefers `navigator.share` and falls back to clipboard copy.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/index.html` — add `<button id="share-link-btn">Share link</button>` near the room code in the lobby.
  - `static/app.js` — `async function shareRoomLink()` that builds the URL, attempts `navigator.share` (best-effort) then falls back to `navigator.clipboard.writeText`. Show "Copied!" feedback on the button for 1.5s on clipboard success. Wire the button click.
  - `static/mobile.html` — add `<button id="m-share-btn" class="m-icon">↗</button>` near the room code on the lobby screen, and a small `↗` button in the game-view top bar (right of the room-code chip).
  - `static/mobile.css` — minor: button styles match existing `.m-icon` and lobby button conventions.
  - `static/mobile.js` — `async function shareRoomLink()` mirroring the desktop helper, but using `/m/<code>` for the URL. Wire the two button clicks.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Added` bullet.
- **Out of scope:**
  - QR-code generation. A nice future v2 (especially for showing across the table) but a separate change.
  - "Smart" detection of recipient's device class to pick `/room/` vs `/m/`. Sender's UI dictates the URL.
  - Accepting a full URL paste in the join-by-code input. Out of scope; the existing `/room/<code>` route handler already prefills the code anyway, so users can navigate the URL directly.
