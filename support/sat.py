"""Propositional track: Sudoku -> CNF, a DPLL solver and uniqueness by entailment.

Course link: Vol. 4, CNF, satisfiability, resolution; KB entails s iff KB + {not s} is unsatisfiable.
Owner: Member C. Phase 2; plan.md section 3.5.

Planned API:
    encode(grid) -> (clauses, symbol_map)    dpll(clauses, tracer=None) -> model | None
    is_unique(grid, solution) -> bool
"""
