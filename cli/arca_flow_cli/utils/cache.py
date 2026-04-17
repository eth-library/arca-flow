"""File-hash-based cache for tool version checks.

Stores tool versions in ``.venv/.dap-tool-cache.json`` and invalidates
when any of ``uv.lock``, ``flake.lock``, or ``flake.nix`` change.
"""

import hashlib
import json
from pathlib import Path

from arca_flow_cli.theme import FAIL

_WATCHED_FILES = ("uv.lock", "flake.lock", "flake.nix")
_CACHE_FILE = ".dap-tool-cache.json"


def _cache_path() -> Path:
    return Path.cwd() / ".venv" / _CACHE_FILE


def _compute_fingerprint() -> str:
    """SHA-256 fingerprint of watched lock/config files."""
    h = hashlib.sha256()
    root = Path.cwd()
    for name in _WATCHED_FILES:
        path = root / name
        if path.is_file():
            h.update(path.read_bytes())
        h.update(b"\x00")
    return h.hexdigest()


def load_tool_cache() -> list[tuple[str, str, str]] | None:
    """Return cached tool info rows if the cache is valid, else ``None``."""
    path = _cache_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("fingerprint") != _compute_fingerprint():
            return None
        return [(t["name"], t["version"], "" if t["found"] else FAIL) for t in data["tools"]]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def save_tool_cache(rows: list[tuple[str, str, str]]) -> None:
    """Write tool info rows to the cache file."""
    data = {
        "fingerprint": _compute_fingerprint(),
        "tools": [
            {"name": name, "version": ver, "found": ver != "not found"} for name, ver, _ in rows
        ],
    }
    try:
        path = _cache_path()
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass  # Cache write failures are non-fatal; tool info is transient.


def delete_tool_cache() -> None:
    """Remove the cache file if it exists."""
    path = _cache_path()
    if path.is_file():
        path.unlink()
