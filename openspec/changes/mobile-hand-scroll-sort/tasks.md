## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-hand-scroll-sort`.

## 2. HTML

- [ ] 2.1 In `static/mobile.html`, replace the `<div id="m-hand-fan" class="m-hand-fan" role="list">` element with the new hand block:

  ```html
  <div id="m-hand-toolbar" class="m-hand-toolbar">
    <button type="button" id="m-sort-btn" aria-pressed="true">Sort: rank</button>
    <span id="m-hand-count" class="m-muted">0 cards</span>
  </div>
  <div id="m-hand-wrap" class="m-hand-wrap">
    <button type="button" id="m-hand-prev" class="m-hand-edge prev" aria-label="Previous cards">‹</button>
    <div id="m-hand-row" class="m-hand-row" role="list" aria-label="Your hand"></div>
    <button type="button" id="m-hand-next" class="m-hand-edge next" aria-label="More cards">›</button>
  </div>
  ```

## 3. CSS

- [ ] 3.1 In `static/mobile.css`, remove the fan-out rules:
  - `.m-hand-fan { position: relative; height: 140px; ... }`
  - `.m-hand-card { position: absolute; transform-origin: 50% 130%; transition: transform 0.15s ease, ...; ... }`
  - `.m-hand-card.red { color: ... }` keep (still used).
  - The `:before/::after` pseudo-elements for `.m-hand-card.selected` / `.m-hand-card.special` are still used — keep them, just adjust positioning if needed for the new layout.

- [ ] 3.2 Add the scrolling-row rules:

  ```css
  .m-hand-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0.5rem 0 0.25rem;
    gap: 0.5rem;
  }

  #m-sort-btn {
    min-height: 36px;
    padding: 0.3rem 0.7rem;
    font-size: 0.85rem;
    background: var(--surface-2);
    color: var(--ink);
    border: 1px solid var(--ink-dim);
    border-radius: 8px;
  }
  #m-sort-btn[aria-pressed="true"] {
    background: var(--accent);
    color: var(--bg);
    border-color: var(--accent);
  }

  .m-hand-wrap {
    position: relative;
  }

  .m-hand-row {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-x;
    padding: 8px 0 12px;
    scrollbar-width: none;
  }
  .m-hand-row::-webkit-scrollbar { display: none; }

  .m-hand-card {
    position: relative;
    flex: 0 0 calc((100% - 16px) / 3);  /* 3 visible, two 8px gaps */
    height: 130px;
    scroll-snap-align: start;
    background: var(--ink);
    color: #11111b;
    border: 3px solid transparent;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1.4rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    line-height: 1.1;
    transition: transform 0.15s ease, border-color 0.15s ease;
    padding: 0;
  }
  .m-hand-card.selected {
    border-color: var(--accent);
    transform: translateY(-6px);
  }

  /* Gradient fade overlay — only visible when scrollable that side. */
  .m-hand-wrap::before,
  .m-hand-wrap::after {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    width: 28px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s ease;
    z-index: 1;
  }
  .m-hand-wrap::before {
    left: 0;
    background: linear-gradient(to right, var(--bg), transparent);
  }
  .m-hand-wrap::after {
    right: 0;
    background: linear-gradient(to left, var(--bg), transparent);
  }
  .m-hand-wrap.has-prev::before { opacity: 1; }
  .m-hand-wrap.has-next::after { opacity: 1; }

  .m-hand-edge {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 36px;
    height: 44px;
    padding: 0;
    border-radius: 18px;
    background: var(--surface-2);
    color: var(--accent);
    font-size: 1.4rem;
    line-height: 1;
    z-index: 2;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
  }
  .m-hand-edge.prev { left: -6px; }
  .m-hand-edge.next { right: -6px; }
  .m-hand-wrap.has-prev .m-hand-edge.prev,
  .m-hand-wrap.has-next .m-hand-edge.next {
    opacity: 0.95;
    pointer-events: auto;
  }

  /* Wider viewport — show 4 cards. */
  @media (min-width: 480px) {
    .m-hand-card { flex: 0 0 calc((100% - 24px) / 4); }
  }
  @media (max-width: 359px) {
    .m-hand-card { flex: 0 0 calc((100% - 8px) / 2); }
  }
  ```

- [ ] 3.3 Update the `[hidden]` overrides block: add `#m-hand-toolbar[hidden]`, `#m-hand-wrap[hidden]` to the rule.

## 4. JS

- [ ] 4.1 In `static/mobile.js`, add `sortHand: true` to the `state` object.

- [ ] 4.2 Replace the body of `renderHand(view)` with the new logic. Pseudo-shape:

  ```js
  function renderHand(view) {
    const wrap = $("m-hand-wrap");
    const row = $("m-hand-row");
    const toolbar = $("m-hand-toolbar");
    row.innerHTML = "";
    const me = view.you;
    const rawCards = me.hand || [];
    if (!rawCards.length || me.active_source !== "hand") {
      toolbar.hidden = true;
      wrap.hidden = true;
      return;
    }
    toolbar.hidden = false;
    wrap.hidden = false;
    $("m-hand-count").textContent = `${rawCards.length} card${rawCards.length === 1 ? "" : "s"}`;

    // Build [{card, originalIdx}] then sort if enabled.
    const items = rawCards.map((c, i) => ({c, idx: i}));
    if (state.sortHand) {
      items.sort((a, b) => a.c.rank - b.c.rank || a.idx - b.idx);
    }

    items.forEach(({c, idx}) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "m-hand-card " + (isRedSuit(c.suit) ? "red" : "black");
      btn.setAttribute("role", "listitem");
      btn.dataset.idx = String(idx);
      btn.innerHTML = `<span>${rankLabel(c.rank)}</span><span>${suitGlyph(c.suit)}</span>`;
      if (isSpecialRank(c.rank, view)) btn.classList.add("special");
      if (isLegalRank(c.rank, view) && me.your_turn) btn.classList.add("legal-hint");
      if (state.selectedIndices.has(idx) && me.active_source === "hand") btn.classList.add("selected");
      btn.addEventListener("click", () => toggleSelect(idx, c.rank));
      row.appendChild(btn);
    });

    updateEdgeIndicators();
  }
  ```

- [ ] 4.3 Add `updateEdgeIndicators()`:

  ```js
  function updateEdgeIndicators() {
    const wrap = $("m-hand-wrap");
    const row = $("m-hand-row");
    if (!wrap || !row || wrap.hidden) return;
    const atStart = row.scrollLeft <= 4;
    const atEnd = row.scrollLeft + row.clientWidth >= row.scrollWidth - 4;
    wrap.classList.toggle("has-prev", !atStart);
    wrap.classList.toggle("has-next", !atEnd && row.scrollWidth > row.clientWidth);
  }
  ```

- [ ] 4.4 In the DOM-ready block, add listeners:

  ```js
  $("m-sort-btn").addEventListener("click", toggleSort);
  $("m-hand-row").addEventListener("scroll", updateEdgeIndicators, { passive: true });
  $("m-hand-prev").addEventListener("click", () => scrollHandBy(-1));
  $("m-hand-next").addEventListener("click", () => scrollHandBy(1));
  ```

- [ ] 4.5 Add `toggleSort()`:

  ```js
  function toggleSort() {
    state.sortHand = !state.sortHand;
    const btn = $("m-sort-btn");
    btn.setAttribute("aria-pressed", String(state.sortHand));
    btn.textContent = state.sortHand ? "Sort: rank" : "Sort: off";
    if (state.view) renderHand(state.view);
  }
  ```

- [ ] 4.6 Add `scrollHandBy(direction)`:

  ```js
  function scrollHandBy(direction) {
    const row = $("m-hand-row");
    const card = row.querySelector(".m-hand-card");
    if (!card) return;
    const step = card.offsetWidth + 8; // gap
    row.scrollBy({ left: direction * step, behavior: "smooth" });
  }
  ```

- [ ] 4.7 Audit: the existing `playSelected()` uses `state.selectedIndices` which are server-side indices — verify no code path assumes rendered position. The `toggleSelect(idx, rank)` calls already receive the server index via `data-idx`. No change needed.

## 5. Docs

- [ ] 5.1 In `CHANGELOG.md` `## [Unreleased]`, add a `### Changed` bullet:
  - "Mobile hand is now a horizontally-scrolling row of full-size cards (3 visible at iPhone 14 width) with snap-to-card scrolling, tappable left/right chevron indicators when more cards exist off-screen, and a **Sort: rank / off** toggle plus a hand-count badge. Replaces the fan-out arc from the original mobile UI. [mobile-hand-scroll-sort]"

## 6. Verify

- [ ] 6.1 `black princess tests` (no Python changes; tidy).
- [ ] 6.2 `pylint princess tests` → 10.00/10.
- [ ] 6.3 `pytest -q` → green.
- [ ] 6.4 `openspec validate --specs --strict` and `openspec validate mobile-hand-scroll-sort --strict`.
- [ ] 6.5 Manual smoke at DevTools 390×844:
  - Start a round on `/m`. Hand renders as a row of ~3 cards.
  - Right chevron visible when hand > 3 cards. Tap it → row scrolls one card. Left chevron appears.
  - Swipe the row by a fraction → snaps to next card.
  - Toggle **Sort** → cards reorder. Toggle again → back to deal order.
  - Tap a card → it lifts with the accent border + ✓.
  - Play it → engine receives the correct server index (verify by playing a card you know the value of).

## 7. Ship

- [ ] 7.1 Commit: `mobile-hand-scroll-sort: Replace fan-out with scrolling row + sort toolbar`.
- [ ] 7.2 Push the branch; open a PR.
- [ ] 7.3 Watch CI; auto-merge once green.

## 8. Wrap up

- [ ] 8.1 `openspec status --change mobile-hand-scroll-sort` → 4/4 done.
- [ ] 8.2 `/opsx:archive mobile-hand-scroll-sort` after merge.
