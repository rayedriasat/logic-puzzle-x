"""Generate puzzles with exactly one solution and grade their difficulty.

Fill a random complete grid, remove clues while the solution stays unique (solver with limit=2),
then grade by the search effort needed. Owner: Member B. Phase 3.

Planned API:
    generate_sudoku(size=9, difficulty="medium", seed=None) -> (puzzle, solution, grade)
    generate_kakuro(rows, cols, seed=None) -> (puzzle, solution)
"""
