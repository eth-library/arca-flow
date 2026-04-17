# arca-flow CLI

Developer CLI for **arca-flow** — the orchestration engine of ETH Zurich's Digital Preservation Pipeline.

The `arca-flow` CLI wraps common development tasks into short, memorable commands. It doesn't replace the underlying tools — it provides ergonomic shortcuts and a consistent interface.

A short alias `af` is installed alongside for daily use — `af test`, `af check`, etc. are equivalent to `arca-flow test`, `arca-flow check`.

## The dev toolchain stack

The project uses a layered toolchain where each layer builds on the one below:

```
nix flakes        Reproducible packages — pins exact versions of Python, uv, kubectl, etc.
  └─ direnv       Auto-loading shell env — activates when you cd into the project
      └─ nix-direnv   Cached flake evaluation — avoids re-evaluating the flake on every shell
          └─ uv       Fast Python deps — installs packages from the lockfile in milliseconds
              └─ arca-flow   Ergonomic commands — wraps pytest, ruff, mypy, helm, kubectl
```

**Why each layer exists:**

- **Nix flakes** (`flake.nix`): ensures every developer has identical tool versions. No "works on my machine".
- **direnv** (`.envrc`): automatically loads the nix environment when you enter the project directory. No manual `nix develop`.
- **nix-direnv**: caches the nix evaluation so shell startup stays fast. Without it, entering the directory would re-evaluate the flake every time.
- **uv** (`pyproject.toml`, `uv.lock`): manages Python dependencies. Fast, deterministic, lockfile-based.
- **arca-flow CLI** (`cli/`): the commands documented below. Wraps quality checks, environment management, and Kubernetes deployment.

## Installation

Handled automatically by direnv and nix:

```bash
git clone <repo-url> && cd arca-flow
direnv allow  # one-time approval
# Everything is now available: arca-flow, python, uv, dagster, kubectl, helm
```

## Commands

### Development

| Command | Description |
|---------|-------------|
| `arca-flow test [--scope core\|cli\|all]` | Run tests with pytest |
| `arca-flow lint [--fix] [--scope ...]` | Check code style and formatting with ruff |
| `arca-flow typecheck [--scope ...]` | Run type checking with mypy |
| `arca-flow check [--scope ...]` | Run all quality checks (ruff, mypy, pytest) |

The `--scope` flag controls which code is checked:
- `core` (default): `arca_flow`, `arca_flow_tests`
- `cli`: `cli/arca_flow_cli`, `cli/tests`
- `all`: both core and CLI

### Environment

| Command | Description |
|---------|-------------|
| `arca-flow welcome` | Show welcome banner and environment info |
| `arca-flow tools [--all]` | Show installed tool versions and paths |
| `arca-flow clean [--yes]` | Remove `.venv` and caches |
| `arca-flow reset [--yes]` | Clean and reinstall dependencies |

`arca-flow tools` shows Python toolchain by default. Pass `--all` to include nix, direnv, kubectl, and helm.

`arca-flow clean` and `arca-flow reset` prompt for confirmation. Pass `--yes` / `-y` to skip (for CI/scripts).

### Kubernetes

| Command | Description |
|---------|-------------|
| `arca-flow k8s up` | Build and deploy to local Kubernetes |
| `arca-flow k8s down [--yes]` | Tear down deployment |
| `arca-flow k8s restart` | Rebuild image and rollout restart |
| `arca-flow k8s status` | Show pods and services |
| `arca-flow k8s logs` | Stream user code pod logs |
| `arca-flow k8s shell` | Interactive shell in user code pod |

Requires Docker Desktop with Kubernetes enabled.

### Hint commands

These commands show how to use tools that are available directly in your shell:

| Command | Description |
|---------|-------------|
| `arca-flow uv` | Common uv commands (sync, lock, add, run) |
| `arca-flow dagster` | Common dagster/dg commands |
| `arca-flow direnv` | Common direnv commands (allow, reload, status) |

### Global flags

| Flag | Description |
|------|-------------|
| `--version` / `-V` | Show CLI version |
| `--help` | Show help |

## Environment variables

| Variable | Effect |
|----------|--------|
| `ARCA_FLOW_THEME=light\|dark` | Override terminal background detection for colours |
| `ARCA_FLOW_QUIET=1` | Suppress Quick Start section in `arca-flow welcome` |
| `NO_COLOR=1` | Disable all colour output (also respected in CI) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for CLI architecture, how to add commands, and testing patterns.
