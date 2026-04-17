"""Tests for tool version cache."""

from pathlib import Path
from unittest.mock import patch

import pytest
from arca_flow_cli.utils.cache import (
    _compute_fingerprint,
    delete_tool_cache,
    load_tool_cache,
    save_tool_cache,
)

SAMPLE_ROWS = [
    ("python", "3.12.12", ""),
    ("uv", "0.9.29", ""),
    ("dap", "0.1.0", ""),
    ("ruff", "not found", "[error]\u2717[/]"),
]


@pytest.fixture()
def _project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Set cwd to a temp dir with watched files and a .venv directory."""
    (tmp_path / "uv.lock").write_text("uv-lock-content")
    (tmp_path / "flake.lock").write_text("flake-lock-content")
    (tmp_path / "flake.nix").write_text("flake-nix-content")
    (tmp_path / ".venv").mkdir()
    monkeypatch.chdir(tmp_path)


@pytest.mark.usefixtures("_project_dir")
class TestToolCache:
    def test_save_and_load_roundtrip(self):
        save_tool_cache(SAMPLE_ROWS)
        loaded = load_tool_cache()
        assert loaded is not None
        assert len(loaded) == len(SAMPLE_ROWS)
        for (name, ver, _icon), (orig_name, orig_ver, _orig_icon) in zip(
            loaded, SAMPLE_ROWS, strict=True
        ):
            assert name == orig_name
            assert ver == orig_ver

    def test_load_returns_none_when_no_cache(self):
        assert load_tool_cache() is None

    def test_load_returns_none_when_fingerprint_changes(self):
        save_tool_cache(SAMPLE_ROWS)
        # Modify a watched file to change the fingerprint
        Path("uv.lock").write_text("changed-content")
        assert load_tool_cache() is None

    def test_load_returns_none_on_corrupt_json(self):
        cache_path = Path(".venv") / ".dap-tool-cache.json"
        cache_path.write_text("not-json{{{")
        assert load_tool_cache() is None

    def test_delete_removes_file(self):
        save_tool_cache(SAMPLE_ROWS)
        cache_path = Path(".venv") / ".dap-tool-cache.json"
        assert cache_path.is_file()
        delete_tool_cache()
        assert not cache_path.is_file()

    def test_delete_noop_when_missing(self):
        delete_tool_cache()  # should not raise

    def test_fingerprint_changes_with_file_content(self):
        fp1 = _compute_fingerprint()
        Path("flake.nix").write_text("changed")
        fp2 = _compute_fingerprint()
        assert fp1 != fp2

    def test_fingerprint_stable_for_same_content(self):
        fp1 = _compute_fingerprint()
        fp2 = _compute_fingerprint()
        assert fp1 == fp2

    def test_found_icon_roundtrip(self):
        """Found tools get empty icon, not-found tools get FAIL icon."""
        save_tool_cache(SAMPLE_ROWS)
        loaded = load_tool_cache()
        assert loaded is not None
        # "python" was found → empty icon
        assert loaded[0][2] == ""
        # "ruff" was not found → FAIL icon (Rich markup)
        assert loaded[3][2] != ""

    def test_welcome_uses_cache(self):
        """welcome() should use cached rows and skip subprocess calls."""
        save_tool_cache(SAMPLE_ROWS)
        with patch("arca_flow_cli.commands.env._tool_info") as mock_tool_info:
            from arca_flow_cli.app import app
            from typer.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(app, ["welcome"])
            assert result.exit_code == 0
            mock_tool_info.assert_not_called()

    def test_welcome_populates_cache_on_miss(self):
        """welcome() should call _tool_info and save cache when no cache exists."""
        with (
            patch(
                "arca_flow_cli.commands.env._tool_info", return_value=SAMPLE_ROWS
            ) as mock_tool_info,
            patch("arca_flow_cli.commands.env.save_tool_cache") as mock_save,
        ):
            from arca_flow_cli.app import app
            from typer.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(app, ["welcome"])
            assert result.exit_code == 0
            mock_tool_info.assert_called_once()
            mock_save.assert_called_once_with(SAMPLE_ROWS)
