## Why

A host shares `princess.geekpark.com/m/AB12` with a friend. The friend opens it and lands on the **lobby** — they have to type their name, look at the room-code box (already prefilled), and tap **Join room**. The fact that they used a deep link that already names a room is wasted: they still go through the same flow as someone who walked in cold.

A deep link's job is to short-circuit the join. Make it actually join.

## What Changes

- **Desktop and mobile both:** when the URL path is `/room/<code>` or `/m/<code>`, the frontend SHALL attempt to **auto-join** that room immediately on page load, without requiring a tap on **Join room**.
- **Name source:**
  - If `localStorage.princess_name` is set (cached from a prior visit), use it.
  - If not, render a **focused name-only view** that hides the Create/Join buttons and the second code field. The page shows just `Your name [____] [Join room AB12]`. After the user types a name and submits, the join fires.
  - The focused view also remembers the name to `localStorage.princess_name` on submit so future deep links auto-join without prompting.
  - The focused view's **Join** button SHALL be `disabled` while the name input is empty or contains only whitespace. The name SHALL be `trim()`-med before being saved or submitted, so a name like `"  Mike  "` is stored and joined as `"Mike"`.
- **Failure path:** if the join API returns an error (404 "room not found", 409 "room full", etc.), the focused view falls back to the full lobby with the code still prefilled and the error message shown — same behavior the user would see today after a failed manual join.
- **Host's own URL is safe:** when the host (or any already-seated player) creates/joins a room, the page's URL is rewritten via `history.replaceState` to `/room/<code>` (desktop) or `/m/<code>` (mobile). If they refresh, the auto-join would normally fire — but the player already has a `pid` for that room. We add a small **session sentinel**: when the join succeeds, we stash `sessionStorage.princess_session = {code, pid, name}`. On page load, if the sentinel matches the URL's code AND the pid is still valid (verified by reopening the WS, which the server validates), we reuse the pid instead of joining as a new player. If the WS rejects (the room or seat is gone), we fall through to a fresh join.
- **Cookie/UA redirect interaction:** the existing UA redirect from `/room/<code>` → `/m/<code>` (from `mobile-ua-redirect`) still fires first. Auto-join runs on the *destination* page, so a mobile user with a deep link still goes through `/m/<code>` → auto-join.

## Capabilities

### Modified Capabilities

- `web-frontend`: deep-link landing skips the lobby form and joins automatically when possible.
- `mobile-frontend`: same, with the focused name-only view styled as a bottom-sheet-friendly compact form.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `static/app.js` — extract a `joinRoom(code, name)` helper that the existing Join-room button already calls. On DOM-ready, if `location.pathname` matches `/room/<code>`, run a new `autoJoinFromUrl()` that:
    1. Checks `sessionStorage.princess_session` — if the code matches and reconnect succeeds, restore.
    2. Else reads `localStorage.princess_name` — if present, auto-call `joinRoom(code, savedName)`.
    3. Else renders the focused name-only view.
  - `static/index.html` — add a small focused-view element with a single name input + a "Join room <code>" button. Hidden by default; shown on auto-join when the name is unknown.
  - `static/mobile.js` — same pattern, mirrored to the mobile flow.
  - `static/mobile.html` — add a focused view in `#m-landing` (or a separate section) for the same purpose.
  - Session/local storage:
    - `localStorage.princess_name` — set on every successful join/create. Read on auto-join.
    - `sessionStorage.princess_session` — set on every successful join/create with `{code, pid, name}`. Read on auto-join to enable refresh-resume.
- **Affected APIs:** none. The server-side join endpoint already exists; we're just calling it differently from the client.
- **Affected dependencies:** none.
- **Docs touched:** `README.md` (the share-link section), `CHANGELOG.md` `### Added`.
- **Out of scope:**
  - Cross-device session resume (sessions are scoped to the browser tab via `sessionStorage`).
  - QR-code generation for deep links.
  - A confirmation modal ("Joining as Mike — change name?"). The existing Rename button covers post-join name changes.
  - Auto-join from `/m` or `/` (no code in the path) — those continue to show the full landing UI.
