## ADDED Requirements

### Requirement: Health check endpoint

The server SHALL expose `GET /healthz` as an **unauthenticated**, cheap liveness probe suitable for nginx upstream health checks and external uptime monitors. The handler SHALL NOT perform any per-room work, engine work, or I/O beyond reading three in-memory counters.

The endpoint SHALL respond `200 OK` with a JSON body of shape:

```
{
  "status": "ok",
  "uptime_seconds": <int>,
  "rooms": <int>,
  "log_buffer_size": <int>
}
```

- `uptime_seconds` SHALL be the integer seconds since the application's startup time was captured (monotonic clock).
- `rooms` SHALL be the current count of rooms in the in-memory registry.
- `log_buffer_size` SHALL be the current count of entries in the in-memory ring buffer (not the buffer capacity).

The endpoint SHALL NOT require a `host_pid`, header, or cookie. It SHALL NOT consult the user-agent (no mobile redirect applies) and SHALL NOT emit any per-request log line at INFO level (DEBUG is acceptable but optional — health probes are high-frequency).

#### Scenario: Basic probe returns 200

- **WHEN** a client issues `GET /healthz` against a running server
- **THEN** the response status is 200 and the body is JSON with `status == "ok"`

#### Scenario: Payload includes diagnostic counters

- **WHEN** a client issues `GET /healthz` against a server with two active rooms and 47 buffered log entries
- **THEN** the body contains `rooms == 2` and `log_buffer_size == 47`

#### Scenario: Uptime reflects process age

- **WHEN** `GET /healthz` is called after the server has been running for at least 1 second
- **THEN** `uptime_seconds` is a non-negative integer greater than or equal to 1

#### Scenario: No authentication required

- **WHEN** `GET /healthz` is called with no body, no auth header, and no cookies
- **THEN** the response status is 200

#### Scenario: Mobile UA does not redirect

- **WHEN** `GET /healthz` is called with a mobile User-Agent header
- **THEN** the response is the JSON payload, NOT a 302 redirect to `/m`
