## 1. Pre-conditions

- [x] 1.1 Branch from main: `git switch -c change/inline-rename-error-recovery`.
- [x] 1.2 Confirm the `unique-room-names` change is on main (server returns 409 on rename collisions). `grep -n "is already taken" princess/server.py` SHALL match.

## 2. Desktop: `renameSelf` returns a boolean

- [x] 2.1 In `static/app.js`, change `renameSelf(newName)` so the success path returns `true`, the validation early-return (`!trimmed` or overlength) returns `false`, and the catch block returns `false`. The signature stays `async`.
- [x] 2.2 Keep the existing `showError("lobby-error", e.message)` in the catch — the boolean is purely a control-flow signal for `beginRenameInline`.

## 3. Desktop: rewrite `beginRenameInline.submit`

- [x] 3.1 Make `submit` an async arrow / function.
- [x] 3.2 Before awaiting `renameSelf`: capture `value = input.value.trim()`. If `!value || value === currentName`, take the cancel path (replace with `nameCell`, no POST) — same as today's blur no-op.
- [x] 3.3 Set `input.disabled = true` before `await renameSelf(value)`.
- [x] 3.4 On `true`: call `clearError("lobby-error")` (or set its text to empty if no `clearError` helper exists), then `input.replaceWith(nameCell)`, set `settled = true`.
- [x] 3.5 On `false`: set `input.disabled = false`, call `input.focus()`, then `input.select()`. Leave `settled = false` so a fresh Enter / blur / Escape can fire again. The error is already in `#lobby-error` from `renameSelf`'s catch.

## 4. Desktop: keep Escape and unchanged-blur paths working

- [x] 4.1 Verify the Escape handler still calls `cancel()` which tears down the input via `input.replaceWith(nameCell)`. No code change expected.
- [x] 4.2 Verify a blur with `value === currentName` still no-ops back to `nameCell` (no POST, no error).
- [x] 4.3 Add a guard in the keydown handler so that while `input.disabled === true`, Enter is ignored (the disable attribute already blocks the event in most browsers, but a `if (input.disabled) return;` line is belt-and-braces).

## 5. Mobile: refocus + select on rename sheet error

- [x] 5.1 In `static/mobile.js`, locate `submitRename`. In the catch block, after `showError(e.message)`, add:

  ```js
  const inp = $("m-rename-input");
  inp.focus();
  inp.select();
  ```

- [x] 5.2 Verify the `try` block still only calls `$("m-rename-sheet").close()` on success — i.e., the catch does NOT close the sheet.

## 6. Manual smoke (two browsers / tabs)

- [x] 6.1 Desktop dupe: Tab A creates a room as "Mike". Tab B joins as "Pat". In Tab B, click **Rename**, type `Mike`, press Enter. Expect: `#lobby-error` shows the 409 detail, the inline `<input>` stays in place, its value `Mike` is selected. Type `Pat2`, press Enter — expect the rename succeeds and the row updates.
- [x] 6.2 Desktop overlength: in Tab B, click Rename, paste a 25-character string, press Enter (the `maxlength="20"` may clip; if it does, try `é` etc. or bypass via DevTools `input.value = "x".repeat(25)`). Expect 422, input stays open, error visible.
- [x] 6.3 Desktop success after error: from the 409 state in 6.1, type `Pat2`, Enter. Expect the input collapses and `#lobby-error` clears.
- [x] 6.4 Desktop Escape: open Rename, type something, press Escape. Expect the input collapses, no POST, no error.
- [x] 6.5 Mobile dupe: open `/m` in two windows, repeat the duplicate-name flow via the bottom sheet. Expect the sheet stays open, the global mobile error helper shows the 409 message, the input value is focused + selected.
- [x] 6.6 Mobile success: from the 409 state, edit to a non-conflicting name, tap Submit. Expect the sheet closes.
- [x] 6.7 Mobile cancel: open the sheet, tap Cancel. Expect the sheet closes silently, no POST.

## 7. Tests

- [x] 7.1 No new server tests required (server contract unchanged).
- [x] 7.2 If a JS unit-test harness exists in this project, add a regression test that simulates `postJSON` returning a rejected promise and asserts `beginRenameInline`'s input is NOT replaced. **If no such harness exists today, skip this task — manual smoke in §6 is the safety net.** (Search: `ls tests/ 2>/dev/null && grep -l "app.js\\|beginRenameInline" tests/`.)

## 8. Docs

- [x] 8.1 In `CHANGELOG.md` `## [Unreleased]` `### Changed`:

  > Inline rename in the desktop lobby now keeps the input open on a server error (e.g., 409 duplicate name). The input is re-focused with its text selected so you can fix the name and resubmit in one keystroke. The mobile rename bottom sheet behaves the same way on error. [inline-rename-error-recovery]

## 9. Verify

- [x] 9.1 `black princess tests` (no-op expected — only JS changes).
- [x] 9.2 `pylint princess tests` → 10.00/10 (no Python changes — should be untouched).
- [x] 9.3 `pytest -q` — should be green; no test additions.
- [x] 9.4 `openspec validate --specs --strict` and `openspec validate inline-rename-error-recovery --strict`.
- [x] 9.5 Hard-reload `/` and `/m` to ensure the new JS is loaded (cache-bust if needed via DevTools).

## 10. Ship

- [x] 10.1 Commit: `inline-rename-error-recovery: keep rename input open on 4xx`.
- [x] 10.2 Push, open PR.
- [x] 10.3 Watch CI; merge once green.

## 11. Wrap up

- [x] 11.1 `openspec status --change inline-rename-error-recovery` → all tasks done.
- [x] 11.2 `/opsx:archive inline-rename-error-recovery` after merge.
