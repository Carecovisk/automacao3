# Plan: Interactive Correspondence Selection for CSV Export

Each query displays up to 3 matched items (current behavior preserved). Those 3 visible items become individually toggleable — click to deselect (gray + strikethrough), click again to re-select. The CSV export produces exactly **one row per query**: the highest-scored visible item that is not deselected. If the user deselects the top item, the second-highest becomes the export candidate, and so on. If all visible items are deselected, that query is omitted from the CSV entirely. Hidden items ("+X mais...") remain non-interactive and are never candidates for export.

## Steps

1. **Add selection state tracker** — Add `const deselectedItems = new Set()` at the top of `static/js/results.js` alongside the existing module-level vars.

2. **Make visible items clickable** — In `displayResults()`, change the `.slice(0, 3)` mapped items from plain `<div>` elements to clickable ones. Each gets:
   - `cursor-pointer select-none` styling
   - `data-result-index="${index}"` and `data-item-index="${itemIndex}"` attributes
   - An `onclick` calling `toggleItem(resultIndex, itemIndex)` on the element

3. **Implement `toggleItem()`** — New function that finds the matching DOM element by its data-attributes, toggles CSS classes `line-through text-gray-400 opacity-50` on it, and adds/removes the key `"${resultIndex}-${itemIndex}"` from `deselectedItems`.

4. **Single-best-match CSV export** — In `downloadCSV()`, for each query iterate over `matched_items.slice(0, 3)` in order (they are already sorted by score descending). Pick the **first item** whose composite key `"${resultIndex}-${itemIndex}"` is **not** in `deselectedItems` and write that single row to the CSV. If all visible items for a query are deselected, skip the query entirely (no row emitted).

5. **Add hint text** — Add a small italic note in `static/html/results.html` below the results count: "Clique em uma correspondência para excluí-la da exportação. Apenas a correspondência de maior score não excluída será exportada por consulta".

## Verification

- Results with multiple matches: top item is the default CSV candidate; click it → gray + strikethrough; download CSV → second item is now the candidate instead; click it too → third item becomes candidate; download → third item exported
- Re-click a deselected item → it restores and reclaims its priority position
- If all 3 are deselected: that query produces no row in the CSV
- Results with only 1 match: that single item is toggleable; if deselected, the query is omitted from the CSV
- The "+X mais..." indicator remains non-interactive as before

## Decisions

- Toggle behavior (re-click re-selects), as confirmed
- Top-3 display cap kept, as confirmed — hidden items are never candidates for export
- Exactly one row per query in the CSV: the highest-scored non-deselected visible item
- State tracked in a JS `Set` with `"resultIndex-itemIndex"` composite keys
- Best score/value columns stay static (no reactive update needed)
