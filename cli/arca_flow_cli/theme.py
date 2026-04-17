"""ETH Zurich brand colours and Rich console configuration for the dap CLI.

Uses official ETH Zurich brand colours and their CI/CD-defined shades.
Light terminals use 100% base colours; dark terminals use 80% shades
for readability. Detection order:
  1. DAP_THEME=light|dark  (explicit override)
  2. COLORFGBG env var     (set by some terminals)
  3. Default: dark         (most developer terminals)

Respects NO_COLOR and CI environments (disables all colour output).

Colour reference:
  https://ethz.ch/staffnet/en/service/communication/corporate-design/colours.html
"""

import os

from rich.console import Console
from rich.theme import Theme

# ETH Zurich official brand colours — 100% (base) and 80% (shade)
# https://ethz.ch/staffnet/en/service/communication/corporate-design/colours.html
_PALETTE: dict[str, dict[str, str]] = {
    "blue": {"light": "#215CAF", "dark": "#4D7DBF"},
    "petrol": {"light": "#007894", "dark": "#3395AB"},
    "green": {"light": "#627313", "dark": "#818F42"},
    "bronze": {"light": "#8E6713", "dark": "#A58542"},
    "red": {"light": "#B7352D", "dark": "#C55D57"},
    "grey": {"light": "#6F6F6F", "dark": "#8C8C8C"},
}

# Logo always uses the full-strength ETH Blue (100%)
ETH_BLUE_LOGO = "#215CAF"


def _detect_background() -> str:
    """Detect terminal background brightness. Returns 'dark' or 'light'.

    Safe fallback: always returns a valid value, never raises.
    """
    override = os.getenv("DAP_THEME", "").lower()
    if override in ("light", "dark"):
        return override

    # COLORFGBG: "foreground;background" — higher bg value means lighter background
    colorfgbg = os.getenv("COLORFGBG")
    if colorfgbg:
        try:
            bg = int(colorfgbg.rsplit(";", 1)[-1])
            return "light" if bg >= 8 else "dark"
        except (ValueError, IndexError):
            pass

    return "dark"


def _is_ci() -> bool:
    return os.getenv("CI") is not None or os.getenv("GITHUB_ACTIONS") is not None


_bg = _detect_background()

# Resolved palette for current terminal background
ETH_BLUE = _PALETTE["blue"][_bg]
ETH_PETROL = _PALETTE["petrol"][_bg]
ETH_GREEN = _PALETTE["green"][_bg]
ETH_BRONZE = _PALETTE["bronze"][_bg]
ETH_RED = _PALETTE["red"][_bg]
ETH_GREY = _PALETTE["grey"][_bg]

dap_theme = Theme(
    {
        "success": f"bold {ETH_GREEN}",
        "error": f"bold {ETH_RED}",
        "warning": f"{ETH_BRONZE}",
        "info": f"{ETH_PETROL}",
        "title": f"bold {ETH_BLUE}",
        "hint": ETH_GREY,
        "command": f"bold {ETH_BLUE}",
    }
)

console = Console(
    theme=dap_theme,
    stderr=True,
    no_color=os.getenv("NO_COLOR") is not None or _is_ci(),
)

# Symbols
OK = "[hint]\u2713[/]"
FAIL = "[error]\u2717[/]"
WARN = "[warning]![/]"
ARROW = "[info]\u2192[/]"
DASH = "[hint]\u2014[/]"
