# PubNet

Publication network analyser for researchers. Given a Google Scholar profile, PubNet fetches your publications and generates interactive visualisations: co-author networks, citation trends, topic clusters, journal impact factors, and formatted references.

## Features

- **Co-author network graph** - interactive force-directed graph showing collaboration patterns
- **Citation trends** - yearly citation counts with rolling h-index overlay
- **Publications per year** - output volume over time
- **Topic clusters** - TF-IDF + k-means clustering of research themes
- **Journal impact factors** - Scimago CSV lookup with OpenAlex API fallback
- **Crossref enrichment** - corrects venue names and adds DOIs via free Crossref API
- **Reference formatting** - APA, MLA, BibTeX, Vancouver, Chicago with copy-to-clipboard
- **Two interfaces** - CLI (self-contained HTML report) and Dash GUI (live interactive exploration)

## Install

```bash
pip install pubnetwork
```

Or for development:

```bash
git clone https://github.com/YOUR_USERNAME/pubnet.git
cd pubnet
pip install -e .
```

Requires Python 3.10+.

## Quick start

### Demo (bundled profile)

```bash
pubnet demo
```

Generates `sanjiv_kumar_pubnet.html` using the bundled Scholar profile.

### Analyse a Scholar profile

```bash
pubnet analyze --scholar-url "https://scholar.google.com/citations?user=ML7X29AAAAAJ"
```

Or by author ID:

```bash
pubnet analyze --author-id ML7X29AAAAAJ
```

### Interactive GUI

```bash
pubnet gui
```

Opens a Dash web app at `http://localhost:8050` with sidebar navigation, filters, and interactive charts.

## CLI options

```
pubnet analyze [OPTIONS]

  --scholar-url TEXT           Google Scholar profile URL
  --author-id TEXT             Google Scholar author ID
  --builtin                    Use bundled demo profile
  --format [apa|mla|bibtex|vancouver|chicago]
                               Reference format (default: apa)
  --topics INTEGER             Number of topic clusters (default: 5)
  -o, --output PATH            Output HTML file path
  --no-cache                   Force fresh Scholar fetch
  --crossref / --no-crossref   Crossref venue correction (default: enabled)
  -v, --verbose                Debug logging
```

## Architecture

```
Fetch (scholarly) -> Clean/Dedup (rapidfuzz) -> Crossref Enrich -> Analyse -> Render
```

Core library with pure-function analysis modules shared by both CLI and GUI:

| Module | Purpose |
|--------|---------|
| `fetch.py` | Scholar fetcher with JSON cache |
| `analyze.py` | Co-author graph, citation trends, topic clusters, stats |
| `formatters.py` | APA/MLA/BibTeX/Vancouver/Chicago references |
| `journal_if.py` | Scimago CSV + OpenAlex API impact factors |
| `crossref.py` | Free Crossref API for venue correction |
| `report.py` | Jinja2 HTML report renderer |
| `gui/` | Dash interactive app |

## Cache management

```bash
pubnet cache list    # Show cached profiles
pubnet cache clear   # Remove all cached data
```

Profiles are cached to `~/.pubnet/cache/` to avoid repeated Scholar fetches.

## Tech stack

Python 3.10+ with scholarly, pydantic, networkx, dash, dash-cytoscape, plotly, scikit-learn, click, jinja2, rapidfuzz.

## Tests

```bash
pip install -e .
pytest tests/
```