## Why

Headless smoke testing caught a real bug shipped in `share-room-link`. On mobile, tapping the `↗` share button correctly copies the URL to the clipboard, but the **"Link copied!" toast never appears** — the user gets no confirmation. Root cause:

`flashShared()` writes into `#m-lobby-error`. That element lives inside `#m-landing`, which is `hidden` the moment a room is created — and the share button only exists after a room is created. So the toast text is set on an element whose parent is `display: none`. The clipboard works, but the user can't tell.

Match the desktop pattern (where the button label flashes **Copied!**) instead. Each `↗` button briefly becomes `✓` for 1.5s — visible because it lives in the same container the user is already looking at, and consistent with the desktop behavior they'll also encounter.

## What Changes

- **Remove `flashShared()`** from `mobile.js`. It writes to a hidden element; no rescuing it.
- **Add `flashShareButton(buttonId)`** that:
  - Reads the clicked button's `textContent`, stashes it, and replaces it with `"✓"` for 1500ms.
  - Restores the original `↗` after the timeout.
- **Pass the clicked button's id into `shareRoomLink()`** so the helper knows which button to flash on clipboard-fallback success.
- **Wire both buttons** (`#m-share-btn-lobby` and `#m-share-btn-game`) to call `shareRoomLink(event.currentTarget.id)`.

No CSS changes. No HTML changes. Engine and desktop untouched.

## Capabilities

### Modified Capabilities

- `mobile-frontend`: clarify the visual-confirmation mechanism in the "Share room link (mobile)" requirement — button glyph flashes `✓` rather than a separate toast element.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/mobile.js` — delete `flashShared()`. New `flashShareButton(id)` helper. `shareRoomLink(buttonId)` becomes `shareRoomLink(buttonId)` and calls `flashShareButton(buttonId)` on clipboard success.
- **Affected APIs:** none.
- **Affected dependencies:** none.
- **Docs touched:** `CHANGELOG.md` `## [Unreleased]` `### Fixed` bullet.
- **Out of scope:**
  - A general toast/notification helper for other "operation succeeded" cues. Per-button flash is fine for v1.
  - Refactoring the desktop's identical clipboard-flash pattern to share code with mobile.
