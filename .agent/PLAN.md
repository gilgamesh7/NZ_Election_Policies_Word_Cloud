# Development Plan & Tracking

**Project:** NZ Political Party Policies Word Cloud  
**Specification:** `.agent/REQUIREMENTS.md`  
**Sequence:** `.agent/IMPLEMENTATION.md`  
**Rules:** `AGENTS.md`  

---

## Phases Overview

| Phase | Description | Status | Acceptance Criteria / Key Deliverable |
|---|---|---|---|
| **Phase 0** | Review and agree the specification | **Completed** | Clarify scope, hostnames, multiple URLs, exclusions, exit criteria met |
| **Phase 1** | Project skeleton and environment | **Completed** | pyproject.toml, uv venv, package structure, minimal test passing |
| **Phase 2** | Configuration and URL rules | **Completed** | Pydantic config, offline URL normaliser/filter, unit tests |
| **Phase 3** | First-level HTML crawler | **Completed** | Polite httpx fetching, 1-level links only, robots.txt, mock tests |
| **Phase 4** | HTML text extraction and source records | **Completed** | Trafilatura + fallback, source URL preservation, inspectable text |
| **Phase 5** | Text cleaning and frequency analysis | **Completed** | Stop words, tokenisation, deterministic tie-breaking, top-20 CSV |
| **Phase 6** | TF-IDF analysis | **Completed** | Multi-party TF-IDF scoring, deterministic ranking, top-20 CSV |
| **Phase 7** | Word clouds and output management | **Completed** | PNG word clouds (freq + tfidf), run directory management |
| **Phase 8** | Notebook integration | **Completed** | End-to-end Jupyter notebook calling package functions |
| **Phase 9** | User acceptance and hardening | **Completed** | Live party website testing, gap documentation, acceptance signoff |

---

## Detailed Task Breakdown

### Phase 0: Review and Agree Specification (Current)
- [x] Review `AGENTS.md`, `.agent/REQUIREMENTS.md`, and `.agent/IMPLEMENTATION.md`.
- [x] Inspect current workspace and git status.
- [x] Research tech stack and verify Python 3.14 compatibility via `uv` dry-run.
- [x] Record technical decisions in `.agent/RESEARCH.md`.
- [ ] Confirm representation of party allowed hostnames with user.
- [ ] Confirm multiple starting URLs and corpus aggregation policy.
- [ ] Confirm default non-policy page URL exclusions.
- [ ] Confirm dual word cloud generation (Frequency + TF-IDF) by default.
- [ ] Obtain user approval before writing application code for Phase 1.

### Phase 1: Project Skeleton and Environment (Completed)
- [x] Create `pyproject.toml` with dependencies (`httpx`, `beautifulsoup4`, `trafilatura`, `wordcloud`, `scikit-learn`, `result`, `pydantic`, `pytest`, `jupyter`, `pyyaml`).
- [x] Set up virtual environment via `uv venv` and install dependencies.
- [x] Create package directory `src/nz_policy_wordcloud/` with modular layout (`__init__.py`, `py.typed`).
- [x] Create `tests/` directory with `conftest.py` and smoke tests in `test_smoke.py`.
- [x] Create sample configuration file `config.example.yaml` with dummy URLs.
- [x] Verify test runner `.venv/bin/pytest` passes.
- [x] Update README setup instructions.

### Phase 2: Configuration and URL Rules (Completed)
- [x] Define Pydantic schema for `PartyConfig`, `CrawlerConfig`, `ExclusionConfig`, and `AppConfig`.
- [x] Implement URL normalisation (scheme check, fragment stripping, default port removal, query param preservation).
- [x] Implement same-host and allowed-subdomain checking.
- [x] Implement rejection rules (non-HTML extensions, mailto/tel/js, excluded URL path patterns).
- [x] Implement `Result[str, UrlRejectReason]` error handling.
- [x] Unit tests for all URL rules and config validation with 100% offline fixtures.
- [x] Add default `config.yaml` with the 8 specified New Zealand political parties.

### Phase 3: First-Level HTML Crawler (Completed)
- [x] Implement crawler client using `httpx` with timeouts, size limits, headers, and rate limiting.
- [x] Implement `robots.txt` checker with `RobotsCache`.
- [x] Implement first-level link discovery on starting pages only (depth = 1 strictly).
- [x] Enforce deduplication and error handling without crashing on failed pages.
- [x] Track crawl manifest (`PageRecord` and `CrawlManifest`).
- [x] Unit tests with mocked HTTP responses and local HTML fixtures.

### Phase 4: HTML Text Extraction and Source Records (Completed)
- [x] Implement `trafilatura` extraction pipeline.
- [x] Implement fallback to BeautifulSoup article/main content parser.
- [x] Save raw extracted text with YAML metadata header linking to source URL.
- [x] Record extraction status (`ExtractionStatus` enum) in metadata.
- [x] Unit tests for boilerplate removal, empty content, malformed HTML.

### Phase 5: Text Cleaning and Frequency Analysis (Completed)
- [x] Normalisation (NFKC, lowercase, punctuation removal, Te Reo Māori macron support).
- [x] Stop-word removal (standard English + configurable domain-specific exclusions).
- [x] Frequency counting with deterministic sorting (count DESC, term ASC).
- [x] Export frequency tables (all terms + top-20).
- [x] Unit tests for deterministic ranking, tie-breaking, and stop words.

### Phase 6: TF-IDF Analysis (Completed)
- [x] Party-level document aggregation.
- [x] TF-IDF vectorisation across all configured parties.
- [x] Deterministic sorting (score DESC, term ASC).
- [x] Export TF-IDF tables (all terms + top-20).
- [x] Unit tests for TF-IDF ranking, edge cases (empty text, single party).

### Phase 7: Word Clouds and Output Management (Completed)
- [x] Implement WordCloud generator for frequency and TF-IDF terms.
- [x] Implement run directory manager (`outputs/run_YYYYMMDD_HHMMSS/`).
- [x] Save PNG images (1200x800) with accessible filenames.
- [x] Generate comprehensive run summary manifest.
- [x] Unit tests for file generation and overwrite safety.

### Phase 8: Notebook Integration (Completed)
- [x] Create structured Jupyter Notebook `notebooks/nz_policy_wordcloud.ipynb`.
- [x] Short, purpose-labelled cells calling package functions.
- [x] Create run script `run_notebook.sh` in project root.
- [x] End-to-end local fixture test for notebook execution.

### Phase 9: User Acceptance and Hardening (Completed)
- [x] Run with user-configured political party URLs.
- [x] Review discovered links and extraction quality.
- [x] Document known limitations (JavaScript-only content, PDF links).
- [x] Final acceptance sign-off ready.
