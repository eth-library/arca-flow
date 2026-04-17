# arca-flow

**ETH Library Zurich · Data Archive · Orchestrator Engine**

> [!TIP]
> This repository is part of [Arca](https://github.com/eth-library/arca),
> ETH Library's digital preservation pipeline. Visit the umbrella
> repository to understand the full system architecture and how to spin up
> the entire stack locally.

A [Dagster](https://dagster.io/)-powered orchestrator that ingests digital assets and assembles OAIS-compliant Submission Information Packages (SIPs), parsing METS/PREMIS metadata along the way.

> [!NOTE]
> This project is in **alpha** and actively evolving. APIs and behaviors may change. Provided as-is, with no guarantees on stability.

## Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Dev Toolchain](#dev-toolchain)
- [Architecture](#architecture)
- [Usage](#usage)
- [Commands Reference](#commands-reference)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Dependency Management](#dependency-management)
- [Troubleshooting](#troubleshooting)
- [Domain Terms](#domain-terms)
- [License](#license)
- [Further Reading](#further-reading)

## Features

- Parses METS XML files into validated Pydantic models following OAIS standards
- Extracts Dublin Core descriptive metadata and PREMIS preservation metadata
- Validates file fixity information (MD5, SHA-1, SHA-256, SHA-512 checksums)
- Automated file monitoring via Dagster sensors
- Hot-reload development with instant feedback
- Kubernetes-ready with Helm chart configuration

## Quick Start

### With Nix (Recommended)

Clone the repository and enter the development environment:

```bash
git clone https://github.com/eth-library/arca-flow.git
cd arca-flow
direnv allow
```

If not using [direnv](https://direnv.net/), activate the environment manually:

```bash
nix develop
```

Start the Dagster development server:

```bash
dagster dev
```

Open http://localhost:3000 in your browser.

### Without Nix

Ensure you have the following installed:

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

Set up the project:

```bash
git clone https://github.com/eth-library/arca-flow.git
cd arca-flow
uv venv --python python3.12
source .venv/bin/activate
uv sync
```

The `arca-flow` command becomes available automatically because the CLI is a UV workspace member.

Start the Dagster development server:

```bash
dagster dev
```

Open http://localhost:3000 in your browser.

## Prerequisites

| Tool | Purpose | Installation |
|------|---------|--------------|
| [Nix](https://nixos.org/download.html) | Development environment (optional but recommended) | [Install guide](https://nixos.org/download.html) |
| [direnv](https://direnv.net/) | Automatic environment loading | [Install guide](https://direnv.net/docs/installation.html) |
| [nix-direnv](https://github.com/nix-community/nix-direnv) | Fast Nix + direnv integration | [Install guide](https://github.com/nix-community/nix-direnv#installation) |
| Python 3.12+ | Runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://github.com/astral-sh/uv) | Fast Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

For Kubernetes development, you'll also need:

- Docker Desktop with Kubernetes enabled
- kubectl
- helm

## Dev Toolchain

The project uses a layered toolchain where each layer builds on the one below. See [cli/README.md](cli/README.md) for the full CLI reference.

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

## Architecture

The pipeline processes XML files through a sequence of Dagster [assets](https://docs.dagster.io/concepts/assets/software-defined-assets), each extracting a specific layer of the preservation package hierarchy:

### Assets

| Asset | Input | Output | Description                                                    |
|-------|-------|--------|----------------------------------------------------------------|
| `sip_asset` | XML file paths | `SIPModel` | Parses METS XML into a structured SIP model                    |
| `intellectual_entities` | `SIPModel` | `list[IEModel]` | Extracts intellectual entity metadata with Dublin Core         |
| `representations` | `list[IEModel]` | `list[RepresentationModel]` | Collects file representations (preservation, access, original) |
| `files` | `list[RepresentationModel]` | `list[FileModel]` | Extracts file metadata including MIME types and paths          |
| `fixities` | `list[FileModel]` | `list[FixityModel]` | Extracts and validates file checksums                          |

### Sensor

The `xml_file_sensor` monitors a configured directory for new XML files and automatically triggers the pipeline. By default, it watches `arca/flow/tests/test_data/` every 30 seconds.

## Usage

### Local Development

Start the Dagster UI with hot-reload:

```bash
dagster dev
```

Run the test suite:

```bash
arca-flow test
```

### Manual Pipeline Runs

To run the pipeline manually via the Dagster UI launchpad, provide a run configuration:

```yaml
ops:
  sip_asset:
    config:
      file_paths:
        - /path/to/your/mets.xml
```

### Kubernetes Deployment

Requires Docker Desktop with Kubernetes enabled (Settings > Kubernetes > Enable).

Deploy to local Kubernetes:

```bash
arca-flow k8s up
```

The Dagster UI will be available at http://localhost:8080.

Rebuild and restart after code changes:

```bash
arca-flow k8s restart
```

Tear down the deployment:

```bash
arca-flow k8s down
```

## Commands Reference

Run `arca-flow --help` to see all available commands. A short alias `af` is installed alongside for daily use — `af test`, `af check`, etc. are equivalent to `arca-flow test`, `arca-flow check`.

### Development

| Command | Description |
|---------|-------------|
| `arca-flow test [--scope core\|cli\|all]` | Run tests with pytest |
| `arca-flow lint [--fix] [--scope ...]` | Check code style and formatting with ruff |
| `arca-flow typecheck [--scope ...]` | Run type checking with mypy |
| `arca-flow check [--scope ...]` | Run all quality checks (ruff, mypy, pytest) |

The `--scope` flag controls which code is checked:
- `core` (default): `arca`
- `cli`: `cli/arca_flow_cli`, `cli/tests`
- `all`: both core and CLI

### Environment

| Command | Description |
|---------|-------------|
| `arca-flow welcome` | Show welcome banner and environment info |
| `arca-flow tools [--all]` | Show installed tool versions and paths |
| `arca-flow env` | Show environment paths and status |
| `arca-flow clean [--yes]` | Remove `.venv` and caches |
| `arca-flow reset [--yes]` | Clean and reinstall dependencies |

`arca-flow tools` shows the Python toolchain by default. Pass `--all` to include nix, direnv, kubectl, and helm.

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

### Hint Commands

These commands show how to use tools that are available directly in your shell:

| Command | Description |
|---------|-------------|
| `arca-flow uv` | Common uv commands (sync, lock, add, run) |
| `arca-flow dagster` | Common dagster/dg commands |
| `arca-flow direnv` | Common direnv commands (allow, reload, status) |

### Global Flags

| Flag | Description |
|------|-------------|
| `--version` / `-V` | Show CLI version |
| `--help` | Show help |

### CLI Development

For working on the arca-flow CLI itself (Python, Typer + Rich), see [cli/CONTRIBUTING.md](cli/CONTRIBUTING.md).

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DAGSTER_HOME` | Dagster instance directory | Project root (set by `.envrc`) |
| `DAGSTER_TEST_DATA_PATH` | Directory containing METS XML files for the sensor to monitor | `arca/flow/tests/test_data` |
| `ARCA_FLOW_THEME` | Override terminal background detection for colours (`light` or `dark`) | unset |
| `ARCA_FLOW_QUIET` | Set to `1` to suppress Quick Start section in `arca-flow welcome` | unset |
| `CI` | When set (e.g. by GitHub Actions), `arca-flow welcome` also omits the startup banner and Quick Start | unset |
| `NO_COLOR` | Set to `1` to disable all colour output (also respected in CI) | unset |

Copy `.env.example` to `.env` and modify as needed.

### Configuration Files

| File | Purpose |
|------|---------|
| `flake.nix` | Nix development environment with multiple shells (see below) |
| `cli/` | Python CLI source code (see [cli/CONTRIBUTING.md](cli/CONTRIBUTING.md)) |
| `pyproject.toml` | Python project metadata and dependencies |
| `dagster.yaml` | Dagster instance configuration |
| `config.yaml` | Example run configuration for manual pipeline execution |
| `helm/values.yaml` | Base Helm values for Kubernetes deployment |
| `helm/values-local.yaml` | Local Kubernetes overrides |
| `helm/pvc.yaml` | Persistent volume claim for Dagster storage |

### Development Shells

The Nix flake provides a single development shell activated via `direnv allow` or `nix develop`. It includes Python, uv, kubectl, and helm.

## Project Structure

```
cli/                         # arca-flow CLI (Python) — see cli/CONTRIBUTING.md
├── arca_flow_cli/
│   ├── app.py               # Entry point — registers all commands
│   ├── theme.py             # Rich console, ETH brand colors, symbols
│   ├── commands/            # Command modules (dev, env, hints, k8s)
│   └── utils/               # Subprocess helpers
└── tests/                   # CLI tests

arca/flow/                   # Main package (Python)
├── definitions.py           # Dagster entry point (Definitions)
├── assets.py                # Pipeline assets
├── sensors.py               # File monitoring sensor and job definition
├── mets_parser.py           # METS XML parsing logic
├── pydantic_models.py       # OAIS-compliant data models
├── utils.py                 # Helper functions for metadata collection
└── tests/
    ├── test_data/           # Sample METS XML files
    │   └── synthetic_sip.xml
    ├── test_assets.py       # Asset tests
    └── conftest.py          # Pytest fixtures

helm/                        # Kubernetes configuration
├── values.yaml              # Base Helm values
├── values-local.yaml        # Local development overrides
└── pvc.yaml                 # Persistent volume claim
```

## Dependency Management

Dependencies are managed with [uv](https://github.com/astral-sh/uv):

Install or update dependencies:

```bash
uv sync
```

Update the lock file:

```bash
uv lock
```

Add a new dependency:

```bash
uv add <package>
```

## Troubleshooting

### Dagster UI not loading

Ensure no other process is using port 3000 (local) or 8080 (Kubernetes):

```bash
lsof -i :3000
```

### Kubernetes deployment fails

Verify Kubernetes is running:

```bash
kubectl cluster-info
```

Ensure Docker Desktop Kubernetes is enabled in Settings > Kubernetes > Enable Kubernetes.

### Sensor not detecting files

Check the `DAGSTER_TEST_DATA_PATH` environment variable points to a directory containing `.xml` files. The sensor only processes files with the `.xml` extension.

### Test failures

Ensure dependencies are installed:

```bash
uv sync
```

## Domain Terms

- **METS** (Metadata Encoding and Transmission Standard): XML schema for encoding metadata about digital objects
- **OAIS** (Open Archival Information System): ISO reference model for digital preservation systems
- **SIP** (Submission Information Package): A package submitted to an archive for ingest
- **IE** (Intellectual Entity): A distinct unit of information to be preserved (e.g., a document, dataset)

## License

[Apache License 2.0](LICENSE) - (c) 2026 ETH Zurich

## Further Reading

### Core Technologies

- [Dagster Documentation](https://docs.dagster.io/) - Data orchestration platform
  - [Assets](https://docs.dagster.io/concepts/assets/software-defined-assets)
  - [Sensors](https://docs.dagster.io/concepts/partitions-schedules-sensors/sensors)
  - [Definitions](https://docs.dagster.io/concepts/code-locations)
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation library

### Digital Preservation Standards

- [METS (Metadata Encoding and Transmission Standard)](https://www.loc.gov/standards/mets/)
- [OAIS Reference Model (ISO 14721)](https://www.iso.org/standard/57284.html)
- [Dublin Core Metadata](https://www.dublincore.org/specifications/dublin-core/)
- [PREMIS (Preservation Metadata)](https://www.loc.gov/standards/premis/)

### Development Tools

- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [Typer](https://typer.tiangolo.com/) - Python CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting library
- [Nix](https://nixos.org/) - Reproducible development environments
- [direnv](https://direnv.net/) - Automatic environment loading
- [Ruff](https://docs.astral.sh/ruff/) - Python linter and formatter

### Kubernetes

- [Helm](https://helm.sh/docs/) - Kubernetes package manager
- [Dagster Helm Chart](https://docs.dagster.io/deployment/guides/kubernetes/deploying-with-helm)
