"""Startup identity banner for arca-* CLIs.

Rendered once at startup / --help greeting — not per-command, not in logs.
Composes the ASCII component logo above a Rich Panel whose top border
carries the component id and role, and whose body shows the shared
Arca / Data Archive lineage.

Centered body text is intentional and specific to this banner: it acts
as an identity nameplate. All other panels in the app left-align.

Designed for reuse across every arca-* CLI — takes component id, role,
and logo; everything else (lineage lines, layout, accent) is baked in.
"""

from rich.box import ROUNDED
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text

# Umbrella lineage — identical for every arca-* component, by design.
_LINEAGE = "Arca · Digital Preservation Pipeline\nData Archive · ETH Library Zurich"

# Layout constants.
_OUTER_MARGIN = 2  # outer left padding before the panel border
_PADDING_H = 3  # panel's internal horizontal padding
_TOP_BORDER_LEAD = 3  # '╭─ ' rendered by Rich before the title content
_DIAMOND_PREFIX = 2  # '◆ ' — our title prefix before the component id

# Indent that puts the logo's first character under the component id in the
# panel's top border: ` ` * outer + '╭─ ' + '◆ ' = outer + 5. Computed so
# any arca-* component reuses this without hard-coding.
_LOGO_INDENT = _OUTER_MARGIN + _TOP_BORDER_LEAD + _DIAMOND_PREFIX


def render_startup_banner(
    console: Console,
    component_id: str,
    role: str,
    logo: str,
    accent: str = "#215CAF",
    show_logo: bool = True,
) -> None:
    """Render the arca-* startup identity banner.

    Args:
        console: Rich Console to render to.
        component_id: Component log/pod identifier (e.g. ``arca-flow``).
        role: Component role (e.g. ``Orchestration Engine``).
        logo: Multi-line ASCII logo text.
        accent: Accent colour for border, title, and logo (default ETH Blue).
        show_logo: When False, render only the identity panel (no ASCII logo
            above it). Used in CI logs where the logo adds noise.
    """
    if show_logo:
        indent = " " * _LOGO_INDENT
        indented_logo = "\n".join(f"{indent}[{accent}]{line}[/]" for line in logo.splitlines())
        console.print(indented_logo)
    console.print(
        Padding(
            Panel(
                Text.from_markup(f"[hint]{_LINEAGE}[/]", justify="center"),
                title=f"[bold {accent}]◆ {component_id} ── {role}[/]",
                title_align="left",
                border_style=accent,
                box=ROUNDED,
                padding=(0, _PADDING_H),
                expand=False,
            ),
            (0, 0, 0, _OUTER_MARGIN),
            expand=False,
        )
    )
