# Project Retrospective & Lessons Learned

## Non-Policy Page Exclusions & URL Filtering
- **Prompt:**
  > "Add exclusions to stop URLs that contain these tags from being accessed: /groups, mp-news, sign-in, tos, rules, bod, ourcandidates, our-team, members, about_our_charter, our_people, about_us_our_mps, get_involved, membership-join, sign_up, work-for-us, email-protection, calendar, get-involved, store, search, facebook, subscribe, the-team, -candidates, in-memory"
- **Lessons Learned:**
  - Expanding substring patterns for site-specific administrative, candidate bio, governance (`bod`, `about_our_charter`, `rules`), engagement (`get_involved`, `membership-join`, `subscribe`, `work-for-us`), and social/technical tracking tags (`facebook`, `email-protection`, `search`, `calendar`) prevents crawling peripheral campaign apparatus while maintaining pure focus on substantive policy platforms.
  - Substring-level URL rejection catches both path segments and URL parameter/filename variations containing these tokens.

- **Prompt:**
  > "Add code to stop the use of data from pages unrelated to policies, like "party-information", "about", "news", "health and safety" , "our people", "payment terms and conditions", "terms of service" and such like. I only want the data from policy websites. If this is not possible, let me know if you want the lonks I want excluded provided to you"
- **Lessons Learned:**
  - Political party starting policy landing pages frequently link in their navigation header or footer to administrative, organisational, and press release sections (e.g. `/news`, `/about`, `/team`, `/our-people`, `/mps`, `/health-and-safety`, `/party-information`, terms of service, payment policies).
  - Without expanding URL exclusion patterns, a 1-level crawl can inadvertently ingest dozens of non-policy biographies and announcements, polluting word cloud frequencies with names and operational boilerplate.
  - Making these exclusions configurable in `config.yaml` under `exclusions.path_patterns` (as well as baking them into `ExclusionConfig` defaults) allows users to filter both exact paths and path prefixes cleanly without altering application code or needing manual individual link exclusion lists.

- **Te Reo Māori Support:** The tokenisation regex explicitly encompasses Unicode macron characters (`[a-z\u0101\u0113\u012b\u014d\u016b]{3,}`), ensuring vital civic and cultural policy terms (such as `whānau`, `māori`, `hauora`) are preserved in analytical results.
- **Deterministic Tie-Breaking:** Enforcing `(-count, term)` sorting guarantees completely repeatable frequency rankings across test environments and runs.

- **Dual-Tier Content Extraction:** Pairing `trafilatura` (for heuristic-based boilerplate, navbar, and footer removal) with a BeautifulSoup DOM fallback ensures substantive content is captured even on unconventional page layouts without guessing fake content.
- **Traceable File Storage:** Prepending YAML frontmatter with `source_url`, `final_url`, `party_id`, `extraction_method`, and character/word counts keeps raw extracted files self-describing and audit-ready.

- **MockTransport Testing:** Using `httpx.MockTransport` allows comprehensive testing of network error handling, status code responses, redirects, body size limits, and `robots.txt` compliance in milliseconds without external network access.
- **HTTP Status Code Evaluation Order:** Checking `resp.status_code >= 400` before inspecting `Content-Type` headers ensures HTTP error responses (such as 404/500 text/plain error pages) are accurately reported as HTTP status failures rather than obscure mime-type mismatches.
- **Strict Depth Isolation:** Explicitly restricting link discovery to `is_starting_page=True` guarantees the crawler never strays beyond one link depth.

- **Pydantic Model Validation:** Cross-field validation (e.g., ensuring `starting_urls` hosts match `allowed_domains`) via `@model_validator(mode="after")` catches configuration discrepancies before any network requests are triggered.
- **URL Normalisation:** Distinguishing between an unlisted subdomain (`DISALLOWED_SUBDOMAIN`) and a foreign domain (`EXTERNAL_HOST`) provides actionable rejection logs for auditing crawler behaviour.
- **Deterministic Deduplication:** Stripping fragments while preserving query strings ensures deduplication works reliably without accidentally discarding pagination or filter parameters.

- **Python 3.14 Compatibility:** All 132 dependencies (including C/binary extensions like `scipy`, `numpy`, `pillow`, `lxml`, `pydantic-core`) install cleanly and quickly via `uv`.
- **Hatchling Editable Install Ordering:** In editable mode with `hatchling`, the package module directory (`src/nz_policy_wordcloud/__init__.py`) must exist on disk before running `uv pip install -e .` so that the build hook discovers the package structure correctly.
- **Rust-style Error Handling:** The package name on PyPI is `result` (`from result import Ok, Err, Result`).
- **Smoke Tests:** Importing `scikit-learn` and `wordcloud` for the very first time on Python 3.14 takes a couple of seconds to compile bytecode, but subsequent test runs execute in ~2 seconds.
