# PubNet

**Visualise your research footprint.** PubNet takes a Google Scholar profile and turns it into interactive visualisations - co-author networks, citation trends, topic clusters, journal impact factors, and formatted references - all from a single command.

**[Try the live demo](https://pubnetwork.onrender.com/)** - no install required.

## What PubNet does

Paste any Google Scholar profile URL, and PubNet will:

- Map your **co-author network** as an interactive force-directed graph
- Chart your **citation trends** over time with a rolling h-index overlay
- Track your **publications per year** to show research output
- Cluster your work into **research topics** using TF-IDF and k-means
- Look up **journal impact factors** from a bundled database of 4,600+ journals
- Correct venue names via the **Crossref API** before impact factor lookup
- Format every publication as a **copyable reference** in APA, MLA, BibTeX, Vancouver, or Chicago style
- Export everything as **JSON or CSV**

PubNet has two interfaces: a **CLI** that generates self-contained HTML reports you can share, and an interactive **web GUI** for live exploration with filters, sorting, and cross-linked charts.

## Quick start

### Option 1: Try it online

Visit **[pubnetwork.onrender.com](https://pubnetwork.onrender.com/)** and click Analyze. A demo profile loads immediately. To analyse your own profile, paste your Google Scholar URL and click Analyze.

### Option 2: Install locally

```bash
pip install pubnetwork
```

Requires Python 3.10+. Then:

```bash
# Generate an HTML report
pubnet analyze --scholar-url "https://scholar.google.com/citations?user=ML7X29AAAAAJ"

# Or launch the interactive GUI
pubnet gui

# Or try the bundled demo
pubnet demo
```

### Option 3: Clone and develop

```bash
git clone https://github.com/sanjiv856/pubnet.git
cd pubnet
pip install -e ".[dev]"
pytest tests/
```

## CLI reference

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

pubnet gui                     Launch interactive web GUI at localhost:8050
pubnet demo                    Generate report from bundled demo profile
pubnet cache list              Show cached profiles
pubnet cache clear             Remove all cached data
```

Profiles are cached to `~/.pubnet/cache/` so repeated analyses don't re-fetch from Scholar.

## How it works

```
Scholar URL → Fetch → Clean/Dedup → Crossref Enrich → Analyse → Render
```

The core library is a set of pure-function modules shared by both CLI and GUI:

| Module | What it does |
|--------|-------------|
| `fetch.py` | Fetches Scholar profiles via SerpAPI or scholarly, with JSON caching |
| `analyze.py` | Builds co-author graphs, citation trends, topic clusters, summary stats |
| `formatters.py` | Formats references in APA, MLA, BibTeX, Vancouver, and Chicago styles |
| `journal_if.py` | Looks up impact factors from a bundled 4,600-journal Scimago database, with OpenAlex API fallback |
| `crossref.py` | Corrects venue names and retrieves DOIs via the free Crossref REST API |
| `report.py` | Renders self-contained HTML reports with embedded Plotly charts |
| `gui/` | Dash web app with sidebar navigation, filters, and interactive cross-linked charts |

## Tech stack

Python 3.10+ with scholarly, pydantic, networkx, dash, dash-cytoscape, plotly, scikit-learn, click, jinja2, rapidfuzz, and SerpAPI for cloud deployment.

## Tests

```bash
pytest tests/
```

142+ tests covering models, fetcher, analysis, formatters, report rendering, CLI, and GUI components.

## License

PolyForm Noncommercial 1.0.0 - free for academic, educational, and non-commercial research use. Commercial use requires a separate license. See [LICENSE](LICENSE) for details.