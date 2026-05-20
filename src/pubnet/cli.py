"""PubNet CLI - publication network analyser.

Entry points:
    pubnet analyze --scholar-url <url>
    pubnet analyze --builtin
    pubnet demo
    pubnet gui
    pubnet cache list | clear
"""

from __future__ import annotations

import json
import sys
import logging

import click

from pubnet import __version__


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(__version__, prog_name="pubnet")
def main():
    """PubNet - Publication network analyser for researchers."""


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--scholar-url", default=None, help="Google Scholar profile URL.")
@click.option("--author-id", default=None, help="Google Scholar author ID.")
@click.option("--builtin", "use_builtin", is_flag=True, help="Use bundled demo profile.")
@click.option("--format", "ref_format", default="apa", type=click.Choice(["apa", "mla", "bibtex", "vancouver", "chicago"], case_sensitive=False), help="Reference format.")
@click.option("--topics", default=5, type=int, help="Number of topic clusters.")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output HTML path.")
@click.option("--no-cache", is_flag=True, help="Force fresh Scholar fetch.")
@click.option("--crossref/--no-crossref", default=True, help="Enrich via Crossref API (corrects venue names, adds DOIs).")
@click.option("--serpapi-key", default=None, envvar="SERPAPI_KEY", help="SerpAPI key (or set SERPAPI_KEY env var, or use `pubnet config set serpapi-key`).")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def analyze(scholar_url, author_id, use_builtin, ref_format, topics, output, no_cache, crossref, serpapi_key, verbose):
    """Analyse a Scholar profile and generate an HTML report."""
    _setup_logging(verbose)

    from pubnet.fetch import fetch_profile, load_demo, FetchError
    from pubnet.analyze import (
        clean_publications,
        build_coauthor_graph,
        compute_citation_trends,
        cluster_topics,
        compute_stats,
    )
    from pubnet.formatters import format_reference

    # --- Resolve data source ---
    if use_builtin:
        click.echo("Loading built-in demo profile...")
        author = load_demo()
    elif scholar_url:
        click.echo("Fetching profile: " + scholar_url)
        try:
            author = fetch_profile(scholar_url, use_cache=not no_cache, serpapi_key=serpapi_key)
        except FetchError as exc:
            click.echo("Error: " + str(exc), err=True)
            sys.exit(1)
    elif author_id:
        click.echo("Fetching profile: " + author_id)
        try:
            author = fetch_profile(author_id, use_cache=not no_cache, serpapi_key=serpapi_key)
        except FetchError as exc:
            click.echo("Error: " + str(exc), err=True)
            sys.exit(1)
    else:
        click.echo("Error: provide --scholar-url, --author-id, or --builtin", err=True)
        sys.exit(1)

    # --- Clean ---
    pubs = clean_publications(author.publications)
    click.echo("Loaded %d publications for %s" % (len(pubs), author.name))

    # --- Crossref enrichment (corrects venue names, adds DOIs) ---
    if crossref:
        from pubnet.crossref import enrich_publications as crossref_enrich
        click.echo("Enriching via Crossref API (corrects venue names, adds DOIs)...")
        cr_results = crossref_enrich(pubs, max_lookups=None)
        corrections = 0
        for idx, cr in cr_results.items():
            if cr.venue_corrected and pubs[idx].venue:
                old = pubs[idx].venue
                if old != cr.venue_corrected and len(cr.venue_corrected) > 3:
                    pubs[idx].venue = cr.venue_corrected
                    corrections += 1
        if corrections:
            click.echo("  Corrected %d venue names via Crossref" % corrections)

    # --- Journal IF lookup ---
    from pubnet.journal_if import JournalIFLookup
    click.echo("Looking up journal impact factors...")
    if_lookup = JournalIFLookup()
    impact_factors = if_lookup.enrich_publications(pubs)

    # --- Analyse ---
    click.echo("Running analysis...")
    graph = build_coauthor_graph(author, pubs)
    trends = compute_citation_trends(pubs)
    topic_result = cluster_topics(pubs, num_clusters=topics)
    stats = compute_stats(author, pubs, impact_factors=impact_factors)

    # --- Print summary ---
    click.echo()
    click.echo("  " + author.name)
    if author.affiliation:
        click.echo("  " + author.affiliation)
    click.echo("  " + "-" * 39)
    click.echo("  Publications:      %d" % stats.total_publications)
    click.echo("  Total citations:   %d" % stats.total_citations)
    click.echo("  h-index:           %d" % stats.h_index)
    click.echo("  i10-index:         %d" % stats.i10_index)
    click.echo("  Years active:      %s" % stats.years_active)
    click.echo("  Co-authors:        %d" % stats.unique_coauthors)
    click.echo("  Top venue:         %s (%d pubs)" % (stats.top_venue, stats.top_venue_count))
    click.echo("  Avg cites/paper:   %s" % stats.avg_citations_per_paper)
    click.echo()

    # --- Top publications ---
    click.echo("  Top publications by citations:")
    for pub in sorted(pubs, key=lambda p: p.citations, reverse=True)[:5]:
        click.echo("    [%4d cites] %s" % (pub.citations, pub.title[:70]))
        click.echo("              %s, %s" % (pub.venue or "Unknown", pub.year or "n.d."))
    click.echo()

    # --- Topic clusters ---
    if topic_result.clusters:
        click.echo("  Topic clusters (%d):" % topic_result.num_clusters)
        for cluster in topic_result.clusters:
            kw = ", ".join(cluster.keywords[:3])
            click.echo("    Cluster %d: %s (%d pubs, %d cites)" % (
                cluster.cluster_id, kw, cluster.publication_count, cluster.total_citations))
        click.echo()

    # --- Sample reference ---
    if pubs:
        top_pub = max(pubs, key=lambda p: p.citations)
        click.echo("  Sample reference (%s):" % ref_format.upper())
        click.echo("    %s" % format_reference(top_pub, style=ref_format))
        click.echo()

    # --- HTML report ---
    from pubnet.report import render_report
    from pathlib import Path

    if not output:
        safe_name = author.name.lower().replace(" ", "_")
        output = "%s_pubnet.html" % safe_name

    click.echo("  Generating HTML report -> %s" % output)
    html = render_report(
        author=author,
        publications=pubs,
        stats=stats,
        coauthor_graph=graph,
        citation_trends=trends,
        topic_analysis=topic_result,
        impact_factors=impact_factors,
    )
    Path(output).write_text(html, encoding="utf-8")
    click.echo("  Done! Report saved to %s" % output)


# ---------------------------------------------------------------------------
# demo shortcut
# ---------------------------------------------------------------------------

@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def demo(ctx, verbose):
    """Quick demo using the bundled profile (shortcut for analyze --builtin)."""
    ctx.invoke(analyze, use_builtin=True, verbose=verbose)


# ---------------------------------------------------------------------------
# gui command
# ---------------------------------------------------------------------------

@main.command()
@click.option("--port", default=8050, type=int, help="Server port.")
@click.option("--scholar-url", default=None, help="Pre-load a Scholar profile URL.")
@click.option("--debug", is_flag=True, help="Enable Dash debug mode.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def gui(port, scholar_url, debug, verbose):
    """Launch the interactive Dash GUI."""
    _setup_logging(verbose)
    click.echo("Starting PubNet GUI on http://localhost:%d" % port)

    from pubnet.gui.app import create_app
    app = create_app(scholar_url=scholar_url)
    app.run(port=port, debug=debug)


# ---------------------------------------------------------------------------
# cache commands
# ---------------------------------------------------------------------------

@main.group()
def cache():
    """Manage cached Scholar profiles."""


@cache.command("list")
def cache_list():
    """List cached profiles."""
    from pubnet.fetch import list_cached_profiles

    profiles = list_cached_profiles()
    if not profiles:
        click.echo("No cached profiles.")
        return
    for p in profiles:
        click.echo("  %s  %s  (%d pubs)" % (p["scholar_id"], p["name"], p["publications"]))


@cache.command("clear")
@click.confirmation_option(prompt="Delete all cached profiles?")
def cache_clear():
    """Clear all cached profiles."""
    from pubnet.fetch import clear_cache

    count = clear_cache()
    click.echo("Removed %d cached profile(s)." % count)


# ---------------------------------------------------------------------------
# config commands
# ---------------------------------------------------------------------------

@main.group()
def config():
    """Manage PubNet configuration (~/.pubnet/config.toml)."""


@config.command("set")
@click.argument("key", type=click.Choice(["serpapi-key"], case_sensitive=False))
@click.argument("value")
def config_set(key, value):
    """Set a configuration value (e.g. pubnet config set serpapi-key <key>)."""
    from pubnet.config import set_config

    # Normalise CLI key name to config key name
    config_key = key.replace("-", "_")
    set_config(config_key, value)
    click.echo("Saved %s to ~/.pubnet/config.toml" % key)


@config.command("show")
def config_show():
    """Show current configuration."""
    from pubnet.config import get_config, CONFIG_PATH, resolve_serpapi_key

    cfg = get_config()
    if not cfg:
        click.echo("No configuration set. File: %s" % CONFIG_PATH)
        click.echo("Use: pubnet config set serpapi-key <your-key>")
        return

    click.echo("Config file: %s" % CONFIG_PATH)
    for key, val in sorted(cfg.items()):
        # Mask API keys for display
        if "key" in key.lower() and val and len(val) > 8:
            display = val[:4] + "..." + val[-4:]
        else:
            display = val
        click.echo("  %s = %s" % (key, display))

    # Show effective SerpAPI key source
    resolved = resolve_serpapi_key()
    if resolved:
        import os
        if os.environ.get("SERPAPI_KEY") or os.environ.get("SERPAPI_API_KEY"):
            click.echo("  (SerpAPI key active via environment variable)")
        elif cfg.get("serpapi_key"):
            click.echo("  (SerpAPI key active via config file)")


@config.command("path")
def config_path():
    """Print the config file path."""
    from pubnet.config import CONFIG_PATH
    click.echo(str(CONFIG_PATH))


@config.command("remove")
@click.argument("key", type=click.Choice(["serpapi-key"], case_sensitive=False))
def config_remove(key):
    """Remove a configuration value."""
    from pubnet.config import remove_config

    config_key = key.replace("-", "_")
    if remove_config(config_key):
        click.echo("Removed %s from config." % key)
    else:
        click.echo("Key %s not found in config." % key)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
