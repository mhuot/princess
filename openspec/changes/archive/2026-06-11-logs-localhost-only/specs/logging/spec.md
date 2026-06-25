## MODIFIED Requirements

### Requirement: Paginated read endpoint

The server SHALL expose `GET /api/logs?since=<int>&limit=<int>` returning `{"entries": [...], "last_id": <int>, "capacity": <int>}`. Each entry SHALL have `id` and `line`. Only entries with `id > since` SHALL be returned, capped at `limit` (default 500). The endpoint SHALL be safe to poll. Access SHALL be restricted to loopback clients (source IP `127.0.0.1` or `::1`); requests from any other source IP SHALL receive `403 Forbidden`.

#### Scenario: Returns only new entries after a cursor

- **WHEN** the buffer contains entries with ids 100–110 and a loopback client requests `since=105`
- **THEN** the response `entries` contains exactly ids 106–110

#### Scenario: Non-loopback client is rejected

- **WHEN** a request arrives at `GET /api/logs` from a non-loopback source IP
- **THEN** the server responds with HTTP 403 Forbidden

### Requirement: Download endpoint

The server SHALL expose `GET /api/logs/download` returning the full current buffer as a `text/plain` response with `Content-Disposition: attachment; filename="princess.log"`. An empty buffer SHALL return a single-line placeholder rather than an empty body. Access SHALL be restricted to loopback clients (source IP `127.0.0.1` or `::1`); requests from any other source IP SHALL receive `403 Forbidden`.

#### Scenario: Browser downloads as attachment

- **WHEN** a loopback client requests `/api/logs/download`
- **THEN** the response carries `Content-Type: text/plain` and `Content-Disposition: attachment; filename="princess.log"`

#### Scenario: Non-loopback client is rejected

- **WHEN** a request arrives at `GET /api/logs/download` from a non-loopback source IP
- **THEN** the server responds with HTTP 403 Forbidden

### Requirement: Clear endpoint

The server SHALL expose `DELETE /api/logs` that empties the buffer and emits a single `INFO` entry recording the clear action. Access SHALL be restricted to loopback clients (source IP `127.0.0.1` or `::1`); requests from any other source IP SHALL receive `403 Forbidden`.

#### Scenario: Clear empties the buffer

- **WHEN** a loopback client calls `DELETE /api/logs`
- **THEN** the immediately subsequent `GET /api/logs?since=0` returns at most a single entry (the clear acknowledgement)

#### Scenario: Non-loopback client cannot clear logs

- **WHEN** a request arrives at `DELETE /api/logs` from a non-loopback source IP
- **THEN** the server responds with HTTP 403 Forbidden and the buffer is unchanged
