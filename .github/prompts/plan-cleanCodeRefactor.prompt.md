# Plan: Clean Code Refactor + Value Field

**What:** Extract pipeline logic from `routes.py` into a dedicated service, introduce a `QueryMatch` domain type to replace parallel `(queries, items_list)` lists across all utility functions, add a `value` field to matched candidates end-to-end, and slim `routes.py` down to pure controllers.

**Why:** `routes.py` currently mixes HTTP handling with business logic. The parallel-list pattern used by `reranker.py` and `preprocesssing.py` is fragile and unclear. A single `QueryMatch` type makes every pipeline stage self-documenting.

---

## Steps

### 1. Create `utils/domain.py` — new domain models file
- New `QueryMatch` dataclass with fields: `query: str`, `candidates: list[PesquisaPrompt.Item]`
- Properties: `best_candidate`, `is_high_confidence(threshold)`, `has_candidates`
- Add `value: float = 0.0` field to `PesquisaPrompt.Item` in `utils/ai.py`

### 2. Refactor `utils/reranker.py`
Change all three function signatures to accept/return `list[QueryMatch]`:
- `rerank_items(matches, progress_callback?)` → `list[QueryMatch]`
- `filter_items_by_score(matches, threshold)` → `list[QueryMatch]`
- `filter_items_by_score_gap(matches, gap_threshold)` → `list[QueryMatch]`
- Internal logic adjusts to iterate `match.candidates` instead of bare `items`

### 3. Refactor `utils/preprocesssing.py`
Update `split_queries_by_confidence`:
- New signature: `split_by_confidence(matches: list[QueryMatch], threshold) → tuple[list[QueryMatch], list[QueryMatch]]`
- Returns `(low_confidence_matches, high_confidence_matches)` instead of nested tuples of parallel lists
- Old name kept as deprecated alias if needed

### 4. Create `services/matching.py`
Extract all pipeline logic from `_process_matching_task` and `_insert_documents_in_batches`:
- `insert_documents_in_batches(db, processed_documents, values, message_callback)` — accepts a parallel `values` list for value lookup
- `run_matching_pipeline(task_id, queries, documents, values, context, task_updater)` — full pipeline operating on `list[QueryMatch]`:
  1. LLM replacements → build `processed_docs` and `doc_value_map: dict[str, float]`
  2. ChromaDB setup + batch insert
  3. Query → build `list[QueryMatch]` with `Item.value` populated from `doc_value_map`
  4. Rerank → filter by score → filter by score gap (all using `QueryMatch`)
  5. `split_by_confidence` → return only high-confidence matches
  6. Report `completed` with serialised results

### 5. Update `web/schemas.py`
- Add `value: float` to `MatchedItem`

### 6. Slim down `web/routes.py` — controllers only
- Remove `_process_matching_task` and `_insert_documents_in_batches` entirely
- `GET /results` extracts `queries`, `documents`, `values` from globals and calls `services.matching.run_matching_pipeline` in a background thread
- Global state (`_pasted_df`, `_excel_df`, etc.) stays as module-level — it's lightweight app state, not business logic

### 7. Update `static/js/results.js`
- Add a "Value" column to the results table, reading `item.value` from each `matched_items` entry when rendering completed results
- Include `value` in the CSV export

---

## Verification
- Run `uvicorn app:app --reload` and go through the full upload → process → results flow
- Confirm the results table shows a value column for each matched candidate
- Confirm CSV export includes value
- Check that `low_confidence` queries are silently excluded (existing behavior preserved)

---

## Design Decisions
- **Service location:** `services/matching.py` (top-level) over `web/services/` to keep domain logic decoupled from the web layer
- **Domain model location:** `utils/domain.py` — clear separation from the prompt-building concerns in `utils/ai.py`
- **Value lookup:** In-memory `dict[str, float]` (processed_description → value) rather than storing metadata in ChromaDB — avoids schema changes and works well with the existing batch-insert pattern
- **Renamed split function:** `split_queries_by_confidence` → `split_by_confidence` for conciseness with updated signature accepting `list[QueryMatch]`
