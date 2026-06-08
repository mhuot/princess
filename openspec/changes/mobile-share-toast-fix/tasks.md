## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-share-toast-fix`.

## 2. JS

- [ ] 2.1 In `static/mobile.js`, delete the existing `flashShared()` function.

- [ ] 2.2 Add `flashShareButton(buttonId)`:

  ```js
  function flashShareButton(buttonId) {
    const btn = $(buttonId);
    if (!btn || btn.dataset.flashing === "1") return;
    btn.dataset.flashing = "1";
    const prev = btn.textContent;
    btn.textContent = "✓";
    setTimeout(() => {
      btn.textContent = prev;
      delete btn.dataset.flashing;
    }, 1500);
  }
  ```

- [ ] 2.3 Change `shareRoomLink()` signature to accept the button id:

  ```js
  async function shareRoomLink(buttonId) {
    if (!state.code) return;
    const url = `${location.origin}/m/${state.code}`;
    const payload = {
      title: "Princess Card Game",
      text: `Join my Princess room ${state.code}:`,
      url,
    };
    if (navigator.share) {
      try { await navigator.share(payload); return; }
      catch (e) { if (e.name === "AbortError") return; /* fall through */ }
    }
    try {
      await navigator.clipboard.writeText(url);
      if (buttonId) flashShareButton(buttonId);
    } catch { /* silent */ }
  }
  ```

- [ ] 2.4 Update the two button click listeners in `DOMContentLoaded` to pass the button id:

  ```js
  $("m-share-btn-lobby").addEventListener("click", () => shareRoomLink("m-share-btn-lobby"));
  $("m-share-btn-game").addEventListener("click", () => shareRoomLink("m-share-btn-game"));
  ```

## 3. Docs

- [ ] 3.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Fixed`:
  - "Mobile Share button now visually confirms the clipboard copy by flashing the `↗` glyph to `✓` for 1.5s. The previous `Link copied!` toast was rendered into `#m-lobby-error` — an element inside `#m-landing` that gets hidden the moment a room is created, so it was always invisible from the user's perspective. [mobile-share-toast-fix]"

## 4. Verify

- [ ] 4.1 `black princess tests`.
- [ ] 4.2 `pylint princess tests` → 10.00/10.
- [ ] 4.3 `pytest -q` → green.
- [ ] 4.4 `openspec validate --specs --strict` and `openspec validate mobile-share-toast-fix --strict`.
- [ ] 4.5 Re-run `scripts/smoke_test.py`. Expect 16/16 — the failing **REAL BUG** check should now pass with the new button-flash check.

## 5. Update the smoke test

- [ ] 5.1 Update `scripts/smoke_test.py`'s mobile-share-flash check to verify the **button's textContent flips to `✓` for ~1.5s** rather than asserting a separate toast element appears. Adjust the screenshot capture timing accordingly (take a screenshot mid-flash, ~700ms after tap).

## 6. Ship

- [ ] 6.1 Commit: `mobile-share-toast-fix: Flash share button glyph instead of unreachable toast`.
- [ ] 6.2 Push the branch; open a PR.
- [ ] 6.3 Watch CI; auto-merge once green.

## 7. Wrap up

- [ ] 7.1 `openspec status --change mobile-share-toast-fix` → 4/4 done.
- [ ] 7.2 `/opsx:archive mobile-share-toast-fix` after merge.
