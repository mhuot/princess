## Context

Mobile's pile area uses three columns: a left stat (Deck count), the center pile card, and a right stat (Rule indicator). Each column is a `.m-pile-stat` block — small label on top, large accent value below. The deck count comes from `view.deck_count`; the rule indicator from a small derivation on the rule string.

`view.pile_size` is already in the broadcast (used to gate the Pick up button) but nothing on screen displays it. The simplest fix is to stack a second stat under the deck — same shape, same color treatment.

## Goals / Non-Goals

**Goals:**
- Surface `view.pile_size` to the player without leaving the play screen.
- Stay within the existing pile-area row; no new vertical real estate.
- Match the visual treatment of the existing deck count (small label, accent number).

**Non-Goals:**
- Touching desktop. Desktop already shows pile size below the pile card.
- Adding a history or trend (max, avg pile size). Just the current count.
- Animating the value (count-up) on broadcasts.
- Conditional visibility (e.g., hide when 0). Always show — "0" is informative.

## Decisions

### Stack inside the existing left column
**Choice:** Replace the single `<div class="m-pile-stat">` (Deck) with a wrapper `<div class="m-pile-stat-col">` containing two `<div class="m-pile-stat">` blocks (Deck and Discard).
**Why:** Preserves the existing three-column layout; the leftmost column grows slightly in height which is fine — the center pile card is the tallest element so the row's height stays driven by it.

### Replace `:last-child` selector with an explicit `.m-stat-value` class
**Choice:** Drop `.m-pile-stat span:last-child { ... }` in favor of `.m-stat-value { ... }`. Add the class to both `#m-deck-count` and the new `#m-discard-count`.
**Why:** With two stats stacked in a column wrapper, `:last-child` semantics get awkward. An explicit class is clearer and unambiguous.

### Label text: "Discard"
**Choice:** Use "Discard" — matches the existing "Discard pile" label on the center pile card.
**Why:** Consistent vocabulary. Players already see "Discard pile" once; "Discard" as the count label reinforces it.

### Always render; "0" means empty
**Choice:** Even when the pile is empty (deck depleted, pile burned), render `Discard 0`.
**Why:** Hiding it would be jarring on the next broadcast when it reappears. Constant presence > conditional jumpiness.

### Small vertical gap between the two stats
**Choice:** `.m-pile-stat-col { display: flex; flex-direction: column; gap: 0.4rem; }`.
**Why:** Visual breathing room so Deck and Discard read as two stats, not one cramped block.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Tall left column changes the row's vertical alignment | Center pile card is taller (~116 px) than either stat block; row alignment stays driven by it. The two stats vertically center within the row by default flexbox behavior. |
| Two big numbers compete for attention | Both stats use the same accent color and font-size; visually balanced. The labels disambiguate. |
| "Discard" wording confuses players who think it means "discarded so far" | Pairing with the existing "Discard pile" label on the center card anchors the meaning. |

## Migration Plan

1. **HTML:** wrap the existing `<div class="m-pile-stat">` (Deck) with a column wrapper containing two stats — Deck on top, Discard below.
2. **CSS:** add `.m-pile-stat-col { display: flex; flex-direction: column; gap: 0.4rem; }`. Replace the `:last-child` rule with `.m-stat-value { font-size: 1.2rem; font-weight: 700; color: var(--accent); }`. Add `class="m-stat-value"` to both spans.
3. **JS:** in `renderPile(view)`, add `$("m-discard-count").textContent = String(view.pile_size || 0);`.
4. CHANGELOG.
5. Commit + push + CI + merge.

Rollback: revert the three static files.

## Open Questions

- Use "Pile" as the label instead of "Discard"? Recommendation: stick with "Discard" — matches the "Discard pile" label already shown above the pile card, and "Pile" is overloaded (face-down pile, hand pile, etc).
