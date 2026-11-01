"""API handlers, called directly (TestClient would add httpx to requirements for no extra coverage)."""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from support import server

EULER = "..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3.."


def test_solve_returns_the_trace_format():
    body = server.solve(server.SolveRequest(puzzle=EULER, algorithm="mac"))
    assert body["status"] == "solved"
    assert body["puzzle"] == {"type": "sudoku", "size": 9, "box": (3, 3), "grid": EULER}
    assert len(body["solution"]) == 81
    assert body["events"][-1] == ["S"]
    assert body["truncated"] is False
    assert set(body["stats"]) == {"nodes", "backtracks", "checks", "prunes", "ms"}


def test_trace_can_be_skipped():
    assert "events" not in server.solve(server.SolveRequest(puzzle=EULER, trace=False))


def test_solve_can_explain_and_prove():
    body = server.solve(server.SolveRequest(puzzle=EULER, algorithm="mac+", explain=True, prove=True))
    assert body["unique"] is True
    assert body["explanation"][0]["text"].startswith("r")


def test_bad_puzzle_is_a_422():
    with pytest.raises(HTTPException) as caught:
        server.solve(server.SolveRequest(puzzle="not a sudoku"))
    assert caught.value.status_code == 422


def test_unsolvable_board_is_reported_not_raised():
    assert server.solve(server.SolveRequest(puzzle="55" + "." * 79))["status"] == "unsat"


@pytest.mark.parametrize("fields", [{"puzzle": "." * 2000}, {"puzzle": EULER, "algorithm": "magic"},
                                    {"puzzle": EULER, "timeout": 500}, {"puzzle": EULER, "timeout": 0}])
def test_requests_are_validated_at_the_boundary(fields):
    with pytest.raises(ValidationError):
        server.SolveRequest(**fields)


def test_race_runs_each_algorithm():
    body = server.race(server.RaceRequest(puzzle=EULER, algorithms=["bt", "mac"]))
    assert [r["algorithm"] for r in body["results"]] == ["bt", "mac"]
    assert body["results"][0]["solution"] == body["results"][1]["solution"]


def test_race_is_capped_at_four_boards():
    with pytest.raises(ValidationError):
        server.RaceRequest(puzzle=EULER, algorithms=["bt", "fc", "mrv", "lcv", "mac"])


def test_generate_returns_a_playable_puzzle():
    body = server.generate(server.GenerateRequest(size=4, difficulty="easy", seed=1))
    assert body["unique"] is True
    assert len(body["puzzle"]) == 16


def test_16x16_generation_is_not_offered_live():
    with pytest.raises(ValidationError):
        server.GenerateRequest(size=16)


def test_puzzles_filter_and_limit():
    famous = server.puzzles(difficulty="famous", limit=50)
    assert {p["id"] for p in famous} >= {"inkala-2012"}
    assert server.puzzles(limit=0) == []
    assert server.puzzles(size=5) == []


def test_benchmarks_route_answers_before_results_exist():
    assert "machine" in server.benchmarks()
