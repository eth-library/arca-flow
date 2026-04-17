"""Environment commands: welcome, tools, env, clean, reset."""

import contextlib
import json
import os
import shutil
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import typer

from arca_flow_cli.banner import render_startup_banner
from arca_flow_cli.theme import ARROW, FAIL, OK, WARN, console
from arca_flow_cli.utils.cache import delete_tool_cache, load_tool_cache, save_tool_cache
from arca_flow_cli.utils.run import run_capture, run_passthrough

_LOGO = files("arca_flow_cli").joinpath("logo.txt").read_text(encoding="utf-8")


def _get_version(cmd: list[str], prefix: str = "") -> str | None:
    """Get a tool version by running a command and stripping a prefix."""
    code, out = run_capture(cmd)
    if code != 0 or not out:
        return None
    if prefix:
        out = out.removeprefix(prefix)
    return out.strip().split("\n")[0]


def _get_path(name: str) -> str | None:
    """Get the install path of a command."""
    return shutil.which(name)


def _tool_row(name: str, ver: str | None, path: str | None = None) -> tuple[str, str, str]:
    """Return a (name, version, path) tuple for table display."""
    if ver:
        return name, ver, path or ""
    return name, "not found", ""


def _nix_tools() -> list[tuple[str, str, str]]:
    """Tools provided by Nix flake (basePackages)."""
    return [
        _tool_row("python", _get_version(["python", "--version"], "Python "), _get_path("python")),
        _tool_row("uv", _get_version(["uv", "--version"], "uv "), _get_path("uv")),
    ]


def _python_tools() -> list[tuple[str, str, str]]:
    """Python packages installed by uv into the virtualenv."""
    return [
        _tool_row("arca-flow", version("arca-flow-cli"), _get_path("arca-flow")),
        _tool_row(
            "dagster",
            _get_version(["python", "-c", "import dagster; print(dagster.__version__)"]),
            _get_path("dagster"),
        ),
        _tool_row("ruff", _get_version(["ruff", "--version"], "ruff "), _get_path("ruff")),
        _tool_row(
            "mypy",
            mypy_ver.split(" (")[0]
            if (mypy_ver := _get_version(["mypy", "--version"], "mypy "))
            else None,
            _get_path("mypy"),
        ),
        _tool_row("pytest", _get_version(["pytest", "--version"], "pytest "), _get_path("pytest")),
    ]


def _infra_tools() -> list[tuple[str, str, str]]:
    """Infrastructure tools from Nix (shown with --all)."""
    nix_ver = _get_version(["nix", "--version"], "nix (Nix) ")
    direnv_ver = _get_version(["direnv", "version"])

    code, out = run_capture(["kubectl", "version", "--client", "-o", "json"])
    kubectl_ver = None
    if code == 0:
        with contextlib.suppress(json.JSONDecodeError, KeyError):
            kubectl_ver = json.loads(out)["clientVersion"]["gitVersion"]

    helm_ver = _get_version(["helm", "version", "--short"])
    if helm_ver and "+" in helm_ver:
        helm_ver = helm_ver[: helm_ver.index("+")]

    return [
        _tool_row("nix", nix_ver, _get_path("nix")),
        _tool_row("direnv", direnv_ver, _get_path("direnv")),
        _tool_row("kubectl", kubectl_ver, _get_path("kubectl")),
        _tool_row("helm", helm_ver, _get_path("helm")),
    ]


def _print_tools_table(rows: list[tuple[str, str, str]]) -> None:
    """Print tools with version, icon, and path (for the tools command)."""
    for name, ver, path in rows:
        found = ver != "not found"
        icon = OK if found else ""
        style = "info" if found else "hint"
        path_hint = f"  [hint]{path}[/]" if path else ""
        console.print(f"  {name:<10} [{style}]{ver:<12}[/]{icon}{path_hint}")


def _print_info_rows(rows: list[tuple[str, str, str]], *, value_width: int = 0) -> None:
    """Print aligned name/value/icon rows for the welcome screen.

    Each row is (name, value, icon). Icon is only shown if non-empty
    (used for warnings or errors — found items have no icon).
    """
    for name, value, icon in rows:
        not_available = "not found" in value or "not set" in value
        style = "hint" if not_available else "info"
        icon_suffix = f"  {icon}" if icon else ""
        if value_width:
            console.print(f"  {name:<14} [{style}]{value:<{value_width}}[/]{icon_suffix}")
        else:
            console.print(f"  {name:<14} [{style}]{value}[/]{icon_suffix}")


def _tool_info() -> list[tuple[str, str, str]]:
    """Core tools as (name, version, icon) for welcome screen. No icon when found."""
    return [
        (name, ver, FAIL if ver == "not found" else "")
        for name, ver, _ in _nix_tools() + _python_tools()
    ]


def _env_info() -> list[tuple[str, str, str]]:
    """Environment paths as (name, value, icon) tuples. Only warn/fail icons shown."""
    rows: list[tuple[str, str, str]] = []
    cwd = Path.cwd()

    if (cwd / "flake.nix").exists():
        rows.append(("nix flake", str(cwd), ""))
    else:
        rows.append(("nix flake", "not found", FAIL))

    venv = os.getenv("VIRTUAL_ENV")
    if venv:
        icon = "" if Path(venv).exists() else WARN
        rows.append(("python venv", venv, icon))
    else:
        rows.append(("python venv", "not set", FAIL))

    dagster_home = os.getenv("DAGSTER_HOME")
    if dagster_home:
        icon = "" if Path(dagster_home).exists() else WARN
        rows.append(("DAGSTER_HOME", dagster_home, icon))
    else:
        rows.append(("DAGSTER_HOME", "not set", FAIL))

    return rows


def welcome() -> None:
    """Show welcome banner and environment info."""
    in_ci = bool(os.getenv("CI"))

    console.print()
    render_startup_banner(
        console,
        "arca-flow",
        "Orchestration Engine",
        _LOGO,
        show_logo=not in_ci,
    )

    console.print()
    console.print("  [title]Tools[/]")
    tool_rows = load_tool_cache()
    if tool_rows is None:
        tool_rows = _tool_info()
        save_tool_cache(tool_rows)
    _print_info_rows(tool_rows, value_width=10)

    console.print()
    console.print("  [title]Environment[/]")
    _print_info_rows(_env_info())

    if not in_ci and not os.getenv("ARCA_FLOW_QUIET"):
        console.print()
        console.print("  [title]Quick Start[/]")
        console.print(f"  {'af test':<14} Run tests (pytest)")
        console.print(f"  {'af check':<14} Run all quality checks (lint, typecheck, test)")
        console.print(f"  {'af tools':<14} Show installed tool versions")
        console.print()
        console.print("  [hint]Run 'af --help' for all commands (af is an alias for arca-flow)[/]")

    console.print()


def tools(
    all: bool = typer.Option(False, "--all", "-a", help="Include nix, direnv, kubectl, and helm."),
) -> None:
    """Show installed tool versions and paths.

    For dagster and dg commands, use them directly (e.g. 'dagster dev', 'dg --help').
    """
    console.print("  [title]Nix[/]")
    _print_tools_table(_nix_tools())
    if all:
        _print_tools_table(_infra_tools())
    console.print()
    console.print("  [title]Python (uv)[/]")
    _print_tools_table(_python_tools())
    console.print()


def env() -> None:
    """Show environment paths and status."""
    _print_info_rows(_env_info())
    console.print()


def clean(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Remove .venv and caches."""
    if not yes:
        typer.confirm("Remove .venv and all caches?", abort=True)
    console.print(f"  {ARROW} Cleaning environment...")
    delete_tool_cache()

    venv = Path(".venv")
    if venv.exists():
        shutil.rmtree(venv, ignore_errors=True)
        console.print(f"  {OK} Removed .venv")

    cache_patterns = [
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "*.egg-info",
    ]
    removed = 0
    for root_dir in [Path("."), Path("arca")]:
        if not root_dir.exists():
            continue
        for path in root_dir.rglob("*"):
            if path.is_dir() and any(path.match(p) for p in cache_patterns):
                shutil.rmtree(path, ignore_errors=True)
                removed += 1

    if removed:
        console.print(f"  {OK} Removed {removed} cache directories")

    console.print(f"  {OK} Environment cleaned")
    console.print()


def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Clean and reinstall dependencies."""
    if not yes:
        typer.confirm("Clean environment and reinstall?", abort=True)
    clean(yes=True)
    console.print(f"  {ARROW} Installing dependencies...")
    code = run_passthrough(["uv", "sync", "--extra", "dev", "--all-packages"])
    if code != 0:
        console.print("  [error]uv sync failed[/]")
        raise typer.Exit(1)
    console.print(f"  {OK} Environment reset complete")
    console.print()
