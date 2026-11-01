"""Generate puzzles with exactly one solution and grade their difficulty.

Fill a random complete grid, remove clues while the solution stays unique (solver with limit=2),
then grade by what it takes to solve: AC-3 alone, AC-3 + hidden singles, or real search.
"""
from __future__ import annotations

import random
import time

from . import sat
from .propagation import ac3, global_propagate
from .sudoku import Grid, box_shape, solve_grid, to_csp
from .trace import Tracer

GRADES = ["easy", "medium", "hard", "extreme"]
CLUE_SHARE = {"easy": 0.47, "medium": 0.38, "hard": 0.31, "extreme": 0.25}  # stop digging at this share of the cells
HARD_BACKTRACKS = 10  # mac+ backtracks that separate hard from extreme, calibrated on generated 9x9 puzzles
ATTEMPTS = 20         # fresh grids to try before settling for the closest grade
STEP_TIMEOUT = 20.0   # seconds for one uniqueness or grading check; only 16x16 ever gets near it


def grade(grid: Grid) -> str:
    """easy: AC-3 solves it · medium: AC-3 + hidden singles solve it · hard / extreme: search is needed."""
    csp = to_csp(grid, global_alldiff=True)
    domains = csp.copy_domains()
    tracer = Tracer(max_events=0)
    if ac3(csp, domains, tracer) and all(len(d) == 1 for d in domains):
        return "easy"
    if global_propagate(csp, domains, tracer) and all(len(d) == 1 for d in domains):
        return "medium"
    result = solve_grid(grid, "mac+", timeout=STEP_TIMEOUT)
    return "hard" if result.status == "solved" and result.stats["backtracks"] <= HARD_BACKTRACKS else "extreme"


def is_unique(grid: Grid) -> bool:
    result = solve_grid(grid, "mac+", limit=2, timeout=STEP_TIMEOUT)
    return result.status == "solved" and len(result.solutions) == 1  # a timeout proves nothing, so keep the clue


def _fill(size: int, box: tuple, rng: random.Random) -> list:
    empty = Grid(size, box, (0,) * size ** 2)
    solution = solve_grid(empty, "mac+", rng=rng).solution
    return [solution[i] for i in range(size ** 2)]


def _dig(solved: list, size: int, box: tuple, difficulty: str, rng: random.Random, deadline=None) -> Grid:
    """Remove clues in random order; skip a removal that breaks uniqueness or overshoots the grade."""
    cells = list(solved)
    target = round(CLUE_SHARE[difficulty] * size ** 2)
    limit = GRADES.index(difficulty)
    order = rng.sample(range(size ** 2), size ** 2)
    clues = size ** 2
    for cell in order:
        if clues <= target or (deadline and time.perf_counter() > deadline):
            break
        value, cells[cell] = cells[cell], 0
        candidate = Grid(size, box, tuple(cells))
        if is_unique(candidate) and GRADES.index(grade(candidate)) <= limit:
            clues -= 1
        else:
            cells[cell] = value
    return Grid(size, box, tuple(cells))


def generate_sudoku(size: int = 9, difficulty: str = "medium", seed=None, box=None, budget: float = 30.0) -> tuple:
    """Return (puzzle Grid, solution dict, grade); digging proved uniqueness with mac+, SAT re-proves it up to 9x9.

    Keeps the attempt closest to the requested grade if `budget` seconds or ATTEMPTS run out.
    """
    rng = random.Random(seed)
    box = tuple(box) if box else box_shape(size)
    deadline = time.perf_counter() + budget
    want = GRADES.index(difficulty)
    best = None
    for _ in range(ATTEMPTS):
        solved = _fill(size, box, rng)
        puzzle = _dig(solved, size, box, difficulty, rng, deadline)
        found = grade(puzzle)
        distance = abs(GRADES.index(found) - want)
        if best is None or distance < best[0]:
            best = distance, puzzle, solved, found
        if not distance or time.perf_counter() > deadline:
            break
    _, puzzle, solved, found = best
    solution = dict(enumerate(solved))
    # shortcut: our DPLL cannot finish 16x16 unsatisfiability proofs, add clause learning to cover them
    if size <= 9 and not sat.is_unique(puzzle, solution):
        raise RuntimeError("generator produced a puzzle with more than one solution")  # MAC and SAT disagree: a bug
    return puzzle, solution, found
