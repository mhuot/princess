## 1. Pre-conditions

- [ ] 1.1 Branch from main: `git switch -c change/mobile-opponent-face-up`.

## 2. JS

- [ ] 2.1 In `static/mobile.js`, locate `renderOpponents(view)`. After appending the `m-opp-meta` element (the `hand N · down N` line), insert a face-up row **before** it so the visual order is name → face-up → counts. Pseudocode:

  ```js
  const faceUpRow = document.createElement("div");
  faceUpRow.className = "m-opp-face-up";
  p.face_up.forEach((c) => {
    const el = document.createElement("span");
    el.className = "m-opp-mini-card " + (isRedSuit(c.suit) ? "red" : "black");
    el.textContent = `${rankLabel(c.rank)}${suitGlyph(c.suit)}`;
    if (isSpecialRank(c.rank, view)) el.classList.add("special");
    faceUpRow.appendChild(el);
  });
  box.appendChild(faceUpRow);
  // ...then the existing m-opp-meta line.
  ```

- [ ] 2.2 Audit: the existing `m-opp-meta` line stays as-is (text content `hand N · down N`). No change to opponent name or turn indicator logic.

## 3. CSS

- [ ] 3.1 In `static/mobile.css`, bump `.m-opponent { min-width: 110px → 170px; }`.

- [ ] 3.2 Add new rules:

  ```css
  .m-opp-face-up {
    display: flex;
    gap: 3px;
    margin: 4px 0 2px;
    min-height: 0;
  }

  .m-opp-mini-card {
    position: relative;
    width: 22px;
    height: 32px;
    background: var(--ink);
    color: #11111b;
    border-radius: 3px;
    font-size: 0.62rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid transparent;
  }
  .m-opp-mini-card.red { color: #a3002b; }
  .m-opp-mini-card.special::after {
    content: "★";
    position: absolute;
    top: 0;
    right: 1px;
    font-size: 0.5rem;
    color: var(--accent-strong);
    line-height: 1;
  }
  ```

- [ ] 3.3 The existing `.m-opponent.finished { opacity: 0.55; }` (or equivalent) already dims the whole chip; verify the face-up row inherits visually. No new rule needed.

## 4. Docs

- [ ] 4.1 In `CHANGELOG.md` `## [Unreleased]`, add a `### Changed` bullet:
  - "Mobile opponent chips now show each opponent's **face-up cards** inline (with the ★ glyph on wild ranks), matching the desktop UI. Public information is now visible without leaving the play screen. [mobile-opponent-face-up]"

## 5. Verify

- [ ] 5.1 `black princess tests` (no Python; tidy).
- [ ] 5.2 `pylint princess tests` → 10.00/10.
- [ ] 5.3 `pytest -q` → green (no test changes).
- [ ] 5.4 `openspec validate --specs --strict` and `openspec validate mobile-opponent-face-up --strict`.
- [ ] 5.5 Manual smoke at DevTools 390×844: open `/m`, start a round, confirm the opponent chip shows their three face-up cards under the name. Trigger a bot to play one of their face-up cards (wait or rig a scenario); confirm the row collapses by one card on next broadcast. Verify the ★ glyph appears on a 2, 10, or the configured reverse rank in their face-up.

## 6. Ship

- [ ] 6.1 Commit: `mobile-opponent-face-up: Show opponent face-up cards inline`.
- [ ] 6.2 Push the branch; open a PR.
- [ ] 6.3 Watch CI; auto-merge once green.

## 7. Wrap up

- [ ] 7.1 `openspec status --change mobile-opponent-face-up` → 4/4 done.
- [ ] 7.2 `/opsx:archive mobile-opponent-face-up` after merge.
