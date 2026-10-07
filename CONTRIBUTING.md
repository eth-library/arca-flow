# Contributing

This guide covers development setup, checks, contribution conventions, and GitHub security and quality configuration. For running arca-flow and the wider system context, see the [README](README.md).

## Table of contents

- [Development toolchain](#development-toolchain)
- [Development environment](#development-environment)
- [Command reference](#command-reference)
- [Code layout](#code-layout)
- [Testing](#testing)
- [Change workflow](#change-workflow)
- [Commit rules](#commit-rules)
- [CI and image publishing](#ci-and-image-publishing)
- [Security and code quality](#security-and-code-quality)
- [Dependency updates](#dependency-updates)
- [References](#references)

## Development toolchain

arca-flow is the Dagster orchestrator in ETH Library's digital preservation pipeline. Python code handles ingestion and metadata processing, with Pydantic models providing validation. The application is evolving, so this guide focuses on the development workflow rather than the details of individual pipeline stages.

[flake.lock](flake.lock) pins the Nix inputs that supply the interpreter and command-line tools; [uv.lock](uv.lock) pins Python dependencies. The [justfile](justfile) defines the commands used locally and in CI, so contributors can run the same checks before submitting changes.

| Tool | Role | How this repository uses it |
|---|---|---|
| **Python** [\[1\]](#ref-1) | Runtime | Application and test code under `arca/flow/`; the supported range is declared in `pyproject.toml` |
| **Dagster** [\[2\]](#ref-2) | Orchestration | Assets, ingestion job, sensor, and development server |
| **Pydantic** [\[3\]](#ref-3) | Data validation | Models for SIP metadata and its nested entities |
| **uv** [\[4\]](#ref-4) | Dependency management | Resolves `pyproject.toml`, maintains `uv.lock`, and runs tools in the project environment |
| **pytest** [\[5\]](#ref-5) | Testing | Materializes the asset pipeline against synthetic METS fixtures |
| **Ruff** [\[6\]](#ref-6) | Linting and formatting | Checks Python code style and imports; formats code |
| **mypy** [\[7\]](#ref-7) | Type checking | Checks `arca/` using the configuration in `pyproject.toml` |
| **pre-commit** [\[8\]](#ref-8) | Commit checks | Runs the hooks configured in `.pre-commit-config.yaml` |
| **Nix flakes** [\[9\]](#ref-9) | Environment management | Supplies Python, uv, and just through `flake.nix` |
| **direnv** [\[10\]](#ref-10) and **nix-direnv** [\[11\]](#ref-11) | Shell activation | Loads and caches the Nix environment through `.envrc` |
| **just** [\[12\]](#ref-12) | Task automation | Provides the commands listed below |
| **GitHub Actions** [\[13\]](#ref-13) | CI and security scanning | Runs checks, publishes images, and executes CodeQL analysis |

## Development environment

### With Nix (recommended)

The Nix shell supplies Python, uv, and just from the pinned environment used by CI. This is the recommended path because it reduces differences between local tooling and the checks on GitHub.

Install Nix with flake support [\[9\]](#ref-9). Clone the repository and enter it:

```bash
git clone https://github.com/eth-library/arca-flow.git
cd arca-flow
```

With direnv [\[10\]](#ref-10) installed, allow the repository's environment:

```bash
direnv allow
```

[.envrc](.envrc) loads the Nix shell, synchronizes development dependencies, and sets the local Dagster and virtual-environment paths. With nix-direnv, later entries reuse the cached environment.

Without direnv, enter the shell and synchronize dependencies explicitly:

```bash
nix develop
uv sync --locked --group dev
```

### Without Nix

Install a Python interpreter satisfying `requires-python` in [pyproject.toml](pyproject.toml), uv [\[4\]](#ref-4), and just [\[12\]](#ref-12). Then run:

```bash
uv sync --locked --group dev
```

`--locked` checks that the project metadata and lockfile agree rather than silently updating the lockfile during setup. Re-run the synchronization command after pulling dependency changes.

### Verify the setup

```bash
just check
```

This runs linting, formatting checks, type checking, and tests. Use `just run` to start the Dagster development server when you need to inspect the application interactively.

Install the optional local commit hooks with pre-commit [\[8\]](#ref-8) once per checkout:

```bash
uv run pre-commit install
```

The hooks in [.pre-commit-config.yaml](.pre-commit-config.yaml) check whitespace, file endings, YAML, TOML, large files, and Python formatting. Some rewrite files, so review and stage their changes before retrying a commit. They do not replace `just check`, which also runs type checking and tests.

## Command reference

The [justfile](justfile) is the source of truth. Run bare `just` to list the available recipes.

| Command | What it does |
|---|---|
| `just check` | Runs `lint`, `type`, and `test`, in that order |
| `just lint` | Runs Ruff lint and format checks on `arca/` without rewriting files |
| `just format` | Applies Ruff fixes and formatting to `arca/` |
| `just type` | Runs mypy on `arca/` |
| `just test` | Runs pytest against `arca/flow/tests/` |
| `just test -k single_file` | Runs tests whose names match `single_file` |
| `just run` | Starts the Dagster development server through `dg dev` |
| `just welcome` | Prints the tool and environment summary |

Extra arguments after `just test` are passed to pytest. Without just, the underlying commands are available in the recipes, for example `uv run mypy arca`.

## Code layout

Application code lives under [arca/flow](arca/flow), with tests under [arca/flow/tests](arca/flow/tests). Dagster coordinates processing; Python code handles parsing and validation.

## Testing

Tests use pytest [\[5\]](#ref-5) and live alongside the application under [arca/flow/tests](arca/flow/tests). The suite exercises the pipeline with synthetic metadata, and its fixtures provide an isolated Dagster home for each test.

Add focused tests for the behavior being changed, including relevant invalid inputs and failure cases. Keep fixtures small and synthetic so their purpose is easy to review. Run `just check` before submitting code changes; for documentation-only changes, check links, commands, and formatting.

## Change workflow

### Issues and pull requests

Use an issue to describe the problem and expected outcome when a change needs discussion. For a bug, include a reproducible example and relevant error output. Small, self-contained changes can be explained directly in a pull request.

Keep pull requests focused on one concern and target `main`. Explain the resulting behavior, link the related issue when there is one, and record how the change was tested. Include relevant tests and update documentation when behavior or configuration changes.

### Branches and review

Use short-lived branches with a descriptive type prefix, such as `feat/`, `fix/`, or `chore/`, and agree on the name with the maintainer. Direct work on `main` requires the maintainer's instruction.

Merging requires passing checks and explicit maintainer approval. If another open pull request depends on the branch, retarget it and confirm the new base before merging or deleting the parent branch.

## Commit rules

Use Conventional Commits [\[14\]](#ref-14): `<type>(<scope>): <summary>`, with the scope optional. For example:

```text
fix(parser): handle missing metadata
docs: explain Code Quality settings
```

Keep one logical change per commit and documentation in separate commits from code or configuration. Use `feat` for new behavior, `fix` for corrections, and `docs`, `test`, or `ci` for those concerns. Mark breaking changes explicitly and explain the migration in the pull request. Do not add Claude attribution or `Co-Authored-By` trailers.

## CI and image publishing

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs on pull requests and pushes to `main`. The shared [Nix setup action](.github/actions/setup-nix-env/action.yml) activates the development environment, then the validation job runs `just lint`, `just type`, and `just test` in sequence.

Path filters skip documentation-only changes and some configuration files. Check the workflow for the full list, and distinguish skipped checks from checks that passed when reporting validation.

After checks pass on `main`, CI builds Linux images for x86-64 and ARM64 and publishes them to `ghcr.io/eth-library/arca-flow`, tagged with the full commit SHA. Pull requests do not publish images.

## Security and code quality

CodeQL checks application and workflow code for security vulnerabilities. Code Quality adds quality rules and AI findings, while Dependabot handles dependency vulnerabilities and updates. Their configurations are separate.

### CodeQL security scanning

[.github/workflows/codeql.yml](.github/workflows/codeql.yml) defines static security analysis for Python and GitHub Actions using the default security queries. It runs on pull requests to `main`, pushes to `main`, weekly, and manually.

CodeQL analyzes code without running the application, including following data into potentially unsafe operations. It complements tests and review.

This uses GitHub's advanced setup [\[15\]](#ref-15), so managed security default setup must remain disabled. Check it with:

```bash
gh api repos/eth-library/arca-flow/code-scanning/default-setup
```

The expected state is `not-configured` because the repository workflow manages scanning.

### GitHub Code Quality

Code Quality [\[16\]](#ref-16) uses CodeQL rules to identify known quality issues and AI analysis to examine recently changed code on the default branch. Its settings live on GitHub and are managed separately from the security workflow through the API:

| Setting | Value | Purpose |
|---|---|---|
| `state` | `configured` | Enables Code Quality |
| `languages` | `["python"]` | Selects Python analysis |
| `runner_type` | `standard` | Uses standard GitHub-hosted runners |
| `ai_findings_option` | `on_push` | Enables AI findings on pushes |
| `schedule` | `weekly` | Scan schedule managed by GitHub |

Inspect the live settings:

```bash
gh api repos/eth-library/arca-flow/code-quality/setup
```

Apply or restore them:

```bash
gh api --method PATCH repos/eth-library/arca-flow/code-quality/setup \
  --raw-field state=configured \
  --raw-field 'languages[]=python' \
  --raw-field runner_type=standard \
  --raw-field ai_findings_option=on_push
```

Use an authenticated maintainer account; fine-grained tokens need repository Administration write permission [\[17\]](#ref-17). The update can start a setup run, so wait for it to finish and inspect the settings again. Keep this table aligned with intentional configuration changes; editing this document does not apply them.

Review automated findings and suggested fixes before accepting them, and test code changes as usual.

## Dependency updates

Dependabot [\[18\]](#ref-18) proposes weekly Python dependency updates through [.github/dependabot.yml](.github/dependabot.yml). The configuration selects direct dependencies and groups `dagster*` packages. Security updates can also address vulnerable transitive dependencies. GitHub Actions, Docker, and Nix version updates are not configured in Dependabot.

Routine updates go through Dependabot pull requests for review and CI checks. Developers use the committed lockfile rather than independently upgrading packages. Agree on new dependencies or other requirement changes with the maintainer before adding them.

## References

- <a id="ref-1"></a>\[1\] **Python**: the language used by the application and tests. [Python documentation](https://docs.python.org/3/)
- <a id="ref-2"></a>\[2\] **Dagster**: assets, sensors, resources, and orchestration tools. [Dagster documentation](https://docs.dagster.io/)
- <a id="ref-3"></a>\[3\] **Pydantic**: data validation and serialization using Python type hints. [Pydantic documentation](https://docs.pydantic.dev/)
- <a id="ref-4"></a>\[4\] **uv**: Python environments, dependency resolution, and lockfiles. [uv documentation](https://docs.astral.sh/uv/)
- <a id="ref-5"></a>\[5\] **pytest**: the test framework used for pipeline materialization tests. [pytest documentation](https://docs.pytest.org/en/stable/)
- <a id="ref-6"></a>\[6\] **Ruff**: Python linting and formatting. [Ruff documentation](https://docs.astral.sh/ruff/)
- <a id="ref-7"></a>\[7\] **mypy**: static type checking for Python. [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- <a id="ref-8"></a>\[8\] **pre-commit**: installing and running the configured commit hooks. [pre-commit documentation](https://pre-commit.com/)
- <a id="ref-9"></a>\[9\] **Nix flakes**: the development environment and its pinned inputs. [nix.dev: flakes](https://nix.dev/concepts/flakes.html)
- <a id="ref-10"></a>\[10\] **direnv**: per-directory environment loading. [direnv documentation](https://direnv.net/)
- <a id="ref-11"></a>\[11\] **nix-direnv**: cached Nix environment loading for direnv. [nix-community/nix-direnv](https://github.com/nix-community/nix-direnv)
- <a id="ref-12"></a>\[12\] **just**: the command runner used for development and CI recipes. [just manual](https://just.systems/man/en/)
- <a id="ref-13"></a>\[13\] **GitHub Actions**: the CI system that runs checks, publishes images, and executes scans. [GitHub Actions documentation](https://docs.github.com/en/actions)
- <a id="ref-14"></a>\[14\] **Conventional Commits**: the commit-message convention used in this repository. [Conventional Commits specification](https://www.conventionalcommits.org/)
- <a id="ref-15"></a>\[15\] **CodeQL advanced setup**: security analysis configured through a repository workflow. [GitHub: configuring advanced setup](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configuring-advanced-setup-for-code-scanning)
- <a id="ref-16"></a>\[16\] **GitHub Code Quality**: CodeQL quality rules and AI analysis of recently changed code. [GitHub: Code Quality](https://docs.github.com/en/code-security/concepts/code-quality/code-quality)
- <a id="ref-17"></a>\[17\] **Code Quality REST API**: inspecting and updating hosted settings and reading findings. [GitHub: Code Quality API](https://docs.github.com/en/rest/code-quality/code-quality)
- <a id="ref-18"></a>\[18\] **Dependabot options**: dependency selection, grouping, and version-update schedules. [GitHub: Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
