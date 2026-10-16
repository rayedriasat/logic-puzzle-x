"""Sudoku <-> CSP for any box size (4x4, 6x6, 9x9, 16x16).

9x9: 81 variables, 810 binary "not equal" factors; each cell's 20 peers form its Markov blanket.
Givens are applied by conditioning (Vol. 3). Owner: Member B. Phase 1; plan.md section 3.5.

Planned API:
    parse(text, box=(3, 3)) -> Grid     to_csp(grid, global_alldiff=False) -> CSP
    peers(cell) -> set[int]             format_grid(values) -> str
"""
