"""dap — Developer CLI for the Data Archive Pipeline (DAP) Orchestrator."""

from __future__ import annotations

from collections import OrderedDict
from importlib.metadata import version

import click
import typer
import typer.core

from arca_flow_cli.commands import dev, env, hints, k8s

# -- Command groups (ordered) ------------------------------------------------
COMMAND_GROUPS: OrderedDict[str, list[str]] = OrderedDict(
    [
        ("Development", ["test", "lint", "typecheck", "check"]),
        ("Environment", ["welcome", "tools", "env", "clean", "reset"]),
        ("Hints", ["uv", "dagster", "direnv"]),
        ("Infrastructure", ["k8s"]),
    ]
)


class GroupedCommands(typer.core.TyperGroup):
    """Click Group that formats commands under named section headers."""

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        commands = {name: self.get_command(ctx, name) for name in self.list_commands(ctx)}
        limit = formatter.width - 6

        for section, names in COMMAND_GROUPS.items():
            rows = []
            for name in names:
                cmd = commands.pop(name, None)
                if cmd is None or cmd.hidden:
                    continue
                rows.append((name, cmd.get_short_help_str(limit=limit)))
            if rows:
                with formatter.section(section):
                    formatter.write_dl(rows)

        # Any remaining commands not listed in COMMAND_GROUPS
        rows = [
            (n, c.get_short_help_str(limit=limit))
            for n, c in commands.items()
            if c and not c.hidden
        ]
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"dap {version('arca-flow-cli')}")
        raise typer.Exit()


app = typer.Typer(
    name="dap",
    help="Developer tools for the Data Archive Pipeline (DAP) Orchestrator.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    cls=GroupedCommands,
)


@app.callback(invoke_without_command=True)
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Developer tools for the Data Archive Pipeline (DAP) Orchestrator."""


# -- Development -----------------------------------------------------------
app.command()(dev.test)
app.command()(dev.lint)
app.command()(dev.typecheck)
app.command()(dev.check)

# -- Environment -----------------------------------------------------------
app.command()(env.welcome)
app.command()(env.tools)
app.command()(env.env)
app.command()(env.clean)
app.command()(env.reset)

# -- Hints -----------------------------------------------------------------
app.command()(hints.uv)
app.command()(hints.dagster)
app.command()(hints.direnv)

# -- Infrastructure --------------------------------------------------------
app.add_typer(k8s.app, name="k8s", help="Kubernetes operations.")


def main() -> None:
    app()
