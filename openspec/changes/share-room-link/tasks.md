## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/share-room-link`.

## 2. Desktop

- [ ] 2.1 In `static/index.html`, locate the room-code display near the top of the lobby's `#room-view` section. Add a sibling button:

  ```html
  <button type="button" id="share-link-btn">Share link</button>
  ```

  (Place it in the same row/section as the existing room-code display element.)

- [ ] 2.2 In `static/app.js`, add `shareRoomLink()`:

  ```js
  async function shareRoomLink() {
    if (!state.code) return;
    const url = `${location.origin}/room/${state.code}`;
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
      const btn = $("share-link-btn");
      const original = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = original; }, 1500);
    } catch { /* silent */ }
  }
  ```

- [ ] 2.3 Wire the click handler in the DOM-ready block: `$("share-link-btn").addEventListener("click", shareRoomLink);`.

## 3. Mobile

- [ ] 3.1 In `static/mobile.html`, in `#m-room` (the in-room lobby section), add a Share button next to the `<p class="m-room-line">Room <strong id="m-room-code">…</strong></p>` line:

  ```html
  <button type="button" id="m-share-btn-lobby" class="m-icon" aria-label="Share room link">↗</button>
  ```

  (You may inline-flex it next to the room-line via a small wrapper if needed.)

- [ ] 3.2 In `static/mobile.html`, in the `#m-game` top bar, add a Share button before (or after) the existing `#m-rename-btn`:

  ```html
  <button type="button" id="m-share-btn-game" class="m-icon" aria-label="Share room link">↗</button>
  ```

- [ ] 3.3 In `static/mobile.css`, no new rules needed — `.m-icon` already styles the buttons (44 × 44 px round, `var(--surface-2)` background). Add a small style for the lobby-line wrapper if you needed one in 3.1:

  ```css
  .m-room-line { display: flex; align-items: center; gap: 0.5rem; }
  ```

- [ ] 3.4 In `static/mobile.js`, add `shareRoomLink()`:

  ```js
  async function shareRoomLink() {
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
      flashShared();
    } catch { /* silent */ }
  }

  function flashShared() {
    // Brief inline confirmation. Reuse the lobby error slot's "shown then hidden"
    // mechanic, but with a positive label.
    const el = $("m-lobby-error");
    if (el) {
      const prev = el.textContent;
      el.textContent = "Link copied!";
      el.hidden = false;
      setTimeout(() => { el.hidden = true; el.textContent = prev; }, 1500);
    }
  }
  ```

- [ ] 3.5 Wire both buttons in the DOMContentLoaded block:

  ```js
  $("m-share-btn-lobby").addEventListener("click", shareRoomLink);
  $("m-share-btn-game").addEventListener("click", shareRoomLink);
  ```

- [ ] 3.6 Audit: the existing `m-game-room-code` tap-to-copy of the bare code remains unchanged.

## 4. Docs

- [ ] 4.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Added`:
  - "Every lobby and the mobile game-view top bar gain a **Share** affordance. Tapping it opens the OS share sheet (`navigator.share`) on capable mobile browsers, or copies the room URL (`/room/<code>` on desktop, `/m/<code>` on mobile) to the clipboard with a transient **Copied!** confirmation. The code-only tap-to-copy on the mobile game-view room chip stays unchanged for voice-dictation flows. [share-room-link]"

## 5. Verify

- [ ] 5.1 `black princess tests`.
- [ ] 5.2 `pylint princess tests` → 10.00/10.
- [ ] 5.3 `pytest -q` → green.
- [ ] 5.4 `openspec validate --specs --strict` and `openspec validate share-room-link --strict`.
- [ ] 5.5 Manual smoke:
  - **Desktop:** create a room. Click **Share link** in Chrome on a Mac. Confirm clipboard has `http://127.0.0.1:8000/room/<code>` and the button flashes **Copied!**.
  - **Mobile (DevTools 390×844 emulation):** create a room. Tap the lobby `↗`. In an emulation, `navigator.share` may not be defined → fallback should copy `http://127.0.0.1:8000/m/<code>` and flash `Link copied!`.
  - **Real phone (if available):** browse to `http://<lan-ip>:8000/m`, create a room, tap `↗`. The OS share sheet should appear.

## 6. Ship

- [ ] 6.1 Commit: `share-room-link: Add Share button to lobbies + mobile game header`.
- [ ] 6.2 Push the branch; open a PR.
- [ ] 6.3 Watch CI; auto-merge once green.

## 7. Wrap up

- [ ] 7.1 `openspec status --change share-room-link` → 4/4 done.
- [ ] 7.2 `/opsx:archive share-room-link` after merge.
