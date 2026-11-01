"""Sudoku <-> CSP for any box size (4x4, 6x6, 9x9, 16x16).

9x9: 81 variables, 810 binary "not equal" factors; each cell's 20 peers form its Markov blanket.
Givens are applied by conditioning (Vol. 3). Global variant: 27 AllDifferent factors (plan.md section 3.5).
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import isqrt

from . import sat
from .csp import CSP, AllDifferent, NotEqual
from .solver import SolveResult, solve
from .trace import Tracer

DIGITS = "123456789ABCDEFGHIJKLMNOP"


def box_shape(size: int) -> tuple:
    """Box rows x cols with the most square shape: 9 -> (3, 3), 6 -> (2, 3), 16 -> (4, 4)."""
    rows = isqrt(size)
    while size % rows:
        rows -= 1
    return rows, size // rows


@dataclass(frozen=True)
class Grid:
    size: int
    box: tuple    # (box rows, box cols)
    cells: tuple  # row-major ints, 0 = empty

    @property
    def units(self) -> list:
        return units(self.size, self.box)

    def __str__(self) -> str:
        return "".join(DIGITS[v - 1] if v else "." for v in self.cells)


@lru_cache(maxsize=None)
def units(size: int, box: tuple) -> tuple:
    """(name, cell indexes) of every row, column and box."""
    br, bc = box
    rows = [(f"row {r + 1}", tuple(r * size + c for c in range(size))) for r in range(size)]
    cols = [(f"col {c + 1}", tuple(r * size + c for r in range(size))) for c in range(size)]
    boxes = [(f"box {i + 1}", tuple((r0 * br + r) * size + c0 * bc + c for r in range(br) for c in range(bc)))
             for i, (r0, c0) in enumerate((r, c) for r in range(bc) for c in range(br))]
    return tuple(rows + cols + boxes)


def parse(text: str, box=None) -> Grid:
    """Accepts '.' or '0' for empty cells; whitespace is ignored. Raises ValueError on bad input."""
    chars = "".join(text.split()).upper()
    size = isqrt(len(chars))
    if not chars or size * size != len(chars) or size > len(DIGITS):
        raise ValueError(f"a Sudoku has N*N cells (N up to {len(DIGITS)}); got {len(chars)} characters")
    allowed = {".": 0, "0": 0, **{d: i + 1 for i, d in enumerate(DIGITS[:size])}}
    bad = sorted(set(chars) - set(allowed))
    if bad:
        raise ValueError(f"invalid characters for a {size}x{size} Sudoku: {' '.join(bad)}")
    box = tuple(box) if box else box_shape(size)
    if box[0] * box[1] != size:
        raise ValueError(f"box {box[0]}x{box[1]} does not fit a {size}x{size} grid")
    return Grid(size, box, tuple(allowed[c] for c in chars))


def peers(cell: int, size: int = 9, box=None) -> set:
    """Markov blanket of a cell: every other cell in its row, column or box."""
    return {u for _, unit in units(size, box or box_shape(size)) if cell in unit for u in unit} - {cell}


@lru_cache(maxsize=None)
def _factors(size: int, box: tuple, global_alldiff: bool) -> tuple:
    if global_alldiff:
        return tuple(AllDifferent(unit, name, permutation=True) for name, unit in units(size, box))
    seen = {}
    for name, unit in units(size, box):
        for i, a in enumerate(unit):
            for b in unit[i + 1:]:
                seen.setdefault((min(a, b), max(a, b)), name)  # a pair in a row and a box is labeled by the row
    return tuple(NotEqual(a, b, name) for (a, b), name in seen.items())


def to_csp(grid: Grid, global_alldiff: bool = False) -> CSP:
    names = [f"r{i // grid.size + 1}c{i % grid.size + 1}" for i in range(grid.size ** 2)]
    domain = range(1, grid.size + 1)
    csp = CSP([domain] * grid.size ** 2, _factors(grid.size, grid.box, global_alldiff), names)
    for var, value in enumerate(grid.cells):
        if value:
            csp.condition(var, value)
    return csp


def solve_grid(grid: Grid, algorithm: str = "mac", tracer=None, timeout=None, limit: int = 1,
               rng=None, global_alldiff=None) -> SolveResult:
    """Run one --algo id on a grid: picks the formulation it needs (mac+ global, dpll CNF)."""
    tracer = tracer or Tracer(max_events=0)  # started here so `ms` includes building the model
    if algorithm == "dpll":
        return sat.solve(grid, tracer, timeout, limit, bool(global_alldiff))
    use_global = algorithm == "mac+" if global_alldiff is None else global_alldiff
    return solve(to_csp(grid, use_global), algorithm, tracer, timeout, limit, rng)


def solution_string(solution: dict, size: int) -> str:
    return "".join(DIGITS[solution[i] - 1] for i in range(size ** 2))


def format_grid(text: str, box=None) -> str:
    """Pretty-print a grid string for the terminal."""
    grid = parse(text, box)
    br, bc = grid.box
    lines = []
    for r in range(grid.size):
        if r and r % br == 0:
            lines.append("-" * (2 * grid.size + 2 * (br - 1) - 1))
        row = [str(grid)[r * grid.size + c] + (" |" if (c + 1) % bc == 0 and c + 1 < grid.size else "")
               for c in range(grid.size)]
        lines.append(" ".join(row))
    return "\n".join(lines)
