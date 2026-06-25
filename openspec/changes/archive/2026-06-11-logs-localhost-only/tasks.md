## 1. Localhost guard dependency

- [x] 1.1 In `princess/server.py`, add a `require_localhost` async dependency function that accepts a `Request`, checks `request.client.host` against `{"127.0.0.1", "::1"}`, and raises `HTTPException(403, "forbidden")` for any non-loopback address. Treat `request.client is None` as non-loopback (fail closed).
- [x] 1.2 Apply `Depends(require_localhost)` to all three log route definitions: `GET /api/logs`, `GET /api/logs/download`, and `DELETE /api/logs`.

## 2. Tests

- [x] 2.1 In `tests/test_server.py` (or `tests/test_logging.py`), add tests for each of the three endpoints that simulate a non-loopback client (e.g. `client.get("/api/logs", headers={"x-forwarded-for": "1.2.3.4"})` won't work — use `app.dependency_overrides` or a custom `TestClient` with a spoofed `scope["client"]` to set a non-loopback IP) and assert HTTP 403.
- [x] 2.2 Add tests that simulate a loopback client (`127.0.0.1`) on all three endpoints and assert the expected success responses (200/200/200 with correct bodies).
- [x] 2.3 Add a test that confirms `request.client is None` also returns 403 (fail-closed path).

## 3. Docs & quality gates

- [x] 3.1 Update `README.md` to note that `/api/logs*` endpoints are restricted to localhost.
- [x] 3.2 Add an entry to the `CHANGELOG.md` `[Unreleased]` section noting the localhost restriction.
- [x] 3.3 Run `black`, `pylint` (≥8.0), and `pytest`; fix any findings.
- [x] 3.4 Run `openspec validate logs-localhost-only` and confirm it passes.
