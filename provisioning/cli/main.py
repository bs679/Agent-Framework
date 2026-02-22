"""
aios CLI — top-level entry point.

Usage:
    aios ai test-routing    Show the full routing table
    aios ai health          Check model endpoint status
    aios ai test            Send a test request through the router
"""

import click

from provisioning.cli.ai import ai_group


@click.group()
def cli():
    """AIOS — Agent Infrastructure & Orchestration System."""
    pass


cli.add_command(ai_group, name="ai")


if __name__ == "__main__":
    cli()
