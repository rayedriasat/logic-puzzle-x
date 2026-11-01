"""Search: every algorithm agrees, heuristics help, and the failure paths report honestly."""
from pathlib import Path

import pytest

from support.solver import ALGORITHMS
from support.sudoku import parse, solution_string, solve_grid, to_csp
from support.trace import Tracer

ROOT = Path(__file__).resolve().parents[2]
LINES = (ROOT / "data" / "sudoku" / "famous.txt").read_text(encoding="utf-8").splitlines()
FAMOUS = {line.split()[1]: line.split()[0] for line in LINES if line.strip() and not line.startswith("#")}
ALL = [*ALGORITHMS, "dpll"]
EULER = FAMOUS["euler-96-grid-01"]
INKALA = FAMOUS["inkala-2012"]
TWO_FIVES_IN_A_ROW = "55" + "." * 79
# Row 1 needs a 9 only at r1c9, which col 9 already holds: every cell is consistent, the puzzle is not.
NO_SOLUTION = "12345678." + "........9" + "." * 63
FOUR_SOLUTIONS_AT_LEAST = "." * 16


@pytest.mark.parametrize("algorithm", ALL)
def test_every_algorithm_finds_the_same_solution(algorithm):
    reference = solve_grid(parse(EULER), "mac+")
    result = solve_grid(parse(EULER), algorithm, timeout=30)
    assert result.status == "solved"
    assert result.solution == reference.solution


@pytest.mark.parametrize("name", FAMOUS)
def test_famous_puzzles_are_unique(name):
    result = solve_grid(parse(FAMOUS[name]), "mac+", limit=2)
    assert len(result.solutions) == 1


def test_a_solved_grid_satisfies_every_factor():
    grid = parse(INKALA)
    solution = solve_grid(grid, "mac+").solution
    assert to_csp(grid).weight(solution) == 1


def test_propagation_cuts_search_on_the_hardest_puzzle():
    nodes = {a: solve_grid(parse(INKALA), a, timeout=60).stats["nodes"] for a in ("fc", "mrv", "mac", "mac+")}
    assert nodes["mac+"] < nodes["mac"] < nodes["mrv"] < nodes["fc"]


@pytest.mark.parametrize("algorithm", ALL)
def test_conflicting_givens_are_unsat(algorithm):
    assert solve_grid(parse(TWO_FIVES_IN_A_ROW), algorithm, timeout=30).status == "unsat"


@pytest.mark.parametrize("algorithm", ["mrv", "lcv", "mac", "mac+", "dpll"])
def test_consistent_givens_without_a_solution_are_unsat(algorithm):
    assert solve_grid(parse(NO_SOLUTION), algorithm, timeout=30).status == "unsat"


@pytest.mark.parametrize("algorithm", ALL)
def test_full_grid_solves_without_search(algorithm):
    full = solution_string(solve_grid(parse(EULER), "mac").solution, 9)
    result = solve_grid(parse(full), algorithm)
    assert result.status == "solved"
    assert result.stats["nodes"] == 0


@pytest.mark.parametrize("algorithm", ALL)
def test_limit_2_finds_a_second_solution(algorithm):
    assert len(solve_grid(parse(FOUR_SOLUTIONS_AT_LEAST), algorithm, limit=2).solutions) == 2


@pytest.mark.parametrize("algorithm", ALL)
def test_timeout_is_reported(algorithm):
    assert solve_grid(parse(INKALA), algorithm, timeout=1e-6).status == "timeout"


def test_timeout_during_a_uniqueness_check_is_not_a_proof():
    result = solve_grid(parse(EULER), "bt", limit=2, timeout=0.05)
    assert result.status == "timeout"


def test_stats_count_every_event():
    tracer = Tracer()
    result = solve_grid(parse(FAMOUS["ai-escargot-2006"]), "mac", tracer)
    kinds = [event[0] for event in tracer.events]
    assert result.stats["nodes"] == kinds.count("A")
    assert result.stats["backtracks"] == kinds.count("B")
    assert result.stats["prunes"] == kinds.count("P")
    assert kinds[-1] == "S"
    assert result.stats["checks"] > 0
