# Contributing to the arca-flow CLI

## Architecture

```
cli/arca_flow_cli/
  app.py              Entry point — registers all commands on a single Typer app
  theme.py            Rich console, ETH Zurich brand colours, symbols
  commands/
    dev.py            test, lint, typecheck, check
    env.py            welcome, tools, clean, reset
    hints.py          uv, dagster, direnv (usage guidance)
    k8s.py            Kubernetes subcommand group (up, down, restart, status, logs, shell)
  utils/
    run.py            Subprocess helpers (run_passthrough, run_capture, run_interactive)

cli/tests/
  test_commands.py    Help tests + behavioral tests for dev/env commands
  test_k8s.py         Unit + behavioral tests for k8s commands
```

### How commands are registered

All commands are registered in `app.py`:

```python
# Top-level commands
app.command()(dev.test)
app.command()(env.welcome)

# Subcommand groups
app.add_typer(k8s.app, name="k8s", help="Kubernetes operations.")

# Hint commands
app.command()(hints.direnv)
```

## Adding a new command

1. **Choose the right module:**
   - `dev.py` for development workflow commands (test, lint, build)
   - `env.py` for environment management (tools, clean, versions)
   - `hints.py` for "how to use X" guidance
   - `k8s.py` for Kubernetes operations (add to the existing `app` Typer)

2. **Write the function** following TUI conventions (see below).

3. **Register it in `app.py`:**
   ```python
   app.command()(module.my_command)
   ```

4. **Add tests** in `cli/tests/`:
   - At minimum: a help test (`runner.invoke(app, ["my-command", "--help"])`)
   - Ideally: a behavioral test with mocked `run_*` calls

5. **Verify:**
   ```bash
   uv run ruff check cli/arca_flow_cli/
   uv run pytest cli/tests/ -v
   uv run arca-flow my-command --help
   ```

## TUI conventions

All CLI output follows these rules. See [`.claude/skills/tui-design.md`](../.claude/skills/tui-design.md) for the complete reference.

### 1. Use the centralized console

```python
from arca_flow_cli.theme import console, OK, FAIL, ARROW
```

Never create a new `Console` instance. The project console writes to stderr, supports `NO_COLOR`, and uses the ETH brand theme.

### 2. Use semantic colours

```python
console.print("[title]Section Header[/]")
console.print("[error]Something failed[/]")
console.print("[hint]Run 'arca-flow --help' for all commands[/]")
```

Available roles: `success`, `error`, `warning`, `info`, `title`, `hint`, `command`.

### 3. Use theme symbols

```python
console.print(f"  {OK} Tests passed")      # checkmark
console.print(f"  {FAIL} Build failed")     # cross
console.print(f"  {WARN} Deprecated")       # exclamation
console.print(f"  {ARROW} Running...")       # right arrow
console.print(f"  {DASH} Not found")        # em dash
```

### 4. Two-space indent

Every output line starts with two spaces:

```python
console.print(f"  {ARROW} Building...")
console.print(f"  {OK} Build complete")
```

### 5. Spinners for blocking operations

```python
from rich.status import Status

with Status("  Checking connectivity...", console=console):
    code, _ = run_capture(["kubectl", "cluster-info"], timeout=10)
```

### 6. Fail-fast with context

```python
if code != 0:
    console.print(f"  {FAIL} Docker build failed")
    raise typer.Exit(1)
```

### 7. Confirm destructive operations

```python
def clean(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    if not yes:
        typer.confirm("Remove .venv and all caches?", abort=True)
```

## Testing patterns

Tests use `typer.testing.CliRunner` and mock subprocess calls at the import site:

```python
from unittest.mock import patch
from typer.testing import CliRunner
from arca_flow_cli.app import app

runner = CliRunner()

def test_my_command_help():
    result = runner.invoke(app, ["my-command", "--help"])
    assert result.exit_code == 0

@patch("arca_flow_cli.commands.dev.run_passthrough", return_value=0)
def test_my_command(mock_run):
    result = runner.invoke(app, ["my-command"])
    assert result.exit_code == 0
```

**Important:** Patch at the import site (`arca_flow_cli.commands.dev.run_passthrough`), not the definition site (`arca_flow_cli.utils.run.run_passthrough`).

## ETH Zurich brand colours

The CLI uses official ETH Zurich brand colours and their 80% shades for dark terminal readability. See `theme.py` for the full palette.

Override detection with `ARCA_FLOW_THEME=light` or `ARCA_FLOW_THEME=dark`.
