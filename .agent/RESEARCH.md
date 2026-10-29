# Research and Technical Decisions

**Project:** New Zealand Political Party Policies Word Cloud  
**Date:** October 2026  
**Status:** Approved for Phase 0  

---

## 1. Technical Stack Evaluation

### 1.1 Python Runtime & Package Management
- **Runtime:** Python 3.14.0 (installed on Apple Silicon macOS).
- **Environment & Dependency Manager:** `uv` (`/opt/homebrew/bin/uv`).
  - Fast, deterministic dependency resolution.
  - Generates standard `pyproject.toml` and virtual environment `.venv`.
- **Package Verification:** Dry-run resolution on Python 3.14 verified all target libraries install without dependency conflicts:
  - `httpx==0.28.1`
  - `beautifulsoup4==4.15.0`
  - `trafilatura==2.3.1`
  - `wordcloud==1.9.6`
  - `scikit-learn==1.9.1`
  - `result==0.17.0`
  - `pydantic==2.14.1`
  - `pytest==9.1.1`
  - `jupyter==1.1.1`
  - `pyyaml==6.0.3`

### 1.2 Error Handling: `result` vs `results`
- `AGENTS.md` requests the "results package for Rust-style error handling".
- PyPI evaluation:
  - `results` is an unrelated database package (`psycopg` wrapper).
  - `result` (`rustedpy/result`) is the standard Python package providing Rust-style `Result[T, E]`, `Ok(value)`, and `Err(error)`.
- **Decision:** Use `result` (v0.17.0+) for explicit, Rust-style error handling across crawler, extractor, and pipeline functions.

### 1.3 Web Collection & Safety
- **HTTP Client:** `httpx` (synchronous client for controlled sequential requests).
  - Configurable custom User-Agent identifying the research tool.
  - Timeouts (default 10s connect/read).
  - Response size limit (e.g. 5MB maximum to prevent memory exhaustion).
  - Polite crawl delay (configurable, default 1.0s per host).
  - Restrained retry behaviour (max 2 retries with backoff on network errors; do not retry 4xx client errors).
- **Robots.txt Compliance:** `urllib.robotparser.RobotFileParser` to respect `robots.txt` disallow directives for the user-agent.
- **Link Normalisation:** `urllib.parse` (`urljoin`, `urlparse`, `urlunsplit`):
  - Strip fragments (`#...`).
  - Strip trailing slashes consistently for deduplication where appropriate, while preserving path structure and query parameters where meaningful.
  - Validate URL schemes: HTTP and HTTPS only.

### 1.4 HTML Text Extraction
- **Primary Extractor:** `trafilatura`.
  - Best-in-class open-source tool for stripping navigation menus, footers, sidebars, cookie banners, and social widgets while extracting core policy text and headings.
- **Fallback Extractor:** `beautifulsoup4` HTML-to-text parser.
  - If `trafilatura` returns empty or `None`, fallback extracts main `<article>` or `<main>` or body text with script/style tags stripped.
  - Fallback status is explicitly recorded in page metadata.

### 1.5 Text Cleaning & Tokenisation
- Unicode normalisation (NFKC), lowercasing, punctuation stripping.
- Custom stop words:
  - Standard English stop words (based on scikit-learn / nltk standard list).
  - Project-specific configurable exclusion list (e.g., "click", "read", "share", "page", party names if requested).
  - All exclusions transparently documented and configurable via YAML/JSON.

### 1.6 Term Frequency & TF-IDF
- **Term Frequency:** Count tokens across all accepted pages for each party.
  - Deterministic tie-breaking: primary sort descending by count, secondary sort ascending alphabetically.
  - Top 20 terms extracted per party.
- **TF-IDF:**
  - One document per party created by concatenating all accepted page texts for that party.
  - Fit TF-IDF across the party documents using `scikit-learn`'s `TfidfVectorizer` (sublinear TF scaling, smooth IDF).
  - Deterministic ranking: primary sort descending by TF-IDF score, secondary sort ascending alphabetically.
  - Clear documentation that TF-IDF measures distinctiveness within the corpus, not policy truth or importance.

### 1.7 Visualisation & Outputs
- **Word Cloud:** `wordcloud.WordCloud` saving to PNG (e.g. 1200x800).
- **Run Directory:** Timestamped output folder (e.g., `outputs/run_YYYYMMDD_HHMMSS/`) to avoid overwriting previous runs.
- **Artifacts:**
  - `manifest.csv` (all attempted URLs, HTTP status, final URL, bytes, extraction status, failure reasons).
  - `raw_text/` (individual extracted text files per page with metadata header).
  - `frequency_top20.csv` and `frequency_all.csv`.
  - `tfidf_top20.csv` and `tfidf_all.csv`.
  - PNG word clouds for both frequency and TF-IDF per party.

---

## 2. Phase 0 Specification Review & Decisions

1. **Party Allowed Hostnames:**
   - Represented as an explicit list in the configuration (e.g. `allowed_domains: ["www.national.org.nz", "national.org.nz"]`).
   - Subdomains outside this list are treated as external and rejected.

2. **Multiple Starting URLs & Corpus Grouping:**
   - A party configuration supports a list of starting URLs: `starting_urls: list[str]`.
   - All unique pages crawled from these starting URLs and their first-level links are collected, extracted, and aggregated into a single unified corpus per party.

3. **Default Exclusions for Non-Policy Pages:**
   - Exclude URL patterns matching administrative, transactional, or social actions:
     - `/(donate|contribute|give|join|membership|volunteer|get-involved|shop|cart|checkout|store|login|signin|register|privacy|terms|cookie|contact|contact-us)`
     - File extensions that are not HTML (e.g. `.pdf`, `.zip`, `.docx`, `.png`, `.jpg`, `.mp4`). Note: PDF support is explicitly deferred to later phase.
     - External links, `mailto:`, `tel:`, `javascript:`.

4. **Visualisation Outputs:**
   - Both Term Frequency (`<party>_frequency.png`) and TF-IDF (`<party>_tfidf.png`) word clouds are generated by default for each party (top 20 terms).
