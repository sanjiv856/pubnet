# CHANGELOG.md - PubNet

Significant changes, grouped by date. Not every commit, just things
worth knowing about when picking up the project after a break.

## 2026-05-20 (v0.1.3)

- **SerpAPI integration** - Added SerpAPI as primary fetch backend, bypasses Scholar rate-limiting and CAPTCHA blocks. Falls back to `scholarly` when no key is configured.
- **Config system** - New `~/.pubnet/config.toml` for persistent settings. SerpAPI key resolves with priority: `--serpapi-key` CLI flag > `SERPAPI_KEY` env var > config file.
- **CLI config commands** - `pubnet config set serpapi-key <key>`, `pubnet config show`, `pubnet config path`, `pubnet config remove serpapi-key`
- **Adaptive throttling** - Increased base delay (4-8s), exponential backoff on Scholar blocks, max 3 retries per publication
- **Partial save on block** - When Scholar blocks mid-fetch, saves already-fetched publications instead of losing all progress
- **Progress logging** - Logs `Fetching publication N/M ...` during fetch
- **Bug fix: SerpAPI citations** - Fixed Pydantic validation error when SerpAPI returns `None` for citation count
- **Bug fix: empty author names** - Fixed `IndexError` crash in all five reference formatters (APA, MLA, BibTeX, Vancouver, Chicago) when publications have empty author strings

## 2026-05-14

- **Project created** - pyproject.toml with hatchling, 13 dependencies, `pubnet` CLI entry point
- **Core models** - 11 Pydantic v2 models in models.py (Publication, Author, CoauthorGraph, CitationTrends, TopicAnalysis, StatsSummary, AnalysisResult, etc.)
- **Scholar fetcher** - fetch.py with scholarly integration, JSON cache (~/.pubnet/cache/), URL parsing, rate limiting, custom exceptions
- **Data QA** - clean_publications() with rapidfuzz dedup (>90% threshold), null-fill, author name normalisation
- **Demo dataset** - 27 synthetic publications in data/demo.json (Sanjiv Kumar, h-index 18, 4547 citations)
- **Analysis modules** - Co-author graph (networkx), citation trends (yearly + rolling h-index), topic clusters (TF-IDF + k-means), stats summary
- **Reference formatters** - APA, MLA, BibTeX, Vancouver, Chicago with proper author truncation rules
- **Journal IF lookup** - Bundled Scimago CSV (60 journals) + OpenAlex API fallback with fuzzy venue matching
- **Static HTML report** - Jinja2 template with embedded CSS/JS, Plotly charts, inline SVG network, dark mode, ~60 KB output
- **Dash GUI** - Full interactive app: topbar, sidebar (nav + filters), stat cards, dash-cytoscape network, Plotly trends/clusters, sortable pub table with badges
- **Cross-filtering** - Network node click filters pubs by co-author; cluster click filters by topic; composes with year-range and citation sliders
- **9 Dash callbacks** - Analyze, view nav, filters, sort, network click, cluster click, clear filters, export, year-range auto-update
- **96 tests passing** - models, fetch, analyze, formatters, journal_if, report, GUI components
- **Project docs** - PLAN.md (full roadmap), CLAUDE.md, TASKS.md, DECISIONS.md, CONVERSATION_LOG.md

---

[Add new entries at the top, most recent first.]
