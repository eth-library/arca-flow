# arca-flow — developer commands
#
# Run `just` with no arguments to see available commands.
# Run `just welcome` any time to re-show the banner.

# Default: list recipes
default:
    @just --list --unsorted

# Display the welcome banner + tool summary
welcome:
    #!/usr/bin/env bash
    set -u

    # ETH Zurich corporate colours (brand palette).
    # 256-colour codes are used for broad compatibility (macOS Terminal.app does not
    # support truecolor). Set COLORTERM=truecolor to opt in to 24-bit variants.
    if [[ "${COLORTERM:-}" == "truecolor" || "${COLORTERM:-}" == "24bit" ]]; then
        ETH_BLUE_LIGHT=$'\033[38;2;33;92;175m'   # #215CAF — primary ETH blue
        ETH_BLUE_DARK=$'\033[38;2;74;142;212m'    # #4A8ED4 — lighter tint
    else
        ETH_BLUE_LIGHT=$'\033[38;5;25m'           # xterm-256: nearest to #215CAF
        ETH_BLUE_DARK=$'\033[38;5;75m'            # xterm-256: lighter blue for dark bg
    fi
    RESET=$'\033[0m'
    DIM=$'\033[2m'

    # Detect light/dark background.
    # COLORFGBG="fg;bg" (xterm convention): bg=15 → light.
    # Apple Terminal defaults to white when COLORFGBG is not set.
    if [[ "${COLORFGBG:-}" == *";15" || ( -z "${COLORFGBG:-}" && "${TERM_PROGRAM:-}" == "Apple_Terminal" ) ]]; then
        BANNER_COLOR="$ETH_BLUE_LIGHT"
    else
        BANNER_COLOR="$ETH_BLUE_DARK"
    fi

    # NO_COLOR (https://no-color.org): any non-empty value disables colour.
    # We filter SGR escapes out of the rendered output rather than emitting a
    # second uncoloured banner file — single source of truth.
    if [[ -n "${NO_COLOR:-}" ]]; then
        emit() { sed $'s/\x1b\\[[0-9;]*m//g'; }
    else
        emit() { cat; }
    fi

    echo

    # Banner — gracefully degrade if banner.txt is missing or unreadable.
    # banner.txt is plain chars; colour is applied entirely here.
    if [[ -r banner.txt ]]; then
        printf '%s%s%s\n' "$BANNER_COLOR" "$(<banner.txt)" "$RESET" | emit
    else
        { printf '  %s◆ arca-flow · Orchestration Engine%s\n' "$BANNER_COLOR" "$RESET"
          printf '  %sArca · Digital Preservation Pipeline · ETH Library Zurich%s\n' "$DIM" "$RESET"
        } | emit
    fi
    echo

    # Tools — `<tool> --version` first line, second whitespace-separated token.
    # Works for: Python 3.13.5 / uv 0.7.2 (sha date) / ruff 0.11.2 /
    # mypy 1.20.1 (compiled: yes) / pytest 9.0.3.
    echo "  Tools"
    for tool in python uv ruff mypy pytest; do
        if command -v "$tool" >/dev/null 2>&1; then
            version=$("$tool" --version 2>&1 | head -1 | awk '{print $2}')
            : "${version:=unknown}"
        else
            version="not found"
        fi
        printf '    %-10s %s\n' "$tool" "$version"
    done
    echo

    echo "  Environment"
    printf '    %-10s %s\n' "cwd"     "$(pwd)"
    printf '    %-10s %s\n' "venv"    "${VIRTUAL_ENV:-not set}"
    printf '    %-10s %s\n' "dagster" "${DAGSTER_HOME:-not set}"
    echo

    { printf '  %sRun "just check" to run lint + typecheck + tests.%s\n' "$DIM" "$RESET"
      printf '  %sRun "just"        to list all available commands.%s\n' "$DIM" "$RESET"
    } | emit
    echo

# Run all quality checks (lint + type + test)
check: lint type test

# Run tests with pytest (extra args passed through: `just test -k foo`)
test *args:
    uv run pytest arca/flow/tests {{args}}

# Lint: check code style + formatting (read-only, no rewrites)
lint:
    uv run ruff check arca arca/flow/tests
    uv run ruff format --check arca arca/flow/tests

# Format: apply formatter + auto-fix lint issues (write)
format:
    uv run ruff check --fix arca arca/flow/tests
    uv run ruff format arca arca/flow/tests

# Type-check with mypy
type:
    uv run mypy arca arca/flow/tests

# Start the Dagster dev server (via dg — the project-scoped CLI)
run:
    uv run dg dev
