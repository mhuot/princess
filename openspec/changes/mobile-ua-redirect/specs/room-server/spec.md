## MODIFIED Requirements

### Requirement: Mobile static routes

The server SHALL expose `GET /m` returning `static/mobile.html` and `GET /m/{code}` returning the same file. The shortcut URL form `<host>/m/<code>` allows a host to share a phone-friendly join link with friends.

These routes serve a **different** static page than `GET /` and `GET /room/{code}`; the latter pair continues to return `static/index.html` (the desktop UI) **unless** the request is from a mobile user agent and has no opt-out signal, in which case the server SHALL respond with a `302` redirect to the corresponding mobile path:

- `GET /` from a mobile UA → `302 Location: /m`
- `GET /room/{code}` from a mobile UA → `302 Location: /m/{code}`

A request is considered to come from a **mobile user agent** when the `User-Agent` header contains the case-sensitive substring `Mobi` (which matches `Mobile` and `Mobi/...` reliably across iOS Safari, Chrome Android, Firefox Mobile, Samsung Internet, etc.). Tablets such as iPads — which omit `Mobi` from their UA — are NOT considered mobile and continue to get the desktop UI.

The server SHALL skip the redirect (and serve `static/index.html` directly) when **any** of the following opt-out signals are present:

- A query-string parameter `desktop=1` (e.g. `GET /?desktop=1`).
- A request cookie `princess_prefer_desktop=1`.

The `/m` and `/m/{code}` routes SHALL NOT inspect the user agent. They always serve the mobile UI regardless of UA — a user who explicitly typed the `/m` URL has made a choice.

#### Scenario: /m serves mobile.html

- **WHEN** a `GET /m` request reaches the server
- **THEN** the response body is the contents of `static/mobile.html`

#### Scenario: /m/{code} serves mobile.html

- **WHEN** a `GET /m/AB12` request reaches the server
- **THEN** the response body is the contents of `static/mobile.html` (the page reads the code from `location.pathname` at runtime)

#### Scenario: Desktop UA on / serves index.html

- **WHEN** a `GET /` request reaches the server with a desktop User-Agent (e.g. `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/...`)
- **THEN** the response body is the contents of `static/index.html`

#### Scenario: Mobile UA on / redirects to /m

- **WHEN** a `GET /` request reaches the server with a mobile User-Agent (e.g. `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 ...) ... Mobile/15E148 Safari/...`)
- **THEN** the response is `302 Location: /m`

#### Scenario: Mobile UA on /room/{code} redirects to /m/{code}

- **WHEN** a `GET /room/AB12` request reaches the server with a mobile User-Agent
- **THEN** the response is `302 Location: /m/AB12`

#### Scenario: ?desktop=1 overrides the redirect

- **WHEN** a `GET /?desktop=1` request reaches the server with a mobile User-Agent
- **THEN** the response body is the contents of `static/index.html` (no redirect)

#### Scenario: princess_prefer_desktop cookie overrides the redirect

- **WHEN** a `GET /` request reaches the server with a mobile User-Agent and the cookie `princess_prefer_desktop=1`
- **THEN** the response body is the contents of `static/index.html` (no redirect)

#### Scenario: /m never redirects regardless of UA

- **WHEN** a desktop browser navigates to `/m` (with no `desktop=1` and no cookie)
- **THEN** the response body is the contents of `static/mobile.html` — no redirect to `/`

#### Scenario: iPad (tablet) gets desktop UI

- **WHEN** a `GET /` request reaches the server with an iPad UA that does NOT contain `Mobi`
- **THEN** the response body is the contents of `static/index.html` — no redirect
