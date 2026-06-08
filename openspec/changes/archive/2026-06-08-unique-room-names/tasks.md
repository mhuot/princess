## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/unique-room-names`.

## 2. Server helper

- [ ] 2.1 In `princess/server.py`, add a helper near the other internal helpers:

  ```python
  def _name_already_taken(room, name: str, *, exclude_pid: str | None = None) -> tuple[bool, str | None]:
      """Case-insensitive, whitespace-trimmed dedupe check.

      Returns (True, existing_name) when a conflict exists, where `existing_name`
      is the casing of the existing seat (for the error message). Returns
      (False, None) otherwise.
      """
      needle = name.strip().casefold()
      for s in room.seats:
          if s.pid == exclude_pid:
              continue
          if s.name.strip().casefold() == needle:
              return True, s.name
      return False, None
  ```

## 3. `/api/rooms` (create)

- [ ] 3.1 Locate the `create_room` handler. Trim the incoming `name` before constructing the host's seat: `name = body.name.strip()` (Pydantic's `min_length=1` already rejects empty strings; trim happens before we persist).

## 4. `/join`

- [ ] 4.1 In `join_room`, trim the incoming name. Call `_name_already_taken(room, name)` and raise `HTTPException(409, f"name '{existing}' is already taken in this room")` on conflict. The check happens before the seat is appended.

## 5. `/rename`

- [ ] 5.1 In `rename_seat`, trim `body.new_name`. If the trimmed value matches the caller's existing seat name (case-folded), return `{"ok": True, "name": seat.name}` immediately without modifying state or broadcasting.
- [ ] 5.2 Otherwise call `_name_already_taken(room, new_name, exclude_pid=body.pid)`. On conflict, raise `HTTPException(409, f"name '{existing}' is already taken in this room")`.
- [ ] 5.3 On success, persist the trimmed form on `seat.name` (and `Player.name` mid-round) as today.

## 6. Tests

- [ ] 6.1 In `tests/test_server.py`, add the following cases (use the existing `_client()` / `_bootstrap_lobby` helpers as appropriate):

  - `test_join_rejects_duplicate_name` — bootstrap a room with host "Ada", second join with "Ada" returns 409 and the detail contains `"'Ada'"`.
  - `test_join_rejects_case_insensitive_duplicate` — host "Mike", second join with "mike" returns 409.
  - `test_join_rejects_whitespace_padded_duplicate` — host "Mike", second join with `"  Mike  "` returns 409.
  - `test_join_rejects_name_matching_a_bot` — host adds a bot (capture its name), human joins with that bot's name → 409.
  - `test_rename_rejects_duplicate_name` — host "Mike", joiner "Pat", joiner posts `/rename` with `"Mike"` → 409.
  - `test_rename_to_own_name_is_noop` — host posts `/rename` with their own name (after trim and case-fold) → 200, no state change, no broadcast (verify by snapshotting `room.seats` before and after).
  - `test_create_room_trims_host_name` — POST `/api/rooms` with `name="  Mike  "`; assert `room.seats[0].name == "Mike"`.
  - `test_bot_name_avoids_human_name` — host "Galaxy Brain"; POST `/bot`; assert the bot's name is NOT "Galaxy Brain". (This already passes today; the test guards against regression.)

## 7. Docs

- [ ] 7.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Changed`:
  - "Per-room names are now unique. `POST /api/rooms/<code>/join` and `POST /api/rooms/<code>/rename` return **409 Conflict** when the chosen name (case-insensitive, whitespace-trimmed) matches an existing seat. Renaming to your own current name is a no-op (200 with no broadcast). [unique-room-names]"

## 8. Verify

- [ ] 8.1 `black princess tests`.
- [ ] 8.2 `pylint princess tests` → 10.00/10.
- [ ] 8.3 `pytest -q` — expect green; the 8 new cases pass.
- [ ] 8.4 `openspec validate --specs --strict` and `openspec validate unique-room-names --strict`.
- [ ] 8.5 Manual smoke: open `/m` in two tabs, create a room in tab 1 as "Mike", join from tab 2 as "Mike" — expect the error visible in the mobile lobby error slot.

## 9. Ship

- [ ] 9.1 Commit: `unique-room-names: 409 on duplicate join/rename`.
- [ ] 9.2 Push the branch; open a PR.
- [ ] 9.3 Watch CI; auto-merge once green.

## 10. Wrap up

- [ ] 10.1 `openspec status --change unique-room-names` → 4/4 done.
- [ ] 10.2 `/opsx:archive unique-room-names` after merge.
