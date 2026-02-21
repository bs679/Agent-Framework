"""AIOS CLI — manage the agent plane.

Entry point for the `aios` command. Registers all command groups.
"""

import typer

from provisioning.cli.commands import planes, agents, config

app = typer.Typer(
    name="aios",
    help="Manage OpenClaw agent planes, agents, and configuration.",
    no_args_is_help=True,
)

app.add_typer(planes.app, name="planes")
app.add_typer(agents.app, name="agents")
app.add_typer(config.app, name="config")


if __name__ == "__main__":
    app()
