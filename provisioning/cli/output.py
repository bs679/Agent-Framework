"""Rich Terminal Calm output helpers.

Terminal Calm rules:
- Dark backgrounds, no decorative elements
- Gentle, non-judgmental language
- Traffic light status: green/yellow/orange (NEVER red)
- Progressive disclosure
- ADHD-friendly: reduce cognitive load
"""

from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

# Status colors — NEVER use "red" or "bright_red"
STATUS_RUNNING = "green"
STATUS_STARTING = "yellow"
STATUS_DEGRADED = "dark_orange"
STATUS_STOPPED = "dim white"

STATUS_ICONS = {
    "running": ("\u2713", STATUS_RUNNING),
    "starting": ("~", STATUS_STARTING),
    "degraded": ("!", STATUS_DEGRADED),
    "stopped": ("\u25cb", STATUS_STOPPED),
    "removing": ("~", STATUS_STARTING),
    "paused": ("\u25cb", STATUS_STOPPED),
    "exited": ("\u25cb", STATUS_STOPPED),
    "created": ("~", STATUS_STARTING),
    "restarting": ("~", STATUS_STARTING),
    "dead": ("!", STATUS_DEGRADED),
}


def success(message: str) -> None:
    console.print(f"[{STATUS_RUNNING}]\u2713[/{STATUS_RUNNING}] {message}")


def warning(message: str) -> None:
    console.print(f"[{STATUS_STARTING}]~[/{STATUS_STARTING}] {message}")


def degraded(message: str) -> None:
    console.print(f"[{STATUS_DEGRADED}]![/{STATUS_DEGRADED}] {message}")


def stopped(message: str) -> None:
    console.print(f"[{STATUS_STOPPED}]\u25cb[/{STATUS_STOPPED}] {message}")


def info(message: str) -> None:
    console.print(f"  {message}")


def error(message: str) -> None:
    """Print a plain-language error. Never stack traces."""
    console.print(f"[{STATUS_DEGRADED}]![/{STATUS_DEGRADED}] {message}")


def status_icon(status: str) -> tuple[str, str]:
    """Return (icon, color) for a container status string."""
    return STATUS_ICONS.get(status, ("?", STATUS_STOPPED))


def print_agent_row(agent_id: str, status: str, description: str) -> None:
    icon, color = status_icon(status)
    console.print(
        f"  [{color}]{icon}[/{color}] {agent_id:<30} {status:<12} {description}"
    )


def make_table(*columns: str, title: str | None = None) -> Table:
    table = Table(title=title, show_header=True, header_style="bold", box=None)
    for col in columns:
        table.add_column(col)
    return table
