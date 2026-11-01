"""Smoke tests: the scaffold imports, the CLI parses, and the sample data is well formed."""
from pathlib import Path

import main
from support.server import app, health

ROOT = Path(__file__).resolve().parents[2]


def test_cli_offers_all_commands():
    help_text = main.build_parser().format_help()
    for command in ("serve", "solve", "bench", "generate"):
        assert command in help_text


def test_solve_command_solves_a_puzzle_file(capsys):
    assert main.main(["solve", str(ROOT / "data" / "sudoku" / "famous.txt"), "--algo", "mrv"]) == 0
    assert "solved nodes=" in capsys.readouterr().out


def test_solve_command_can_explain(capsys):
    assert main.main(["solve", "1...2...3...4...", "--algo", "mac", "--explain"]) == 0
    assert "r1c2" in capsys.readouterr().out


def test_solve_command_rejects_bad_input(capsys):
    assert main.main(["solve", "not a puzzle"]) == 2
    assert "Invalid puzzle" in capsys.readouterr().out


def test_kakuro_is_reported_as_planned(capsys):
    assert main.main(["solve", "x", "--type", "kakuro"]) == 2
    assert main.main(["generate", "--type", "kakuro"]) == 2
    assert "planned" in capsys.readouterr().out


def test_generate_command_prints_puzzle_and_grade(capsys):
    assert main.main(["generate", "--size", "4", "--difficulty", "easy"]) == 0
    grid, grade = capsys.readouterr().out.split()
    assert len(grid) == 16
    assert grade == "easy"


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
