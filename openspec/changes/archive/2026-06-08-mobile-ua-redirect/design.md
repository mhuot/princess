## Context

The deployed site has two parallel UIs:
- `/` (and `/room/{code}`) → `static/index.html` (desktop layout)
- `/m` (and `/m/{code}`) → `static/mobile.html` (touch-friendly layout)

Today the server has no idea which one to send anyone — visiting `princess.geekpark.com/` from a phone gives you the desktop UI, dense and awkward. We add a small UA-sniff at the two desktop entry points and 302 to the mobile equivalents when the request is from a phone.

The standard test today is **substring `"Mobi"` in the User-Agent string** — this is the test Chrome itself recommends and what every Mobi-detection library reduces to. It matches:

- iOS Safari: `Mozilla/5.0 (iPhone; ...) ... Mobile/15E148 Safari/...`
- Chrome Android: `... Chrome/... Mobile Safari/...`
- Firefox Android: `... Mobile; rv:... ) Gecko/... Firefox/...`
- Samsung Internet: `... Mobile Safari/...`

Tablets like iPad explicitly do NOT include `Mobi` — Apple removed it in 2019. So iPads get the desktop UI by default, which matches their larger viewport.

## Goals / Non-Goals

**Goals:**
- A phone user typing `princess.geekpark.com` lands on the mobile UI without any extra step.
- A phone user with a deep link `princess.geekpark.com/room/AB12` lands on `/m/AB12`.
- Power users (developer testing, accessibility) can force the desktop UI on a phone.
- The reverse path (desktop user opens `/m` for a quick check) keeps working.

**Non-Goals:**
- Detecting tablets as a third class.
- Server-side per-user preference storage. A cookie is fine.
- Redirecting non-HTML paths (`/logs`, `/api`, `/ws`).
- Choosing the right UI for embedded webviews / Discord activities — accept whatever UA reports.

## Decisions

### `"Mobi"` substring check, not a library
**Choice:** `if "Mobi" in request.headers.get("user-agent", ""):` redirect.
**Why:** Matches Chrome's own detection. No dependency, no maintenance, immune to UA evolution. The `case-sensitive` check is intentional — both `Mobi` and `Mobile` match.

### `302` redirect, not `301`
**Choice:** Use `status_code=302` (temporary).
**Why:** Behavior may change. A `301` would cache aggressively in browsers — making future tweaks to the redirect rule invisible until cache-bust. `302` is safe.

### Escape hatches: query param + cookie
**Choice:** `?desktop=1` opts out for that request. A cookie (`princess_prefer_desktop=1`) opts out persistently. The desktop "Mobile site" link clears the cookie and navigates to `/m`.
**Why:** Query param is testable and shareable (`?desktop=1` URLs work from any device). Cookie persists for the session, so a phone user with a strong preference for desktop doesn't have to re-add `?desktop=1` on every page navigation.

### Cookie name and lifetime
**Choice:** `princess_prefer_desktop=1`, no `Expires`, `Path=/`. Session cookie — survives reloads, dies on browser close.
**Why:** Most users who pick "desktop on my phone" want it for the session. Cross-session persistence would surprise visitors months later who forgot they ticked it.

### Where to add the footer links
**Choice:** Desktop footer (where "View logs" already lives) gains a "Mobile site" link. Mobile lobby footer gains a "View desktop site" link.
**Why:** Both pages already have a small footer slot. The mobile footer link is below the lobby's content so it doesn't compete with play affordances.

### Reverse: do NOT redirect `/m` based on UA
**Choice:** `/m` always serves mobile, regardless of UA.
**Why:** A user who explicitly typed `/m` (or followed a `/m/<code>` shared link) made a choice. Bouncing them is rude.

### Don't redirect the WebSocket or API routes
**Choice:** Only the two HTML page handlers (`index()`, `room_page()`) get the redirect logic. `mobile_index()`, `mobile_room_page()`, `/api/...`, `/ws/...`, `/logs` are untouched.
**Why:** WebSocket and API consumers don't follow 302s. Logs viewer doesn't care.

### No redirect loops possible
**Choice:** The redirect only fires from `/` and `/room/{code}` → `/m...`. `/m...` never redirects. So there's no possible loop.

### Future: don't pre-emptively widen detection
**Choice:** Accept that iPads, foldables, and other tweener devices get desktop. If users complain, we tune later.
**Why:** The current check is the simplest reliable one. Custom logic per device class is a maintenance sink.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Power user on phone wants desktop UI and doesn't know `?desktop=1` exists | The mobile footer has a "View desktop site" link → cookie → desktop. Discoverable in one tap. |
| Crawlers / bots get redirected and never see the canonical desktop content | Google's mobile crawler reports a phone UA; redirecting it to the mobile equivalent is correct. Desktop crawler keeps getting desktop. |
| iPad users get desktop UI on a screen that's somewhat narrow in portrait | iPad portrait is 768+px wide — wide enough for the desktop UI to function. Tablets are an explicit non-goal for v1. |
| Cookie escape doesn't work if the user has cookies disabled | Query param `?desktop=1` still works on every request. |
| Server tests for redirect need a UA-controlled TestClient | FastAPI's TestClient accepts arbitrary headers. No issue. |

## Migration Plan

1. **`princess/server.py`:** factor a `_wants_mobile(request) -> bool` helper that takes user-agent, query, cookies. Both `index()` and `room_page()` use it; on True they return `RedirectResponse("/m" or "/m/{code}", status_code=302)`.
2. **Tests (`tests/test_server.py`):** new cases covering: iPhone UA → 302 to /m; desktop UA → index.html served; `?desktop=1` → index served despite mobile UA; cookie → index served despite mobile UA; `/room/AB12` with mobile UA → 302 to /m/AB12; `/m` with desktop UA → mobile served (no redirect).
3. **`static/index.html`:** add `<a id="switch-to-mobile" href="/m">Mobile site</a>` near `View logs`.
4. **`static/app.js`:** click handler on `#switch-to-mobile` clears the cookie via `document.cookie = "princess_prefer_desktop=; Path=/; Expires=...";` before letting the link navigate.
5. **`static/mobile.html`:** add `<button id="m-switch-to-desktop" class="m-link">View desktop site</button>` in a small footer.
6. **`static/mobile.css`:** small style for `.m-link` — text-only button styled as a link.
7. **`static/mobile.js`:** click handler sets the cookie and navigates to `/`.
8. **`README.md`:** one-line note about the auto-redirect + escape hatches.
9. **`CHANGELOG.md`:** `### Added` entry.
10. Commit + push + CI + merge. Verify on production by visiting `/` from a phone.

Rollback: revert the server.py + static files. Trivial.

## Open Questions

- Should the desktop "Mobile site" link be hidden on actual mobile UAs (since you'd already be on /m)? Recommendation: leave it visible. Symmetry; rare edge case.
- Should the cookie also affect future-session visits? Recommendation: no — session-only. Avoids stale preferences months later.
