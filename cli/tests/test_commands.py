"""Tests for dap CLI commands — structural and behavioral."""

from unittest.mock import patch

from arca_flow_cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


# ── Structural: commands exist and show help ──


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Developer tools" in result.output


def test_test_help():
    result = runner.invoke(app, ["test", "--help"])
    assert result.exit_code == 0
    assert "pytest" in result.output


def test_lint_help():
    result = runner.invoke(app, ["lint", "--help"])
    assert result.exit_code == 0
    assert "--fix" in result.output


def test_typecheck_help():
    result = runner.invoke(app, ["typecheck", "--help"])
    assert result.exit_code == 0


def test_check_help():
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "quality" in result.output.lower()


def test_welcome_help():
    result = runner.invoke(app, ["welcome", "--help"])
    assert result.exit_code == 0


def test_tools_help():
    result = runner.invoke(app, ["tools", "--help"])
    assert result.exit_code == 0
    assert "--all" in result.output


def test_clean_help():
    result = runner.invoke(app, ["clean", "--help"])
    assert result.exit_code == 0


def test_reset_help():
    result = runner.invoke(app, ["reset", "--help"])
    assert result.exit_code == 0


def test_k8s_help():
    result = runner.invoke(app, ["k8s", "--help"])
    assert result.exit_code == 0
    assert "up" in result.output
    assert "down" in result.output
    assert "restart" in result.output
    assert "status" in result.output
    assert "logs" in result.output
    assert "shell" in result.output


# ── Behavioral: commands call the right tools ──


@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=0)
def test_lint_calls_ruff(mock_run):
    result = runner.invoke(app, ["lint"])
    assert result.exit_code == 0
    calls = [str(c) for c in mock_run.call_args_list]
    assert any("ruff" in c and "check" in c for c in calls)
    assert any("ruff" in c and "format" in c for c in calls)


@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=0)
def test_lint_fix_calls_ruff_fix(mock_run):
    result = runner.invoke(app, ["lint", "--fix"])
    assert result.exit_code == 0
    calls = [str(c) for c in mock_run.call_args_list]
    assert any("ruff" in c and "--fix" in c for c in calls)


@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=0)
def test_test_calls_pytest(mock_run):
    result = runner.invoke(app, ["test"])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "pytest"


@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=0)
def test_typecheck_calls_mypy(mock_run):
    result = runner.invoke(app, ["typecheck"])
    assert result.exit_code == 0
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "mypy"


@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=0)
def test_check_runs_all_steps(mock_run):
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    calls = [str(c) for c in mock_run.call_args_list]
    assert any("ruff" in c for c in calls)
    assert any("mypy" in c for c in calls)
    assert any("pytest" in c for c in calls)


@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=1)
def test_check_fails_fast_on_lint(mock_run):
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 1
    # Should have stopped after first ruff call failed
    assert mock_run.call_count <= 2  # at most ruff check (failed)


@patch("arca_flow_cli.commands.env.run_passthrough", return_value=0)
def test_reset_calls_uv_sync(mock_run):
    result = runner.invoke(app, ["reset", "--yes"])
    assert result.exit_code == 0
    calls = [str(c) for c in mock_run.call_args_list]
    assert any("uv" in c and "sync" in c for c in calls)
