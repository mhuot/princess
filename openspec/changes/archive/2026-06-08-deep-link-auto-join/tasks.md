## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/deep-link-auto-join`.

## 2. Desktop frontend

- [ ] 2.1 In `static/index.html`, inside the lobby `#lobby` section, add a hidden focused-view block (anywhere alongside the existing form):

  ```html
  <section id="focused-join" hidden>
    <h2 id="focused-heading">Join room <span id="focused-code"></span></h2>
    <label for="focused-name">Your name</label>
    <input id="focused-name" name="name" maxlength="20" autocomplete="nickname" />
    <button type="button" id="focused-join-btn" disabled>Join room</button>
    <div id="focused-error" role="alert" class="error-banner" hidden></div>
  </section>
  ```

  Keep the existing form (`#lobby-form`) intact — the focused view will hide it via `style.display = 'none'` or by toggling its parent's visibility.

- [ ] 2.2 In `static/app.js`:
  - Extract a `joinRoomBy(code, name)` helper that calls `postJSON("/api/rooms/<code>/join", {name})`, returns the response, and on success persists `princess_name`, `princess_session`, then opens the WS via the existing flow.
  - Refactor the existing manual `joinRoom()` to delegate to `joinRoomBy(form_code, form_name)`.
  - Add `autoJoinFromUrl()` that:
    1. Parses `location.pathname` for `/room/<code>`. If no match, return.
    2. Reads `sessionStorage.princess_session`. If `code` matches, try `reconnectWith(stored.pid, stored.name)`. On WS rejection or error, clear the sentinel and continue.
    3. Reads `localStorage.princess_name`. If present, call `joinRoomBy(urlCode, savedName)`. On success, return. On failure, fall through.
    4. Shows the focused view: set `#focused-code` to `urlCode`, hide `#lobby-form`, show `#focused-join`. Wire a single `input` listener on `#focused-name` that toggles `#focused-join-btn.disabled = !$("#focused-name").value.trim()`. Wire the button's click to `joinRoomBy(urlCode, $("#focused-name").value.trim())` (button is already disabled when the trimmed value is empty, so the click handler can trust the input).
  - Call `autoJoinFromUrl()` at the end of the DOM-ready handler.

- [ ] 2.3 Update the existing `createRoom()` and `joinRoomBy()` success paths to write `princess_name` to localStorage and `princess_session` to sessionStorage (both best-effort, swallow exceptions).

## 3. Mobile frontend

- [ ] 3.1 In `static/mobile.html`, inside `#m-landing`, add a hidden focused-view block:

  ```html
  <section id="m-focused-join" hidden>
    <h2 id="m-focused-heading">Join room <span id="m-focused-code"></span></h2>
    <label for="m-focused-name">Your name</label>
    <input id="m-focused-name" name="name" maxlength="20" autocomplete="nickname" />
    <button type="button" id="m-focused-join-btn" class="m-primary" disabled>Join room</button>
  </section>
  ```

- [ ] 3.2 In `static/mobile.js`:
  - Extract a `joinRoomBy(code, name)` helper mirroring desktop's behavior (writes localStorage + sessionStorage, opens the mobile WS).
  - Refactor existing manual `joinRoom()` to delegate.
  - Add `autoJoinFromUrl()` with the same three-tier chain as desktop, targeting mobile element ids (`#m-focused-join`, `#m-focused-code`, `#m-focused-name`, `#m-focused-join-btn`).
  - Wire an `input` listener on `#m-focused-name` that toggles `#m-focused-join-btn.disabled` based on `trim()`.
  - Wire the new button's click to call `joinRoomBy(urlCode, $("#m-focused-name").value.trim())`.
  - Call `autoJoinFromUrl()` at the end of `DOMContentLoaded`.

## 4. Shared session helpers

- [ ] 4.1 Both files: when the WS connects successfully, do nothing extra (the join already wrote the sentinel). When the WS rejects (close code 1008 / unknown pid / etc.), clear `sessionStorage.princess_session` so the next refresh falls through to tier 2 or 3.

- [ ] 4.2 Wrap all `localStorage` / `sessionStorage` writes in `try { ... } catch { }` so a quota or private-browsing error doesn't break the join.

## 5. CSS

- [ ] 5.1 In `static/styles.css`, add a small block for `#focused-join` (centered card with the existing accent palette). Reuse `.error-banner`.
- [ ] 5.2 In `static/mobile.css`, add similar block for `#m-focused-join` — full-width input, large submit button, single-column layout. Reuse `.m-primary`.

## 6. Docs

- [ ] 6.1 In `README.md`, near the share-link section, add a sentence:
  - "Friends who tap your `/m/<code>` (or `/room/<code>`) link land **directly in the room** — first-time visitors type just their name and tap Join; returning visitors auto-join with their saved name. The name is cached in localStorage; session state in sessionStorage (so a refresh keeps your seat)."

- [ ] 6.2 In `CHANGELOG.md` `## [Unreleased]` `### Added`:
  - "Deep links (`/room/<code>` and `/m/<code>`) now **auto-join** the room. First-time visitors see a focused name-only form (no Create-room clutter); returning visitors auto-join with their saved name. Page refreshes restore the seat via a session sentinel. [deep-link-auto-join]"

## 7. Verify

- [ ] 7.1 `black princess tests`.
- [ ] 7.2 `pylint princess tests` → 10.00/10.
- [ ] 7.3 `pytest -q` → green (no test changes needed — pure frontend).
- [ ] 7.4 `openspec validate --specs --strict` and `openspec validate deep-link-auto-join --strict`.
- [ ] 7.5 Update `scripts/smoke_test.py`:
  - **Mobile auto-join section:** open `/m/<code>` with no localStorage. Expect `#m-focused-join` visible, `#m-landing` create/join controls hidden, focused button text `Join room <code>`. Type a name and submit; expect the room to load.
  - **Saved-name re-visit:** persist a name via `page.evaluate("localStorage.setItem('princess_name','Mike')")`, then visit `/m/<code>`. Expect direct landing in the room with no focused view.
  - **Failure fallback:** visit `/m/ZZZZ` (non-existent code). Expect `#m-focused-join` to hide, `#m-landing` to show with `#m-code` prefilled, and an error in `#m-lobby-error`.
  - **Empty-name guard:** on `/m/<code>` with no saved name, the focused view is shown. Assert `#m-focused-join-btn.disabled === true`. Type `"  "` (whitespace) → button stays disabled. Type a real character → button enables. Clear → disables again.
  - **Trim on submit:** type `"  Pat  "` (with whitespace), click Join. After landing in the seated UI, assert `localStorage.princess_name === "Pat"` (no whitespace).

## 8. Ship

- [ ] 8.1 Commit: `deep-link-auto-join: Auto-join the room on /room/<code> and /m/<code>`.
- [ ] 8.2 Push the branch; open a PR.
- [ ] 8.3 Watch CI; auto-merge once green.

## 9. Wrap up

- [ ] 9.1 `openspec status --change deep-link-auto-join` → 4/4 done.
- [ ] 9.2 `/opsx:archive deep-link-auto-join` after merge.
