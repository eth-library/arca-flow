"""Hint commands for tools available directly in the shell."""

import typer

from arca_flow_cli.theme import ARROW, console


def uv(ctx: typer.Context) -> None:
    """Show how to use uv directly."""
    console.print(f"  {ARROW} uv is available directly in your shell.")
    console.print()
    console.print("  [title]Common commands[/]")
    console.print(f"  [command]{'uv sync':<26}[/] [hint]Install dependencies[/]")
    console.print(f"  [command]{'uv lock --upgrade':<26}[/] [hint]Update lockfile[/]")
    console.print(f"  [command]{'uv add <pkg>':<26}[/] [hint]Add a dependency[/]")
    console.print(f"  [command]{'uv run <cmd>':<26}[/] [hint]Run a command in the venv[/]")
    console.print()
    console.print("  [hint]Run 'uv --help' for all options.[/]")
    console.print()


def dagster(ctx: typer.Context) -> None:
    """Show how to use dagster and dg directly."""
    console.print(f"  {ARROW} dagster and dg are available directly in your shell.")
    console.print()
    console.print("  [title]Common commands[/]")
    console.print(f"  [command]{'dagster dev':<26}[/] [hint]Start the dev server[/]")
    console.print(f"  [command]{'dagster job execute':<26}[/] [hint]Run a job[/]")
    console.print(f"  [command]{'dg --help':<26}[/] [hint]Dagster CLI (project-scoped)[/]")
    console.print(f"  [command]{'dg check defs':<26}[/] [hint]Validate definitions[/]")
    console.print()
    console.print("  [hint]Run 'dagster --help' or 'dg --help' for all options.[/]")
    console.print()


def direnv(ctx: typer.Context) -> None:
    """Show how to use direnv directly."""
    console.print(f"  {ARROW} direnv is available directly in your shell.")
    console.print()
    console.print("  [title]Common commands[/]")
    console.print(f"  [command]{'direnv allow':<26}[/] [hint]Approve the .envrc file[/]")
    console.print(f"  [command]{'direnv reload':<26}[/] [hint]Force reload the environment[/]")
    console.print(f"  [command]{'direnv status':<26}[/] [hint]Show current direnv state[/]")
    console.print()
    console.print(
        "  [hint]The environment reloads automatically when"
        " pyproject.toml, flake.nix, flake.lock, or uv.lock change.[/]"
    )
    console.print()
