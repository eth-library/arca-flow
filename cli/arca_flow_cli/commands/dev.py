"""Development commands: test, lint, typecheck, check."""

from enum import StrEnum

import typer

from arca_flow_cli.theme import ARROW, FAIL, OK, console
from arca_flow_cli.utils.run import run_passthrough

# Target directories per scope
CORE_TARGETS = ["arca"]
CLI_TARGETS = ["cli/arca_flow_cli"]
ALL_TARGETS = [*CORE_TARGETS, *CLI_TARGETS]

CORE_TEST_TARGETS = ["arca/flow/tests"]
CLI_TEST_TARGETS = ["cli/tests"]
ALL_TEST_TARGETS = [*CORE_TEST_TARGETS, *CLI_TEST_TARGETS]

_TEST_ARGS = typer.Argument(default=None, help="Extra arguments passed to pytest.")


class Scope(StrEnum):
    core = "core"
    cli = "cli"
    all = "all"


def _targets(scope: Scope) -> list[str]:
    if scope == Scope.cli:
        return CLI_TARGETS
    if scope == Scope.all:
        return ALL_TARGETS
    return CORE_TARGETS


def _test_targets(scope: Scope) -> list[str]:
    if scope == Scope.cli:
        return CLI_TEST_TARGETS
    if scope == Scope.all:
        return ALL_TEST_TARGETS
    return CORE_TEST_TARGETS


def _scope_label(scope: Scope) -> str:
    if scope == Scope.cli:
        return "CLI"
    if scope == Scope.all:
        return "core + CLI"
    return "core"


_SCOPE_OPTION = typer.Option(Scope.core, help="Scope: core (default), --cli, or --all.")


def test(
    ctx: typer.Context,
    args: list[str] | None = _TEST_ARGS,
    scope: Scope = _SCOPE_OPTION,
) -> None:
    """Run tests with pytest."""
    targets = _test_targets(scope)
    cmd = ["pytest", *targets, *(args or [])]
    console.print(f"  {ARROW} Running tests ({_scope_label(scope)})")
    console.print(f"  [hint]  pytest {' '.join(targets)}[/]")
    console.print()
    code = run_passthrough(cmd)
    if code != 0:
        raise typer.Exit(code)
    console.print(f"  {OK} Tests passed")
    console.print()


def lint(
    fix: bool = typer.Option(False, help="Auto-fix issues."),
    scope: Scope = _SCOPE_OPTION,
) -> None:
    """Check code style and formatting with ruff."""
    targets = _targets(scope)
    if fix:
        console.print(f"  {ARROW} Fixing lint issues ({_scope_label(scope)})")
        console.print(f"  [hint]  ruff check --fix {' '.join(targets)}[/]")
        console.print()
        code = run_passthrough(["ruff", "check", "--fix", *targets])
        if code != 0:
            raise typer.Exit(code)
        code = run_passthrough(["ruff", "format", *targets])
        if code != 0:
            raise typer.Exit(code)
        console.print(f"  {OK} Code fixed and formatted")
        console.print()
    else:
        console.print(f"  {ARROW} Checking code style ({_scope_label(scope)})")
        console.print(f"  [hint]  ruff check {' '.join(targets)}[/]")
        console.print()
        code = run_passthrough(["ruff", "check", *targets])
        if code != 0:
            console.print(f"  {FAIL} Lint check failed")
            raise typer.Exit(code)
        code = run_passthrough(["ruff", "format", "--check", *targets])
        if code != 0:
            console.print(f"  {FAIL} Format check failed")
            raise typer.Exit(code)
        console.print(f"  {OK} All lint checks passed")
        console.print()


def typecheck(
    scope: Scope = _SCOPE_OPTION,
) -> None:
    """Run type checking with mypy."""
    targets = _targets(scope)
    console.print(f"  {ARROW} Type checking ({_scope_label(scope)})")
    console.print(f"  [hint]  mypy {' '.join(targets)}[/]")
    console.print()
    code = run_passthrough(["mypy", *targets])
    if code != 0:
        console.print(f"  {FAIL} Typecheck failed")
        raise typer.Exit(code)
    console.print(f"  {OK} Typecheck passed")
    console.print()


def _run_step(label: str, cmd: list[str]) -> bool:
    """Run a step with streaming output. Returns True on success."""
    console.print(f"  {ARROW} {label}")
    console.print(f"  [hint]  {' '.join(cmd)}[/]")
    console.print()
    code = run_passthrough(cmd)
    console.print()
    if code == 0:
        console.print(f"  {OK} {label} — passed")
        return True
    else:
        console.print(f"  {FAIL} {label} — failed")
        return False


def check(
    scope: Scope = _SCOPE_OPTION,
) -> None:
    """Run all quality checks (ruff, mypy, pytest)."""
    targets = _targets(scope)
    test_targets = _test_targets(scope)
    label = _scope_label(scope)

    console.print()

    # Lint
    if not _run_step(f"Lint ({label}) — checking code style", ["ruff", "check", *targets]):
        console.print("\n  Stopped — typecheck and test skipped")
        raise typer.Exit(1)
    if not _run_step(
        f"Lint ({label}) — checking formatting", ["ruff", "format", "--check", *targets]
    ):
        console.print("\n  Stopped — typecheck and test skipped")
        raise typer.Exit(1)

    # Typecheck
    if not _run_step(f"Typecheck ({label}) — running mypy", ["mypy", *targets]):
        console.print("\n  Stopped — test skipped")
        raise typer.Exit(1)

    # Test
    if not _run_step(f"Test ({label}) — running pytest", ["pytest", *test_targets]):
        raise typer.Exit(1)

    console.print(f"\n  {OK} All checks passed ({label})")
    console.print()
