"""PubNet configuration management.

Stores persistent settings in ~/.pubnet/config.toml.
Key resolution order: explicit parameter > environment variable > config file.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".pubnet"
CONFIG_PATH = CONFIG_DIR / "config.toml"

# ---------------------------------------------------------------------------
# Low-level read / write
# ---------------------------------------------------------------------------


def _read_toml(path: Path) -> dict:
    """Read a TOML file, returning an empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # fallback for 3.10
        except ImportError:
            # Last resort: minimal hand-parse for simple key=value pairs
            return _read_toml_fallback(path)
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not parse %s: %s", path, exc)
        return {}


def _read_toml_fallback(path: Path) -> dict:
    """Minimal TOML reader for flat key = \"value\" files (no tables)."""
    data: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            data[key] = val
    return data


def _write_toml(path: Path, data: dict) -> None:
    """Write a flat dict as TOML (simple key = \"value\" format)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# PubNet configuration", "# See: https://github.com/drsanjivk/pubnet", ""]
    for key, val in sorted(data.items()):
        if val is None:
            continue
        lines.append('%s = "%s"' % (key, val))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_config() -> dict:
    """Return the full config dict from ~/.pubnet/config.toml."""
    return _read_toml(CONFIG_PATH)


def set_config(key: str, value: str) -> None:
    """Set a single config key and persist to disk."""
    data = get_config()
    data[key] = value
    _write_toml(CONFIG_PATH, data)
    logger.info("Saved %s to %s", key, CONFIG_PATH)


def remove_config(key: str) -> bool:
    """Remove a config key. Returns True if the key existed."""
    data = get_config()
    if key not in data:
        return False
    del data[key]
    _write_toml(CONFIG_PATH, data)
    return True


def resolve_serpapi_key(explicit: str | None = None) -> str | None:
    """Resolve the SerpAPI key with priority: explicit > env > config file.

    Args:
        explicit: Key passed directly (e.g. from CLI --serpapi-key).

    Returns:
        The API key string, or None if not configured anywhere.
    """
    if explicit:
        return explicit
    env_key = os.environ.get("SERPAPI_KEY") or os.environ.get("SERPAPI_API_KEY")
    if env_key:
        return env_key
    cfg = get_config()
    return cfg.get("serpapi_key") or None
