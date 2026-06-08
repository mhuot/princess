## Why

A phone user lands on `princess.geekpark.com/` and gets the desktop UI — dense, with the chrome (status entries, Special-cards collapsible, Rename/Quit buttons) sandwiched between the pile and the hand. They can't see opponents + pile + hand at a glance. The mobile UI at `/m` is designed exactly for this case but only people who know the URL ever find it.

Auto-redirect mobile user agents from `/` (and `/room/{code}`) to `/m` (and `/m/{code}`) so visitors land on the right interface for their device. Keep an explicit escape hatch (`?desktop=1`) for power users who want to force the desktop UI on a phone.

## What Changes

- **`GET /` and `GET /room/{code}`** SHALL detect mobile user agents and `302` redirect to the corresponding mobile path:
  - `/` → `/m`
  - `/room/{code}` → `/m/{code}`
- **Detection:** the standard "`Mobi`" substring check against the `User-Agent` header — covers iPhone Safari, Chrome Android, Firefox Mobile, Edge Mobile, Samsung Internet, etc. Tablets like iPad (which omit `Mobi`) get the desktop UI by default; this matches their generally-larger screen and is the same heuristic Chrome itself uses.
- **Escape hatch:** if the request URL has a `desktop=1` query param (or the path was reached via a redirect from `/m` — we don't want loops), serve the desktop UI without redirect. A persisted `princess_prefer_desktop=1` cookie also opts the user out for the session.
- **No redirect on `/m` routes** — they always serve the mobile UI regardless of user agent. (A desktop visitor who navigates to `/m` directly is being explicit.)
- **Add a small "View desktop site" link to the mobile UI footer** so a mobile user who *wants* desktop has a one-tap path. Tapping it sets the `princess_prefer_desktop=1` cookie and redirects to `/` (which now sees the cookie and doesn't redirect back).
- **Mirror affordance on desktop:** a small "Mobile site" link in the desktop footer for the reverse direction — clears the cookie and goes to `/m`.

## Capabilities

### Modified Capabilities

- `room-server`: `GET /` and `GET /room/{code}` gain UA-based mobile-redirect behavior with an explicit escape hatch.
- `web-frontend`: footer gains a "Mobile site" link.
- `mobile-frontend`: footer gains a "View desktop site" link.

### New Capabilities

(none)

## Impact

- **Affected code:**
  - `princess/server.py` — `index()` and `room_page()` inspect `request.headers["user-agent"]`, the query string, and the cookie; return a `RedirectResponse` if appropriate.
  - `static/index.html` — add a small `<a href="/m" id="switch-to-mobile">Mobile site</a>` in the footer (next to "View logs"). A tiny `<script>` clears the cookie before navigating.
  - `static/mobile.html` — add a `<button id="m-switch-to-desktop">View desktop site</button>` in a small bottom-of-screen area (or as a footer link in the lobby). Sets the cookie and navigates to `/`.
  - `static/app.js` — handle the cookie-clear click on `#switch-to-mobile`.
  - `static/mobile.js` — handle the cookie-set click on `#m-switch-to-desktop`.
  - `tests/test_server.py` — server tests asserting redirect behavior for various UAs and override paths.
- **Affected APIs:** none changed; existing routes just gain redirect behavior for some requests.
- **Affected dependencies:** none.
- **Docs touched:** `README.md` (mention the auto-redirect), `CHANGELOG.md` `### Added`.
- **Out of scope:**
  - Detecting tablets specifically (they get desktop UI; we accept that for v1).
  - Persisting the preference server-side per user (cookie is fine).
  - Redirecting `/logs`, `/api/*`, or WebSocket paths — only the two HTML page routes.
  - Choosing the right UI for embedded webviews / Discord activities / etc. (whatever the WebView UA says wins).
