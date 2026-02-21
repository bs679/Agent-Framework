"""AIOS CLI — provisioning and management for OpenClaw agent planes."""

import click

from provisioning.cli.planes import planes
from provisioning.cli.agents import agents


@click.group()
def cli():
    """AIOS — OpenClaw Multi-Tenant Agent Provisioning CLI."""
    pass


cli.add_command(planes)
cli.add_command(agents)
