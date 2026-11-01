"""Generated puzzles have one solution and the requested grade."""
import pytest

from support import sat
from support.generator import GRADES, generate_sudoku, grade, is_unique
from support.sudoku import parse, solve_grid


@pytest.mark.parametrize("size", [4, 6, 9])
def test_generated_puzzle_is_unique_by_both_paradigms(size):
    puzzle, solution, _ = generate_sudoku(size, "medium", seed=1)
    assert is_unique(puzzle)
    assert sat.is_unique(puzzle, solution)
    assert solve_grid(puzzle, "mac+").solution == solution


@pytest.mark.parametrize("difficulty", GRADES[:3])
def test_9x9_hits_the_requested_grade(difficulty):
    puzzle, _, found = generate_sudoku(9, difficulty, seed=2)
    assert found == difficulty == grade(puzzle)


def test_harder_grades_keep_fewer_clues():
    clues = [sum(1 for v in generate_sudoku(9, d, seed=3)[0].cells if v) for d in GRADES[:3]]
    assert clues == sorted(clues, reverse=True)


def test_same_seed_same_puzzle():
    assert generate_sudoku(9, "easy", seed=5)[0] == generate_sudoku(9, "easy", seed=5)[0]


def test_budget_still_returns_a_unique_puzzle():
    puzzle, solution, _ = generate_sudoku(9, "hard", seed=4, budget=0.0)
    assert is_unique(puzzle)


def test_grade_uses_the_propagation_ladder():
    assert grade(parse("..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3..")) == "easy"
    assert grade(parse("8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..")) == "extreme"


def test_is_unique_rejects_many_solutions():
    assert not is_unique(parse("." * 16))
