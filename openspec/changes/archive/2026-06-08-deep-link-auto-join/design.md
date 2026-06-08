## Context

The current deep-link behavior was a half-step: extract the code from `location.pathname`, drop it into the code input, then sit on the landing page waiting for the user to tap **Join room**. That made sense as a v1 — until users started sharing links and friends kept asking "where's the room? what do I do?"

Three things change in this round:

1. **The action is implicit.** Landing on `/m/AB12` means "join AB12." We do the join automatically.
2. **The name is recalled.** Users who have joined before don't re-type their name.
3. **Refresh-survives.** A page refresh on `/m/AB12` after joining doesn't kick the user back to the lobby — it reconnects them to their existing seat.

## Goals / Non-Goals

**Goals:**
- One-tap join from a shared link for first-time visitors (name + auto-submit).
- Zero-tap reconnect for users who already have a saved name AND a sentinel session.
- Survives a page refresh without dropping the seat.
- Same UX semantics on desktop and mobile.

**Non-Goals:**
- Cross-device session restore (Bluetooth handoff, etc.).
- Sessions that survive closing the browser entirely (`sessionStorage` dies with the tab; that's intentional).
- A "switch account" affordance — users use the existing Rename button.
- Auto-join from non-code paths (`/`, `/m`, `/logs`).
- Server-side session validation beyond what the join endpoint already enforces.

## Decisions

### Three-tier auto-join chain
**Choice:**
1. **Session sentinel** (sessionStorage) — `{code, pid, name}` from this tab's last successful join. If `code` matches the URL and we can reopen the WS with that `pid`, restore.
2. **Saved name** (localStorage) — call the existing `joinRoom(code, savedName)` directly. Get a new `pid` back. Stash a fresh session sentinel.
3. **Focused name view** — single input + "Join room ABCD" button. On submit, save the name and join.
**Why:** Each tier handles a real scenario without falling back to the lobby. Tier 1 handles refresh and tab-restore. Tier 2 handles "second-time visitor." Tier 3 handles "brand new visitor."

### Name persistence: localStorage
**Choice:** `localStorage.princess_name` (key, no namespacing) holds the last successful name.
**Why:** Users typically use the same name across sessions. Single key keeps it simple. Privacy: there's nothing sensitive — it's a display name.

### Session sentinel: sessionStorage
**Choice:** `sessionStorage.princess_session = JSON.stringify({code, pid, name})` written on every successful create/join.
**Why:** `sessionStorage` dies with the tab — exactly the lifetime we want. If you close the tab, your seat went stale (the room may have evicted you anyway). If you only refresh, you stay.

### Verify the pid via WS, not a separate REST call
**Choice:** Don't add a new "is this pid still valid?" endpoint. Just try the WS connection — the server already rejects unknown pid/code combinations.
**Why:** Zero new server surface area. The WS open/reject is itself the validation.

### Focused name view, not a modal
**Choice:** Hide the main lobby form (Create/Join buttons, second code field), reveal a small block with only the name input and a `Join room <code>` button. No modal overlay.
**Why:** Modals on mobile compete with keyboard popups. Inline form fits naturally above the soft keyboard. On desktop the focused view is just a compact lobby section — cleaner than a dialog.

### Failure → fall back to the regular lobby
**Choice:** If the join API returns any error, hide the focused view, show the regular lobby with the code prefilled and the error message in the existing error slot.
**Why:** "Auto-join failed" is the same state as "manual join failed" — the user already knows that screen. No new error UI to design.

### Host's URL is rewritten, but auto-join only kicks in WHEN there's no current session for *that same code*
**Choice:** The host calls `history.replaceState` after creating a room. If the host refreshes, the sentinel-based reconnect runs first. If the sentinel exists AND its `code` matches the URL, we reconnect with the host's existing pid instead of joining as a new player.
**Why:** Preserves host identity across refresh. Without this, a host refreshing their own room would create a second seat for themselves — bad.

### Auto-join only fires when the URL path provides the code
**Choice:** `/room/CODE` and `/m/CODE` (exact-match). Plain `/` and `/m` don't auto-join.
**Why:** Plain `/` is the user explicitly landing on the lobby with intent to create or browse — auto-joining a random room they haven't chosen would be wrong.

### Storage write is best-effort
**Choice:** If `localStorage.setItem` throws (private browsing, quota), the join still proceeds. The next visit just doesn't auto-recall.
**Why:** Storage is a nicety, not a correctness requirement. Don't let it break the happy path.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Saved name leaks across rooms (user joined with "Mike" then wants to join another room as "M") | The Rename button covers it; the saved name is just the default. We could add a "saved as Mike — change?" link in the focused view but it adds clutter for the common case. |
| sessionStorage misalignment causes a host to lose pid on tab restore | Tab restore via the OS *does* restore sessionStorage in modern browsers. If it ever doesn't, we fall through to a new join — the host loses host status, but the room continues. Acceptable. |
| Auto-join fires before the WebSocket-ready check finishes and gets confused | Order: REST `/join` first (returns pid), THEN open WS with that pid. Same as the existing manual flow. No race. |
| User in private/incognito mode never auto-recalls | Storage fails silently. They get the focused name view every time. No worse than today. |
| A bot stranger discovers a `/m/<code>` URL and auto-joins | Same risk as today, where they could manually join. Room codes are short (4 chars); cap-on-seats is the real protection (already implemented). |

## Migration Plan

1. **`static/app.js`:**
   - Refactor the existing manual `joinRoom()` to call a `joinRoomBy(code, name)` helper that returns the join response.
   - Save `princess_name` to localStorage on every successful join.
   - Save `princess_session` to sessionStorage on every successful join/create.
   - On DOM-ready, after wiring listeners, call `autoJoinFromUrl()`:
     - If path matches `/room/<code>`, try sentinel reconnect → saved-name join → focused view.
     - The focused view is a hidden block in `index.html` with one input + one button.
2. **`static/index.html`:** add a `<section id="focused-join" hidden>` with `<label>Your name</label> <input id="focused-name"> <button id="focused-join-btn">Join room <span id="focused-code"></span></button>`. Style with existing classes.
3. **`static/mobile.js`:** same logic; the focused view lives inside `#m-landing`.
4. **`static/mobile.html`:** add `<section id="m-focused-join" hidden>` similar to desktop. Reuse `.m-primary` button style.
5. **CHANGELOG, README** — short notes.
6. Update `scripts/smoke_test.py` to add an auto-join section: visit `/m/<code>` with no saved name → focused view appears; with saved name → land directly in the room.
7. Commit + push + CI + merge.

Rollback: revert the four static files.

## Open Questions

- Should the focused view also let the user pre-pick "I'm a bot" — i.e., let visitors join as autonomous? **Recommendation:** no. Out of scope; not how the project models bots.
- Should host status be transferable via deep link (e.g., `/m/AB12?host=token`)? **Recommendation:** no. Host is whoever created the room; that's the model.
