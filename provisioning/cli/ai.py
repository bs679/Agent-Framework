"""
aios ai — CLI commands for AI router testing and introspection.

Commands:
    aios ai test-routing    Print the full routing table
    aios ai health          Check all model endpoints
    aios ai test            Send a real request through the router
"""

from __future__ import annotations

import asyncio
import sys

import click

from integrations.ai.router import AIRouter

# ---------------------------------------------------------------------------
# Terminal Calm formatting helpers
# ---------------------------------------------------------------------------

DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;208m"


def _header(text: str) -> str:
    return f"\n{DIM}{text}{RESET}"


def _ok(text: str) -> str:
    return f"{GREEN}✓{RESET} {text}"


def _disabled(text: str) -> str:
    return f"{YELLOW}○{RESET} {text}"


def _error(text: str) -> str:
    return f"{ORANGE}△{RESET} {text}"


# ---------------------------------------------------------------------------
# Command group
# ---------------------------------------------------------------------------

@click.group()
def ai_group():
    """AI routing commands — test, inspect, and verify the AI router."""
    pass


# ---------------------------------------------------------------------------
# aios ai test-routing
# ---------------------------------------------------------------------------

@ai_group.command("test-routing")
def test_routing():
    """Print the full routing table in a formatted table."""
    try:
        router = AIRouter()
    except Exception as e:
        click.echo(f"Failed to load AI routing config: {e}", err=True)
        sys.exit(1)

    routing = router.config.get("routing", {})

    # Header
    click.echo(_header("AI Routing Table"))
    click.echo()
    header = f"  {'TASK TYPE':<28} {'MODEL':<12} {'SENSITIVE':<12} {'FALLBACK':<10}"
    click.echo(header)
    click.echo(f"  {'─' * 62}")

    for task_type in sorted(routing.keys()):
        cfg = routing[task_type]
        model = cfg["model"]
        sensitive = "✓ yes" if cfg["sensitive"] else "○ no"
        fallback = cfg.get("fallback") or "none"
        click.echo(f"  {task_type:<28} {model:<12} {sensitive:<12} {fallback:<10}")

    click.echo()


# ---------------------------------------------------------------------------
# aios ai health
# ---------------------------------------------------------------------------

@ai_group.command("health")
def health():
    """Check all configured model endpoints and print status."""
    try:
        router = AIRouter()
    except Exception as e:
        click.echo(f"Failed to load AI routing config: {e}", err=True)
        sys.exit(1)

    statuses = asyncio.run(router.health())

    models_cfg = router.config.get("models", {})

    click.echo(_header("AI Model Health"))
    click.echo()

    # Default model names when env vars aren't set
    _model_defaults = {
        "ollama": "llama3.1:8b",
        "kimi_k2": "moonshotai/kimi-k2",
        "claude": "claude-sonnet-4-20250514",
    }

    for model_name, status in statuses.items():
        raw = models_cfg.get(model_name, {}).get("model")
        model_id = raw if raw and raw is not False else _model_defaults.get(model_name, "unknown")

        if status == "ok":
            click.echo(f"  {_ok(f'{model_name:<16} running  ({model_id})')}")
        elif status == "disabled":
            hints = {
                "kimi_k2": "set KIMI_ENABLED=true to activate",
                "claude": "set CLAUDE_ENABLED=true to activate",
            }
            hint = hints.get(model_name, "check config")
            click.echo(f"  {_disabled(f'{model_name:<16} disabled ({hint})')}")
        else:
            click.echo(f"  {_error(f'{model_name:<16} error    ({model_id})')}")

    click.echo()


# ---------------------------------------------------------------------------
# aios ai test
# ---------------------------------------------------------------------------

@ai_group.command("test")
@click.option("--task", required=True, help="Task type from the routing table.")
@click.option("--prompt", required=True, help="Test prompt to send.")
def test(task: str, prompt: str):
    """Send a real request through the router and print routing details."""
    try:
        router = AIRouter()
    except Exception as e:
        click.echo(f"Failed to load AI routing config: {e}", err=True)
        sys.exit(1)

    click.echo(_header("AI Router Test"))
    click.echo()

    # Show routing decision
    try:
        routing_cfg = router._get_routing(task)
    except ValueError as e:
        click.echo(f"  {_error(str(e))}")
        sys.exit(1)

    click.echo(f"  Task:        {task}")
    click.echo(f"  Preferred:   {routing_cfg['model']}")
    click.echo(f"  Sensitive:   {'yes' if routing_cfg['sensitive'] else 'no'}")
    click.echo(f"  Fallback:    {routing_cfg.get('fallback') or 'none'}")

    # Check sanitizer
    if router._contains_sensitive_data(prompt):
        click.echo(f"  Sanitizer:   {_error('TRIGGERED — sensitive patterns detected')}")
    else:
        click.echo(f"  Sanitizer:   {_ok('clean')}")

    click.echo()
    click.echo(f"  {DIM}Sending request …{RESET}")
    click.echo()

    try:
        response = asyncio.run(router.complete(task=task, prompt=prompt))
    except Exception as e:
        click.echo(f"  {_error(f'Request failed: {e}')}")
        sys.exit(1)

    click.echo(f"  Routed to:   {response.routed_to}")
    click.echo(f"  Model used:  {response.model_used}")
    click.echo(f"  Fallback:    {'yes' if response.fallback_used else 'no'}")
    click.echo()
    click.echo(f"  {DIM}── Response ──{RESET}")
    click.echo()
    click.echo(f"  {response.text}")
    click.echo()
