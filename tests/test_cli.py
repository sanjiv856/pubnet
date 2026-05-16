"""Tests for the Click CLI entry points."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from pubnet.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "PubNet" in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "pubnet" in result.output

    def test_no_command_shows_help(self, runner):
        result = runner.invoke(main, [])
        # Click groups show help on no subcommand (may exit 0 or 2)
        assert "analyze" in result.output or "Usage" in result.output


class TestAnalyzeCommand:
    def test_analyze_no_source_exits(self, runner):
        """analyze with no --scholar-url, --author-id, or --builtin should fail."""
        result = runner.invoke(main, ["analyze"])
        assert result.exit_code != 0
        assert "provide" in result.output.lower() or "Error" in result.output

    def test_analyze_builtin(self, runner, tmp_path):
        """analyze --builtin should succeed and produce an HTML report."""
        output_file = str(tmp_path / "test_report.html")
        result = runner.invoke(main, ["analyze", "--builtin", "-o", output_file])
        assert result.exit_code == 0
        assert "Loading built-in demo profile" in result.output
        assert "publications" in result.output.lower()
        assert "h-index" in result.output.lower()
        assert Path(output_file).exists()
        html_content = Path(output_file).read_text(encoding="utf-8")
        assert "<html" in html_content.lower()

    def test_analyze_builtin_default_output(self, runner, tmp_path, monkeypatch):
        """Without -o, analyze should create <name>_pubnet.html in cwd."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["analyze", "--builtin"])
        assert result.exit_code == 0
        assert "Report saved" in result.output

    def test_analyze_verbose(self, runner, tmp_path):
        output_file = str(tmp_path / "verbose_report.html")
        result = runner.invoke(main, ["analyze", "--builtin", "-v", "-o", output_file])
        assert result.exit_code == 0

    def test_analyze_with_format(self, runner, tmp_path):
        """--format changes the sample reference style."""
        output_file = str(tmp_path / "mla_report.html")
        result = runner.invoke(main, ["analyze", "--builtin", "--format", "mla", "-o", output_file])
        assert result.exit_code == 0
        assert "MLA" in result.output

    def test_analyze_with_topics(self, runner, tmp_path):
        output_file = str(tmp_path / "topics_report.html")
        result = runner.invoke(main, ["analyze", "--builtin", "--topics", "3", "-o", output_file])
        assert result.exit_code == 0
        assert "Topic clusters" in result.output

    def test_analyze_invalid_format(self, runner):
        result = runner.invoke(main, ["analyze", "--builtin", "--format", "invalid"])
        assert result.exit_code != 0

    def test_analyze_scholar_url_fetch_error(self, runner):
        """--scholar-url with a fetch error should exit 1."""
        from pubnet.fetch import FetchError
        with patch("pubnet.fetch.fetch_profile", side_effect=FetchError("Blocked")):
            result = runner.invoke(main, ["analyze", "--scholar-url", "https://scholar.google.com/citations?user=FAKE"])
            assert result.exit_code != 0
            assert "Error" in result.output or "Blocked" in result.output

    def test_analyze_author_id_fetch_error(self, runner):
        from pubnet.fetch import FetchError
        with patch("pubnet.fetch.fetch_profile", side_effect=FetchError("Not found")):
            result = runner.invoke(main, ["analyze", "--author-id", "FAKEID"])
            assert result.exit_code != 0


class TestDemoCommand:
    def test_demo(self, runner):
        """demo should be a shortcut for analyze --builtin."""
        result = runner.invoke(main, ["demo"])
        assert result.exit_code == 0
        assert "Loading built-in demo profile" in result.output
        assert "h-index" in result.output.lower()

    def test_demo_help(self, runner):
        result = runner.invoke(main, ["demo", "--help"])
        assert result.exit_code == 0
        assert "Quick demo" in result.output


class TestGuiCommand:
    def test_gui_help(self, runner):
        result = runner.invoke(main, ["gui", "--help"])
        assert result.exit_code == 0
        assert "port" in result.output.lower()
        assert "scholar-url" in result.output.lower()

    def test_gui_imports_app(self):
        """Verify the gui/app module imports without errors."""
        from pubnet.gui.app import create_app
        app = create_app()
        assert app is not None


class TestCacheCommands:
    def test_cache_help(self, runner):
        result = runner.invoke(main, ["cache", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "clear" in result.output

    def test_cache_list(self, runner):
        result = runner.invoke(main, ["cache", "list"])
        assert result.exit_code == 0

    def test_cache_clear_confirmed(self, runner):
        """cache clear with --yes should succeed."""
        with patch("pubnet.fetch.clear_cache", return_value=0) as mock_clear:
            result = runner.invoke(main, ["cache", "clear", "--yes"])
            assert result.exit_code == 0
            assert "Removed" in result.output
            mock_clear.assert_called_once()

    def test_cache_clear_aborted(self, runner):
        """cache clear without --yes prompts, 'n' aborts."""
        result = runner.invoke(main, ["cache", "clear"], input="n\n")
        assert result.exit_code != 0 or "Aborted" in result.output


class TestSetupLogging:
    def test_setup_logging_normal(self):
        from pubnet.cli import _setup_logging
        import logging
        logging.root.handlers.clear()
        logging.root.setLevel(logging.WARNING)
        _setup_logging(False)
        assert logging.root.level == logging.INFO

    def test_setup_logging_verbose(self):
        from pubnet.cli import _setup_logging
        import logging
        logging.root.handlers.clear()
        logging.root.setLevel(logging.WARNING)
        _setup_logging(True)
        assert logging.root.level == logging.DEBUG
