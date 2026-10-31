"""Propositional track: Sudoku -> CNF, a DPLL solver and uniqueness by entailment.

Course link: Vol. 4, CNF, satisfiability, resolution; KB entails s iff KB + {not s} is unsatisfiable.
Symbol p(r,c,v) = "cell (r,c) holds v", numbered from 1. Literals are +symbol / -symbol.
DPLL keeps per-clause counters so unit propagation only touches clauses that mention the literal.
"""
from __future__ import annotations

import sys
import time
from itertools import combinations

from .solver import SolveResult
from .trace import Tracer


def symbol(grid, cell: int, value: int) -> int:
    return cell * grid.size + value


def decode(grid, sym: int) -> tuple:
    return (sym - 1) // grid.size, (sym - 1) % grid.size + 1  # (cell, value)


def encode(grid, extended: bool = False) -> list:
    """Clauses: each cell holds at least one value, at most one value, each value at most once per unit.

    `extended` adds the redundant "at least once per unit" clauses. Givens become unit clauses.
    """
    n = grid.size
    values = range(1, n + 1)
    clauses = []
    for cell in range(n * n):
        clauses.append([symbol(grid, cell, v) for v in values])
        clauses += [[-symbol(grid, cell, a), -symbol(grid, cell, b)] for a, b in combinations(values, 2)]
    for _, unit in grid.units:
        for v in values:
            clauses += [[-symbol(grid, a, v), -symbol(grid, b, v)] for a, b in combinations(unit, 2)]
            if extended:
                clauses.append([symbol(grid, cell, v) for cell in unit])
    clauses += [[symbol(grid, cell, v)] for cell, v in enumerate(grid.cells) if v]
    return clauses


class _DPLL:
    """Recursive DPLL. Search state lives in counters and is undone from a trail."""

    def __init__(self, clauses, n_symbols, grid, tracer, deadline):
        self.clauses, self.grid, self.tracer, self.deadline = clauses, grid, tracer, deadline
        self.occurs = {}
        for i, clause in enumerate(clauses):
            for lit in clause:
                self.occurs.setdefault(lit, []).append(i)
        self.value = [0] * (n_symbols + 1)  # 0 unknown, 1 true, -1 false
        self.satisfied = [0] * len(clauses)  # true literals in each clause
        self.free = [len(c) for c in clauses]  # unknown literals in each clause
        self.trail = []
        self.quiet = {symbol(grid, c, v) for c, v in enumerate(grid.cells) if v}  # givens are already on the board

    def _log(self, lit: int) -> None:
        """Show the literal on the board: p true is an assignment, p false removes a candidate."""
        cell, value = decode(self.grid, abs(lit))
        if lit > 0 and lit not in self.quiet:
            self.tracer.assign(cell, value)
        elif lit < 0:
            self.tracer.prune(cell, value, "clause")

    def propagate(self, literals: list) -> bool:
        """Set literals and follow every unit clause they create. False on conflict (trail stays for undo)."""
        stack = list(literals)
        while stack:
            lit = stack.pop()
            current = self.value[abs(lit)]
            if current:
                if (current > 0) != (lit > 0):
                    return False
                continue
            self.value[abs(lit)] = 1 if lit > 0 else -1
            self.trail.append(lit)
            self._log(lit)
            conflict = False
            for i in self.occurs.get(lit, ()):
                self.satisfied[i] += 1
            for i in self.occurs.get(-lit, ()):  # finish this loop even on conflict: undo needs the counters whole
                self.tracer.checks += 1  # clause visits, the SAT counterpart of constraint checks
                self.free[i] -= 1
                if not self.satisfied[i]:
                    if self.free[i] == 0:
                        conflict = True
                    elif self.free[i] == 1:
                        stack.append(next(x for x in self.clauses[i] if not self.value[abs(x)]))
            if conflict:
                return False
        return True

    def undo(self, mark: int) -> None:
        while len(self.trail) > mark:
            lit = self.trail.pop()
            self.value[abs(lit)] = 0
            for i in self.occurs.get(lit, ()):
                self.satisfied[i] -= 1
            for i in self.occurs.get(-lit, ()):
                self.free[i] += 1
            if lit > 0 and lit not in self.quiet:
                self.tracer.backtrack(decode(self.grid, lit)[0])

    def pure_literals(self) -> list:
        """Literals whose negation appears in no open clause."""
        open_lits = {x for i, c in enumerate(self.clauses) if not self.satisfied[i] for x in c
                     if not self.value[abs(x)]}
        return [x for x in open_lits if -x not in open_lits]

    def branch_symbol(self) -> int:
        """A symbol from the shortest open clause; 0 when every clause is satisfied."""
        best, size = None, 1 << 30
        for i, free in enumerate(self.free):
            if not self.satisfied[i] and free < size:
                best, size = i, free
        if best is None:
            return 0
        return next(abs(x) for x in self.clauses[best] if not self.value[abs(x)])

    def search(self, literals: list, root: bool = False) -> bool:
        if self.deadline and time.perf_counter() > self.deadline:
            raise TimeoutError
        mark = len(self.trail)
        ok = self.propagate(literals)
        if ok and root:  # shortcut: pure literals only at the root, a scan per node costs more than it saves on Sudoku
            ok = self.propagate(self.pure_literals())
        if ok:
            sym = self.branch_symbol()
            if not sym or self.search([sym]) or self.search([-sym]):
                return True
        self.undo(mark)
        return False


def dpll(clauses: list, grid, tracer=None, timeout=None) -> set | None:
    """Return the true symbols of a model, or None if the clauses are unsatisfiable."""
    if not all(clauses):  # an empty clause is false: a full grid's blocking clause
        return None
    deadline = time.perf_counter() + timeout if timeout else None
    sys.setrecursionlimit(max(sys.getrecursionlimit(), grid.size ** 3 + 100))  # one frame per decision
    solver = _DPLL(clauses, grid.size ** 3, grid, tracer or Tracer(max_events=0), deadline)
    if not solver.search([c[0] for c in clauses if len(c) == 1], root=True):
        return None
    return {sym for sym in range(1, grid.size ** 3 + 1) if solver.value[sym] > 0}


def _solution(grid, model: set) -> dict:
    return dict(decode(grid, sym) for sym in model)


def solve(grid, tracer, timeout=None, limit: int = 1, extended: bool = False):
    """solve_grid() entry for --algo dpll. limit=2 asks for a second model via a blocking clause."""
    clauses = encode(grid, extended)
    found = []
    try:
        model = dpll(clauses, grid, tracer, timeout)
        if model:
            tracer.solved()
            found.append(_solution(grid, model))
            if limit > 1:
                second = dpll(clauses + [blocking_clause(grid, found[0])], grid, None, timeout)
                if second:
                    found.append(_solution(grid, second))
        status = "solved" if found else "unsat"
    except TimeoutError:
        status = "timeout"
    return SolveResult(status, found[0] if found else None, tracer.stats(), tracer, found)


def blocking_clause(grid, solution: dict) -> list:
    """not-s: at least one non-given cell differs from the solution."""
    return [-symbol(grid, cell, solution[cell]) for cell, v in enumerate(grid.cells) if not v]


def is_unique(grid, solution: dict, timeout=None) -> bool:
    """KB entails s iff KB + {not s} is unsatisfiable (Course Vol. 4, p. 31)."""
    return dpll(encode(grid) + [blocking_clause(grid, solution)], grid, None, timeout) is None
