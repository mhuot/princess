## ADDED Requirements

### Requirement: Per-IP rate limiting on room mutation endpoints

The server SHALL apply per-client-IP rate limits to four HTTP endpoints to protect the in-memory room registry from flooding and to deter scripted enumeration of the 4-character room-code namespace.

The enforced limits SHALL be:

- `POST /api/rooms` — **6 requests per minute per IP**.
- `POST /api/rooms/{code}/join` — **30 requests per minute per IP**.
- `POST /api/rooms/{code}/bot` — **20 requests per minute per IP**.
- `POST /api/rooms/{code}/rename` — **30 requests per minute per IP**.

Each endpoint's quota SHALL be tracked independently — a client exhausting `/api/rooms` SHALL still be allowed to call `/join` up to that endpoint's own quota.

When a request exceeds its endpoint's quota, the server SHALL respond with **HTTP 429** and a JSON body of the form `{"detail": "<reason including the quota>"}` so existing client error helpers can surface the message verbatim.

All other HTTP endpoints (read endpoints, `/config`, `/start`, `/abort`, `/rematch`, `/leave`, `/remove_bot`, `/end_round`, mobile static routes) and all WebSocket traffic SHALL NOT be rate-limited.

#### Scenario: Create-room flood is throttled

- **WHEN** the same client IP issues more than 6 `POST /api/rooms` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429** with a `detail` field describing the exceeded quota

#### Scenario: Join flood is throttled

- **WHEN** the same client IP issues more than 30 `POST /api/rooms/{code}/join` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429**

#### Scenario: Bot-add flood is throttled

- **WHEN** the same client IP issues more than 20 `POST /api/rooms/{code}/bot` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429**

#### Scenario: Rename flood is throttled

- **WHEN** the same client IP issues more than 30 `POST /api/rooms/{code}/rename` requests within a 60-second window
- **THEN** at least one of the later requests in that window returns **HTTP 429**

#### Scenario: Per-endpoint quotas are independent

- **WHEN** a client IP has exhausted its `POST /api/rooms` quota for the current window
- **THEN** the same IP can still call `POST /api/rooms/{code}/join` up to that endpoint's own 30/minute quota

#### Scenario: Read endpoints are not rate-limited

- **WHEN** a client IP issues 1000 read requests in a minute (e.g. polling a public read endpoint or the mobile static page)
- **THEN** no request is rejected with HTTP 429 by the limiter

#### Scenario: WebSocket traffic is not rate-limited

- **WHEN** a connected client sends a high volume of WebSocket messages
- **THEN** no message is rejected with HTTP 429 by the limiter (engine-level rejections still apply)

### Requirement: Real client IP behind nginx

The rate-limiter's per-client key SHALL be the **original client IP** as recorded in the `X-Forwarded-For` request header set by the nginx reverse proxy. When the header contains a comma-separated list, the first entry SHALL be used as the client IP. When the header is absent, the server SHALL fall back to `request.client.host`.

#### Scenario: First XFF entry is used as the key

- **WHEN** a request arrives with `X-Forwarded-For: 203.0.113.7, 10.0.0.1`
- **THEN** the rate-limiter treats `203.0.113.7` as the client identity

#### Scenario: Fallback to direct peer when XFF missing

- **WHEN** a request arrives with no `X-Forwarded-For` header (e.g. direct local call in dev)
- **THEN** the rate-limiter uses `request.client.host` as the client identity

#### Scenario: Two distinct client IPs share independent buckets

- **WHEN** IP `A` exhausts its `POST /api/rooms` quota and IP `B` then issues a `POST /api/rooms` request
- **THEN** IP `B`'s request is served normally (its own bucket is empty)

### Requirement: Rate limiting can be disabled for dev and tests

The server SHALL honor the environment variable `PRINCESS_RATE_LIMIT_DISABLED`. When the variable is set to `1` at process startup, the limiter SHALL be disabled and no request SHALL be rejected with HTTP 429 by the limiter, regardless of volume.

The default test suite SHALL set `PRINCESS_RATE_LIMIT_DISABLED=1` before importing the server module, so existing tests are not affected by the new limits. A dedicated test SHALL clear the variable (or build a fresh app instance with the variable cleared) to verify enforcement.

#### Scenario: Env var disables enforcement

- **WHEN** the server starts with `PRINCESS_RATE_LIMIT_DISABLED=1` and the same client IP issues 100 `POST /api/rooms` requests in one minute
- **THEN** zero requests are rejected with HTTP 429 by the limiter

#### Scenario: Default (env var unset) enforces limits

- **WHEN** the server starts with `PRINCESS_RATE_LIMIT_DISABLED` unset (or set to any value other than `1`) and the same client IP exceeds an endpoint's quota
- **THEN** the over-quota requests are rejected with HTTP 429
