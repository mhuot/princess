## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-ua-redirect`.

## 2. Server

- [ ] 2.1 In `princess/server.py`, add a helper:

  ```python
  def _wants_mobile_redirect(request: Request) -> bool:
      """True iff a desktop route should 302 to its /m equivalent."""
      if request.query_params.get("desktop") == "1":
          return False
      if request.cookies.get("princess_prefer_desktop") == "1":
          return False
      ua = request.headers.get("user-agent", "")
      return "Mobi" in ua
  ```

- [ ] 2.2 Change `index()` and `room_page()` to accept the `Request` and return `RedirectResponse` when `_wants_mobile_redirect(...)` is True:

  ```python
  @app.get("/")
  async def index(request: Request):
      if _wants_mobile_redirect(request):
          return RedirectResponse("/m", status_code=302)
      return FileResponse(STATIC_DIR / "index.html")

  @app.get("/room/{code}")
  async def room_page(request: Request, code: str):
      if _wants_mobile_redirect(request):
          return RedirectResponse(f"/m/{code}", status_code=302)
      return FileResponse(STATIC_DIR / "index.html")
  ```

  Add the necessary imports: `from fastapi import Request` and `from fastapi.responses import RedirectResponse`.

- [ ] 2.3 Leave `mobile_index()` and `mobile_room_page()` untouched. They never redirect.

## 3. Server tests

- [ ] 3.1 In `tests/test_server.py`, add a fixture or helper that builds a `TestClient` and lets you pass custom headers.

- [ ] 3.2 Add the following cases:
  - `test_index_serves_desktop_for_desktop_ua` — `GET /` with a Mac Safari UA returns 200 and HTML containing `<title>Princess Card Game</title>`.
  - `test_index_redirects_mobile_ua_to_m` — `GET /` with an iPhone UA returns 302 and `Location: /m`. Use `follow_redirects=False`.
  - `test_room_page_redirects_mobile_ua` — `GET /room/AB12` with iPhone UA returns 302 and `Location: /m/AB12`.
  - `test_desktop_query_override_blocks_redirect` — `GET /?desktop=1` with iPhone UA returns 200 desktop HTML.
  - `test_cookie_override_blocks_redirect` — `GET /` with iPhone UA and the `princess_prefer_desktop=1` cookie returns 200 desktop HTML.
  - `test_m_serves_mobile_for_desktop_ua` — `GET /m` with Mac Safari UA returns 200 and HTML containing `<title>Princess — mobile</title>`.
  - `test_ipad_serves_desktop` — `GET /` with an iPad UA (no `Mobi` substring) returns 200 desktop HTML.

## 4. Desktop frontend

- [ ] 4.1 In `static/index.html`, locate the existing footer. Add a "Mobile site" link near "View logs":

  ```html
  <p class="muted">
    Licensed under Apache 2.0.
    <a href="/logs" target="_blank" rel="noopener">View logs</a>
    ·
    <a id="switch-to-mobile" href="/m">Mobile site</a>
  </p>
  ```

- [ ] 4.2 In `static/app.js`, wire the click handler to clear the cookie before navigation:

  ```js
  document.getElementById("switch-to-mobile")?.addEventListener("click", () => {
    document.cookie = "princess_prefer_desktop=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });
  ```

  (No `preventDefault` — the link still navigates after the cookie is cleared.)

## 5. Mobile frontend

- [ ] 5.1 In `static/mobile.html`, add a tiny footer-style link inside `#m-room` (so it's visible after joining a room) and a duplicate inside `#m-landing` (so a desktop user who hits `/m` and wants `/` can switch back without joining first):

  ```html
  <p class="m-muted m-switch-row">
    <button type="button" id="m-switch-to-desktop" class="m-link">View desktop site</button>
  </p>
  ```

  Or use a `<a>` styled appropriately; both work. Pick one. Place it after the existing `#m-waiting` line in the lobby section.

- [ ] 5.2 In `static/mobile.css`, add:

  ```css
  .m-link {
    background: none;
    border: none;
    color: var(--accent);
    text-decoration: underline;
    padding: 0;
    cursor: pointer;
    font: inherit;
    min-height: auto;
  }
  .m-switch-row { margin-top: 1rem; text-align: center; }
  ```

- [ ] 5.3 In `static/mobile.js`, wire the click handler:

  ```js
  document.getElementById("m-switch-to-desktop")?.addEventListener("click", () => {
    document.cookie = "princess_prefer_desktop=1; Path=/";
    location.href = "/";
  });
  ```

## 6. Docs

- [ ] 6.1 In `README.md`, near the URL listing, add a sentence:
  > "Phones are auto-redirected from `/` to `/m`. To force the desktop UI on a phone, append `?desktop=1` or use the **View desktop site** link in the mobile lobby."

- [ ] 6.2 In `CHANGELOG.md` `## [Unreleased]`, append under `### Added`:
  - "Phones are auto-redirected from `/` and `/room/<code>` to `/m` and `/m/<code>`. Override with `?desktop=1` or the **View desktop site** link in the mobile lobby. The reverse-path **Mobile site** link lives in the desktop footer. [mobile-ua-redirect]"

## 7. Verify

- [ ] 7.1 `black princess tests`.
- [ ] 7.2 `pylint princess tests` → 10.00/10.
- [ ] 7.3 `pytest -q` — green; the new server tests pass.
- [ ] 7.4 `openspec validate --specs --strict` and `openspec validate mobile-ua-redirect --strict`.
- [ ] 7.5 Update `scripts/smoke_test.py` to navigate from `/` with a mobile UA and assert it lands on `/m`. (Playwright's `make_mobile_context` already sets a mobile UA via the iPhone string.)
- [ ] 7.6 Manual smoke on the deployed site: visit `https://princess.geekpark.com/` from a phone → expect to land on `/m`. Visit `https://princess.geekpark.com/?desktop=1` from a phone → expect the desktop UI.

## 8. Ship

- [ ] 8.1 Commit: `mobile-ua-redirect: 302 phones from / to /m + escape hatches`.
- [ ] 8.2 Push the branch; open a PR.
- [ ] 8.3 Watch CI; auto-merge once green.

## 9. Wrap up

- [ ] 9.1 `openspec status --change mobile-ua-redirect` → 4/4 done.
- [ ] 9.2 `/opsx:archive mobile-ua-redirect` after merge.
