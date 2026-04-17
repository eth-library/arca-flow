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
- [Local Development](#local-development)
- [Usage](#usage)
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

## Quick Start

### With Nix (Recommended)

Clone the repository and enter the development environment:

```bash
git clone https://github.com/eth-library/arca-flow.git
cd arca-flow
direnv allow
```

`direnv allow` activates the Nix devshell, installs Python dependencies, and prints the welcome banner. If not using [direnv](https://direnv.net/), activate the environment manually:

```bash
nix develop
```

Start the Dagster development server:

```bash
just run
```

Open http://localhost:3000 in your browser.

### Without Nix

Ensure you have the following installed:

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

Set up the project:

```bash
git clone https://github.com/eth-library/arca-flow.git
cd arca-flow
uv sync --group dev
```

Start the Dagster development server:

```bash
uv run dg dev
```

Open http://localhost:3000 in your browser.

## Prerequisites

| Tool | Purpose | Installation |
|------|---------|--------------|
| [Nix](https://nixos.org/download.html) | Development environment (optional but recommended) | [Install guide](https://nixos.org/download.html) |
| [direnv](https://direnv.net/) | Automatic environment loading | [Install guide](https://direnv.net/docs/installation.html) |
| [nix-direnv](https://github.com/nix-community/nix-direnv) | Fast Nix + direnv integration | [Install guide](https://github.com/nix-community/nix-direnv#installation) |
| Python 3.14+ | Runtime | [python.org](https://www.python.org/downloads/) |
| [uv](https://github.com/astral-sh/uv) | Fast Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [just](https://github.com/casey/just) | Command runner | Included in Nix devshell; see [install guide](https://github.com/casey/just#installation) |

## Dev Toolchain

The project uses a layered toolchain where each layer builds on the one below.

```
nix flakes        Reproducible packages — pins exact versions of Python, uv, just, etc.
  └─ direnv       Auto-loading shell env — activates when you cd into the project
      └─ nix-direnv   Cached flake evaluation — avoids re-evaluating the flake on every shell
          └─ uv       Fast Python deps — installs packages from the lockfile in milliseconds
              └─ just     Developer commands — wraps pytest, ruff, mypy via a justfile
```

**Why each layer exists:**

- **Nix flakes** (`flake.nix`): ensures every developer has identical tool versions. No "works on my machine".
- **direnv** (`.envrc`): automatically loads the nix environment when you enter the project directory. No manual `nix develop`.
- **nix-direnv**: caches the nix evaluation so shell startup stays fast. Without it, entering the directory would re-evaluate the flake every time.
- **uv** (`pyproject.toml`, `uv.lock`): manages Python dependencies. Fast, deterministic, lockfile-based.
- **just** (`justfile`): the commands documented below. Wraps quality checks and the dev server.

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

## Local Development

Once the environment is set up — `direnv allow` (recommended, Nix + direnv), `nix develop && uv sync --group dev` (Nix without direnv), or `uv sync --group dev` (no Nix) — all dev commands go through `just`. Without Nix, install `just` separately to use the recipes below, or run the underlying `uv run <tool>` commands directly:

```bash
just          # list all available commands
just check    # run lint + type check + tests (all quality gates)
just test     # run pytest
just lint     # ruff check + format check (read-only)
just format   # ruff check --fix + ruff format (write)
just type     # mypy
just run      # start the Dagster dev server via dg
just welcome  # re-display the welcome banner
```

Pass extra arguments to `just test` with a space: `just test -k foo` runs only tests matching `foo`.

For Kubernetes operations (local k3d bringup, multi-service e2e tests), see the umbrella [arca](https://github.com/eth-library/arca) repository.

## Usage

### Manual Pipeline Runs

To run the pipeline manually via the Dagster UI launchpad, provide a run configuration:

```yaml
ops:
  sip_asset:
    config:
      file_paths:
        - /path/to/your/mets.xml
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DAGSTER_HOME` | Dagster instance directory | Project root (set by `.envrc`) |
| `DAGSTER_TEST_DATA_PATH` | Directory containing METS XML files for the sensor to monitor | `arca/flow/tests/test_data` |
| `CI` | When set (e.g. by GitHub Actions), `just welcome` exits silently | unset |
| `NO_COLOR` | Set to any non-empty value to disable all colour output | unset |

Copy `.env.example` to `.env` and modify as needed.

### Configuration Files

| File | Purpose |
|------|---------|
| `flake.nix` | Nix development environment |
| `justfile` | Developer command runner |
| `pyproject.toml` | Python project metadata and dependencies |
| `dagster.yaml` | Dagster instance configuration |
| `config.yaml` | Example run configuration for manual pipeline execution |

### Development Shells

The Nix flake exposes two devShells:

- `default` — Python + uv + just + kubectl + helm (full stack)
- `minimal` — Python + uv + just (pipeline and tests only)

Activated via `direnv allow` (uses `default`) or `nix develop .#minimal`.

## Project Structure

```
justfile                     # Developer commands (just check, just test, just run, …)
banner.txt                   # Welcome banner rendered by just welcome

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
```

## Dependency Management

Dependencies are managed with [uv](https://github.com/astral-sh/uv):

Install or update dependencies (including dev group):

```bash
uv sync --group dev
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

Ensure no other process is using port 3000:

```bash
lsof -i :3000
```

### Sensor not detecting files

Check the `DAGSTER_TEST_DATA_PATH` environment variable points to a directory containing `.xml` files. The sensor only processes files with the `.xml` extension.

### Test failures

Ensure dependencies are installed:

```bash
uv sync --group dev
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
- [just](https://github.com/casey/just) - Command runner
- [Nix](https://nixos.org/) - Reproducible development environments
- [direnv](https://direnv.net/) - Automatic environment loading
- [Ruff](https://docs.astral.sh/ruff/) - Python linter and formatter
