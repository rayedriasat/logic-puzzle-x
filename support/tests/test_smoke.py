"""Smoke tests: the scaffold imports, the CLI parses, and the sample data is well formed."""
from pathlib import Path

import main
from support.server import app, health

ROOT = Path(__file__).resolve().parents[2]


def test_cli_offers_all_commands():
    help_text = main.build_parser().format_help()
    for command in ("serve", "solve", "bench", "generate"):
        assert command in help_text


def test_health_route_reports_ok():
    assert "/api/health" in {route.path for route in app.routes}
    assert health()["status"] == "ok"


def test_famous_puzzles_are_well_formed():
    text = (ROOT / "data" / "sudoku" / "famous.txt").read_text(encoding="utf-8")
    grids = [line.split()[0] for line in text.splitlines() if line.strip() and not line.startswith("#")]
    assert len(grids) == 3
    for grid in grids:
        assert len(grid) == 81
        assert set(grid) <= set("123456789.")
