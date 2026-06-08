## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-hand-scroll-hint`.

## 2. HTML

- [ ] 2.1 In `static/mobile.html`, append a sibling element near the end of `#m-game` (just before the closing `</section>` of `#m-game`):

  ```html
  <button type="button" id="m-hand-scroll-hint" class="m-hand-scroll-hint" hidden aria-label="Scroll to bottom of hand">↓ more</button>
  ```

## 3. CSS

- [ ] 3.1 In `static/mobile.css`, locate the `#m-game` rule (or add one if absent under the `.m-screen` block). Add:
  ```css
  #m-game {
    padding-bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 12px);
  }
  ```

- [ ] 3.2 Add the chip style block (near the other floating elements):
  ```css
  .m-hand-scroll-hint {
    position: fixed;
    left: 50%;
    transform: translateX(-50%);
    bottom: calc(var(--m-action-h) + env(safe-area-inset-bottom) + 8px);
    background: var(--accent);
    color: var(--bg);
    border: none;
    border-radius: 999px;
    padding: 0.4rem 0.9rem;
    font-size: 0.85rem;
    font-weight: 700;
    min-height: 44px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    z-index: 5;
    cursor: pointer;
  }
  ```

- [ ] 3.3 Add `#m-hand-scroll-hint[hidden]` to the existing `[hidden]` override block (around line 528):
  ```css
  ...,
  #m-hand-scroll-hint[hidden] {
    display: none !important;
  }
  ```

## 4. JS

- [ ] 4.1 In `static/mobile.js`, add a module-level `handEndObserver` variable (initialized to `null`).

- [ ] 4.2 In the `DOMContentLoaded` listener, after the existing listeners, initialize the observer:

  ```js
  // Build the rootMargin once. The bottom margin equals the action bar's
  // measured height + 12 px buffer; we negate it so the observer fires
  // when the sentinel crosses ABOVE the action bar's top edge.
  const actionBar = document.querySelector("#m-game .m-action-bar");
  const initObserver = () => {
    if (!actionBar) return;
    const barHeight = actionBar.getBoundingClientRect().height || 80;
    handEndObserver = new IntersectionObserver(
      (entries) => {
        const sentinelEntry = entries[0];
        const chip = $("m-hand-scroll-hint");
        if (!sentinelEntry) return;
        if (sentinelEntry.isIntersecting) {
          chip.hidden = true;
        } else {
          // Count cards hidden under the action bar's top edge.
          const cards = document.querySelectorAll("#m-hand-row .m-hand-card");
          const threshold = window.innerHeight - barHeight;
          let hiddenCount = 0;
          cards.forEach((c) => {
            if (c.getBoundingClientRect().top >= threshold) hiddenCount++;
          });
          chip.hidden = hiddenCount === 0;
          chip.textContent = `↓ ${hiddenCount} more`;
        }
      },
      { rootMargin: `0px 0px -${barHeight + 12}px 0px` }
    );
  };
  initObserver();

  $("m-hand-scroll-hint").addEventListener("click", () => {
    const sentinel = $("m-hand-end-sentinel");
    if (sentinel) sentinel.scrollIntoView({ block: "end", behavior: "smooth" });
  });
  ```

- [ ] 4.3 In `renderHand(view)`, after appending all the card buttons to `#m-hand-row`, append a sentinel `<span>` and re-observe it:

  ```js
  const sentinel = document.createElement("span");
  sentinel.id = "m-hand-end-sentinel";
  sentinel.setAttribute("aria-hidden", "true");
  row.appendChild(sentinel);
  if (handEndObserver) {
    handEndObserver.disconnect();
    handEndObserver.observe(sentinel);
  }
  ```

- [ ] 4.4 Audit: ensure the chip is also hidden when the toolbar/wrap are hidden (empty hand or non-hand active source). In the early-return path of `renderHand`, set `$("m-hand-scroll-hint").hidden = true;` before returning.

## 5. Docs

- [ ] 5.1 In `CHANGELOG.md` `## [Unreleased]`, append under `### Added`:
  - "Mobile hand surfaces a floating **↓ N more** indicator chip when one or more hand cards are hidden beneath the sticky action bar (typically a 16+ card hand after a forced pickup). Tap the chip to smooth-scroll to the end of the hand. `#m-game` reserves bottom padding so the last row clears the action bar at the bottom of the page. [mobile-hand-scroll-hint]"

## 6. Verify

- [ ] 6.1 `black princess tests`.
- [ ] 6.2 `pylint princess tests` → 10.00/10.
- [ ] 6.3 `pytest -q` → green.
- [ ] 6.4 `openspec validate --specs --strict` and `openspec validate mobile-hand-scroll-hint --strict`.
- [ ] 6.5 Manual smoke at DevTools 390 × 844:
  - Start a round, hand ≤ 10 cards. Confirm the chip is hidden.
  - Engineer a scenario where the player picks up a large pile so the hand grows to 18+ cards. Confirm the chip appears with an accurate count.
  - Tap the chip → page scrolls so the last row is visible; chip then hides.
  - Sort toggle → chip count refreshes (chip may or may not be visible depending on hand size).

## 7. Ship

- [ ] 7.1 Commit: `mobile-hand-scroll-hint: Add overflow indicator + bottom padding`.
- [ ] 7.2 Push the branch; open a PR.
- [ ] 7.3 Watch CI; auto-merge once green.

## 8. Wrap up

- [ ] 8.1 `openspec status --change mobile-hand-scroll-hint` → 4/4 done.
- [ ] 8.2 `/opsx:archive mobile-hand-scroll-hint` after merge.
