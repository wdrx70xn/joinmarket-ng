"""CLI tests for jmwalletd."""

from __future__ import annotations

import click
from typer.testing import CliRunner

from jmwalletd.cli import app

runner = CliRunner()


def test_root_help_shows_completion_options() -> None:
    """jmwalletd CLI should expose Typer shell completion options."""
    result = runner.invoke(app, ["--help"], prog_name="jmwalletd")
    output = click.unstyle(result.stdout)

    assert result.exit_code == 0
    assert "--install-completion" in output
    assert "--show-completion" in output
