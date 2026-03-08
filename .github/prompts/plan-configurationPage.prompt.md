# Plan: Configuration Page & LLM Toggle System

**Summary:** Add a persistent JSON config file (`config.json`) at the project root, a `utils/config.py` module to load/save it, two new API routes and one new page route in FastAPI, a new `config.html`+`config.js` frontend page, and light integration into the matching pipeline so that LLM features are gated by the saved settings. All settings default to LLM-off, matching the requirement.

---

## Steps

1. **Create `config.json`** at the project root with the default values:
   - `use_llm: false`
   - `gemini_api_key: ""`
   - `use_llm_abbreviation_expansion: false`
   - `use_llm_judge: false`
   - `high_confidence_threshold: 0.9`

2. **Create `utils/config.py`**
   - Define an `AppConfig` dataclass (or TypedDict) with the five fields above.
   - `load_config() → AppConfig` — reads `config.json`; creates it with defaults if absent.
   - `save_config(config: AppConfig)` — writes atomically to `config.json`.
   - Default values live here, so `config.json` never needs to be shipped in VCS.

3. **Add Pydantic schema `ConfigSchema`** to `web/schemas.py` matching the five fields (all optional for PATCH-style updates).

4. **Add routes to `web/routes.py`**
   - `GET /config` → serve `config.html` (mirrors the `read_upload` / `read_results` pattern).
   - `GET /api/config` → return `load_config()` as JSON; mask `gemini_api_key` to `"***"` if non-empty so the key is never sent back to the browser in plaintext.
   - `POST /api/config` → accept `ConfigSchema`, call `save_config()`, return `{"ok": true}`. If the submitted `gemini_api_key` equals `"***"` (masked placeholder), keep the stored key unchanged.

5. **Create `static/html/config.html`**
   - Same Tailwind card layout as the other pages (`bg-gray-100 p-5` body, `bg-white p-5 rounded-lg shadow-md` card).
   - Fields (all inside a single `<form id="config-form">`):
     - **Use LLM** — toggle/checkbox; when off, the three LLM-specific fields below are visually disabled/greyed.
     - **Gemini API Key** — `<input type="password">`, hidden/disabled when Use LLM is off.
     - **Abbreviation expansion via LLM** — checkbox, disabled when Use LLM is off.
     - **LLM judge for low-confidence candidates** — checkbox, disabled when Use LLM is off.
     - **High-confidence threshold** — `<input type="number" min="0" max="1" step="0.01">`.
   - A **Save** button that POSTs to `/api/config`.
   - A success/error toast (same vanilla-JS `fetch` + `async/await` pattern used in other pages).
   - Add a simple text nav bar (consistent across all pages) linking to Home, Upload, Results, Config.

6. **Create `static/js/config.js`**
   - On `DOMContentLoaded`: fetch `GET /api/config`, populate form fields, run toggle-visibility logic.
   - On `use_llm` change: show/hide the dependent fields live.
   - On form submit: `POST /api/config` with current field values; show success/error message.

7. **Add nav links to existing pages** (`static/html/home.html`, `static/html/upload.html`, `static/html/results.html`) — a minimal `<nav>` bar with links to `/`, `/upload`, and `/config`.

8. **Integrate config into the pipeline** in `services/matching.py` — inside `run_matching_pipeline`:
   - Call `load_config()` at the start of the pipeline.
   - Gate the `get_replacements_from_llm` call (abbreviation expansion, currently in `utils/preprocesssing.py`) behind `config.use_llm and config.use_llm_abbreviation_expansion`.
   - Pass `config.high_confidence_threshold` to `split_by_confidence()` and to `QueryMatch.is_high_confidence()` in `utils/domain.py` (replacing the hardcoded `0.9`).
   - Note: The LLM-judge branch (`get_candidates` in `utils/ai.py`) is already dead code — add a guarded call stub gated on `config.use_llm and config.use_llm_judge` with a `TODO: implement execution logic` comment, satisfying the "configuration only" requirement.

9. **Propagate API key to Gemini clients** — in `utils/models/gemini.py` and `utils/embeddings.py`, replace bare `genai.Client()` with `genai.Client(api_key=load_config().gemini_api_key or None)` so the stored key is used when set; falls back to `GOOGLE_API_KEY` env var when empty (no regression for existing setups).

---

## Verification

- Start the server and navigate to `/config` — page loads, form pre-populates with defaults, save returns 200.
- Toggle "Use LLM" off → Gemini key + LLM-specific checkboxes become disabled.
- Save with a fake API key → `config.json` is written; refreshing the page shows `***` in the key field.
- Run the matching pipeline with `use_llm_abbreviation_expansion: false` → preprocessing skips the LLM call.
- Edit `config.json` by hand to `use_llm: true` + valid key → pipeline uses LLM as before.

---

## Decisions

- Config format: flat JSON file (matches existing `cache/llm_replacements/*.json` pattern, no extra dependencies).
- API key security: stored in plaintext in `config.json` (local app); masked to `"***"` in GET response to avoid leaking it to the browser.
- No template engine: nav bar is duplicated across the three existing HTML files (no Jinja2 in use).
- `use_llm` master toggle controls visibility and pipeline execution; `use_llm_abbreviation_expansion` and `use_llm_judge` are sub-options that only matter when `use_llm` is true.
