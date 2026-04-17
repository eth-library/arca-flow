"""Subprocess helpers for running external commands."""

import shutil
import subprocess
import sys


def run_passthrough(args: list[str]) -> int:
    """Run a command with stdout/stderr connected to the terminal. Returns exit code."""
    result = subprocess.run(args)
    return result.returncode


def run_interactive(args: list[str]) -> int:
    """Run a command with full stdin/stdout/stderr connected (for interactive use)."""
    result = subprocess.run(args, stdin=sys.stdin)
    return result.returncode


def run_capture(
    args: list[str], timeout: int | None = None, input: str | None = None
) -> tuple[int, str]:
    """Run a command and capture stdout. Returns (exit_code, stdout).

    Pass ``input`` to feed data to the command's stdin (e.g. piping output
    from one command into another).
    """
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=input)
        return result.returncode, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, ""


def which(name: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(name) is not None
