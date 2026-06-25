## Context

The three log endpoints (`GET /api/logs`, `GET /api/logs/download`, `DELETE /api/logs`) are currently accessible to any HTTP client. The application is deployed behind an nginx reverse proxy that forwards all traffic; there is no existing network-layer restriction on these routes. The fix must work at the application layer so it is effective regardless of deployment topology (local dev, Docker + nginx, bare uvicorn).

FastAPI provides a `Request` object that exposes `request.client.host` — the IP address of the connecting client as seen by the ASGI layer (which is the uvicorn worker, not a downstream proxy). Since nginx runs on the same host and proxies to uvicorn on an internal Docker network, requests that originate externally arrive at uvicorn with the nginx container IP, not a loopback address. Requests made directly by an operator (e.g. `curl http://localhost:8000/api/logs` from inside the container or on the host) arrive with `127.0.0.1`.

## Goals / Non-Goals

**Goals:**
- Any request to the three log endpoints from a non-loopback source IP receives `403 Forbidden`.
- Operator access from the same host (loopback) continues to work unchanged.
- The check is self-contained in one reusable FastAPI dependency.

**Non-Goals:**
- Changing the nginx configuration or firewall rules (out of scope; application-layer fix is sufficient).
- Adding authentication (username/password, API key) to the log endpoints — localhost restriction is the chosen mechanism.
- Restricting any other endpoint.
- Handling `X-Forwarded-For` or other proxy headers for the loopback check — doing so would let an external client spoof the header and bypass the guard.

## Decisions

**Decision: FastAPI `Depends` on a `require_localhost` function, not middleware.**

A dependency applied per-route is the lowest-blast-radius option: it touches exactly the three routes, leaves every other route unaffected, and is easy to test by injecting a fake `Request` with an arbitrary `client.host`. Alternatives considered:

- *Middleware*: Would need to filter by path string, coupling it to route naming; harder to test in isolation; risk of accidentally blocking other routes during future refactors.
- *Nginx `allow 127.0.0.1; deny all;` location block*: Requires coordinating nginx config changes and adds a deployment dependency. Also doesn't protect local dev (bare uvicorn) where nginx isn't involved.
- *Separate internal FastAPI app / sub-application*: Excessive complexity for three routes.

**Decision: Check `request.client.host` directly; do NOT honour `X-Forwarded-For`.**

`X-Forwarded-For` is attacker-controlled. A check on the direct connection IP is unforgeable. The deployment model (nginx on the same host) means external requests arrive at uvicorn from the nginx container IP (non-loopback), and operator shell requests arrive from 127.0.0.1 — the distinction is reliable.

**Decision: Loopback set is `{"127.0.0.1", "::1"}`.**

Covers both IPv4 and IPv6 loopback. `localhost` resolves to one of these at the OS layer; the check sees the resolved IP, not the hostname.

## Risks / Trade-offs

- [Operator locked out in unusual topologies] If an operator accesses uvicorn from a non-loopback address (e.g. port-forwarded externally without nginx), they get 403. → Documented; expected deployment model is always nginx-on-same-host or direct container shell.
- [`request.client` is None] FastAPI sets `request.client` to `None` in some test harness configurations. → The dependency treats `None` as non-loopback (fails closed), and tests must inject a fake `Request` with an explicit `client`.
- [Future reverse proxy on a different host] If nginx moves to a separate machine, operator loopback access also breaks. → Not a current concern; noted as a future migration consideration in the open questions of any infra change.

## Migration Plan

Pure code change; no data migration. Standard deploy via push to `main` triggers the CI pipeline and container rebuild. Rollback is reverting the commit. No persistent state is affected.
