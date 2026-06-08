## Context

The browser has two relevant APIs:

- **`navigator.share(payload)`** — opens the OS-native share sheet. Supported on iOS Safari, Chrome Android, Edge, and modern Firefox. Requires HTTPS (or `localhost`) and a user-gesture context. Resolves on user dismissal; rejects with `AbortError` when the user cancels.
- **`navigator.clipboard.writeText(text)`** — copies text to the system clipboard. Same gesture/HTTPS requirements. Resolves silently; the recipient app has no signal.

Both are gated on a user-gesture context — fine, the share button click satisfies it. Both can fail (no permission, insecure context); we handle both.

The mobile UI's existing tap-to-copy on the room-code chip uses `navigator.clipboard` to copy the bare code (e.g., `"AB12"`). That's still useful when a friend on a voice call wants the code dictated and is ready to type it. We *don't* want to break that — Share is additive.

## Goals / Non-Goals

**Goals:**
- One-click share from desktop lobby, mobile lobby, and mobile game-view.
- Native share sheet on mobile when available (no copy-paste dance for Messages / WhatsApp / etc.).
- Graceful clipboard-only fallback when `navigator.share` is missing.
- Clear visual confirmation when copy succeeds (so the user doesn't double-tap).

**Non-Goals:**
- QR-code generation. Out of scope; separate change.
- Detecting the recipient's preferred UI (mobile vs desktop). Sender's interface dictates.
- A persistent "Recently shared with" history.
- Adding share to the in-game header on desktop (the lobby button is enough for v1).
- Email / SMS deep-link templates (`mailto:` / `sms:`). The OS share sheet handles those when available.

## Decisions

### Helper signature: one async function per UI
**Choice:** `shareRoomLink()` lives on both `app.js` and `mobile.js`. Each builds its own URL (`/room/<code>` vs `/m/<code>`) and runs the same share-then-clipboard-fallback chain.
**Why:** No build step in this project, so a shared module would add complexity. Two ~25-line copies are fine.

### URL form: `location.origin + "/<path>/" + state.code`
**Choice:** Build with `location.origin` so the link inherits scheme + host + port. Path is `/room/<code>` on desktop and `/m/<code>` on mobile.
**Why:** Works equally for local dev (`http://127.0.0.1:8000`), LAN play, and production. The recipient pastes once and lands in the right UI.

### `navigator.share` payload
**Choice:**
```js
{
  title: "Princess Card Game",
  text: `Join my Princess room ${state.code}:`,
  url: roomUrl,
}
```
**Why:** Title is the friendly app name. Text gives context for clients that don't render the URL preview (some SMS apps). URL is the deep link.

### Fallback order: share → clipboard → silent no-op
**Choice:**
```js
if (navigator.share) {
  try { await navigator.share(payload); return; }
  catch (e) { if (e.name === "AbortError") return; /* try clipboard */ }
}
try { await navigator.clipboard.writeText(url); flashCopied(); }
catch { /* no clipboard either — silent */ }
```
**Why:** Share is best; clipboard is OK; nothing crashes if neither works. `AbortError` is the user cancelling — also a no-op (don't flash "Copied").

### Visual feedback: button text becomes "Copied!" for 1.5s
**Choice:** Desktop button label flips to **Copied!** for 1500ms, then back. Mobile lobby's `↗` icon button gets a one-shot toast (or label flash if it has a label).
**Why:** Confirms the action without a heavy modal. 1.5s is long enough to read, short enough to not block re-share.

### No share-sheet auto-fill for code-input
**Choice:** If the user later wants to *receive* a shared link, they paste the URL into the browser, which the server already handles via `/room/<code>` and `/m/<code>` routes (the existing `index.html` / `mobile.html` read the path and pre-fill the code input).
**Why:** No new code path needed for the receiver side; the deep-link routing already works.

### Buttons are tap-target compliant
**Choice:** Mobile icon buttons follow the existing `.m-icon` pattern (44 × 44 px). Desktop button reuses the standard lobby button sizing.
**Why:** Accessibility floor.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| `navigator.share` requires HTTPS in production; users testing on `http://1.2.3.4` (LAN, non-localhost) see clipboard-only fallback | Acceptable — clipboard still works, which is what we have today. |
| Some browsers reject `share()` silently if the user denies a permission prompt | Treated the same as `AbortError`; no "Copied" flash, no error to the user. |
| Mobile `↗` icon may not be self-explanatory | Pair with `aria-label="Share room link"`; the on-tap behavior is one tap to validate. We can add a tiny tooltip later if a user reports confusion. |
| Race: user taps Share while the lobby broadcast hasn't yet set `state.code` | Guard with `if (!state.code) return;` — same pattern the existing tap-to-copy uses. |
| `navigator.clipboard` requires secure context (HTTPS or localhost) | Already true today — the existing tap-to-copy has the same constraint. Document via a console warning during dev. |

## Migration Plan

1. **Desktop HTML/CSS:** add the **Share link** button near the room code; reuse existing button styles.
2. **Desktop JS:** implement `shareRoomLink()` with the share→clipboard chain; wire the button.
3. **Mobile HTML/CSS:** add an icon button next to the lobby room code and in the game-view top bar.
4. **Mobile JS:** implement `shareRoomLink()` with the share→clipboard chain; wire the buttons.
5. **CHANGELOG.md** entry.
6. Commit + push + CI + merge.

Rollback: revert four static files.

## Open Questions

- Should the desktop button copy `/m/<code>` instead of `/room/<code>` to optimize for the common case of recipients being on phones? Recommendation: stick with `/room/<code>` — desktop sender → desktop link; recipients can hit `/m/<code>` themselves if they prefer. Cross-UI mind-reading is a trap.
