## ADDED Requirements

### Requirement: WebSocket close code for permanent rejection

The WebSocket handler `WS /ws/{code}/{pid}` SHALL close the socket with **application-specific close code 4001** when the rejection is **permanent** — i.e., the URL's `code` or `pid` does not match a seated human in the current registry. The close SHALL be paired with a machine-readable `reason` string so the client can distinguish the two permanent-rejection paths:

- When the room `code` is unknown (`REGISTRY.get(code) is None`), the server SHALL close with `code=4001, reason="unknown_room"`.
- When the room is found but `pid` does not match any seat in that room (`room.seat_by_pid(pid) is None`), or the matching seat is a bot (`seat.is_bot is True`), the server SHALL close with `code=4001, reason="unknown_pid"`.

In both cases the server SHALL first send the existing JSON error message (`{"type": "error", "message": "room not found"}` or `{"type": "error", "message": "seat not found"}`) for log and human-eyeball debugging, THEN call `close(code=4001, reason=...)`.

Close codes for **transient** disconnects (network drop, normal disconnect, server crash) SHALL NOT use 4001. They continue to use the default codes (1000 for clean close, 1006 for abnormal closure) so the client can distinguish "this sentinel is dead — clear it" from "the connection blipped — retry."

#### Scenario: Unknown room code closes with 4001 unknown_room

- **WHEN** a client opens `WS /ws/ZZZZ/<any pid>` and no room with code `ZZZZ` exists
- **THEN** the server sends `{"type": "error", "message": "room not found"}` and then closes the socket with `code=4001` and `reason="unknown_room"`

#### Scenario: Unknown pid in an existing room closes with 4001 unknown_pid

- **WHEN** a client opens `WS /ws/AB12/<bogus_pid>` where `AB12` exists but no seat has that pid
- **THEN** the server sends `{"type": "error", "message": "seat not found"}` and then closes the socket with `code=4001` and `reason="unknown_pid"`

#### Scenario: Bot pid is treated as unknown_pid

- **WHEN** a client opens `WS /ws/AB12/<bot_pid>` where `AB12` exists and the matching seat is a bot
- **THEN** the server closes the socket with `code=4001` and `reason="unknown_pid"`

#### Scenario: Normal disconnect does NOT use 4001

- **WHEN** a successfully-seated client cleanly closes their socket
- **THEN** the server's close frame uses a default WebSocket close code (1000-range), NOT 4001
