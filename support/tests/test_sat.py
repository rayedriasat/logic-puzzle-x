"""CNF encoding, DPLL and uniqueness by entailment."""
from support import sat
from support.sudoku import parse, solve_grid

EULER = "..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3.."
ESCARGOT = "1....7.9..3..2...8..96..5....53..9...1..8...26....4...3......1..4......7..7...3.."


def test_clause_counts_match_the_plan():
    empty = parse("." * 81)
    # 81 at-least-one + 81*36 at-most-one per cell + 27 units * 9 values * 36 pairs
    assert len(sat.encode(empty)) == 81 + 81 * 36 + 27 * 9 * 36 == 11745
    assert len(sat.encode(empty, extended=True)) == 11745 + 27 * 9


def test_givens_become_unit_clauses():
    grid = parse(EULER)
    units = [c for c in sat.encode(grid) if len(c) == 1]
    assert len(units) == sum(1 for v in grid.cells if v)


def test_symbols_are_numbered_from_one_and_round_trip():
    grid = parse("." * 81)
    assert sat.symbol(grid, 0, 1) == 1
    assert sat.symbol(grid, 80, 9) == 729
    assert sat.decode(grid, sat.symbol(grid, 40, 7)) == (40, 7)


def test_dpll_model_is_a_valid_solution():
    grid = parse(ESCARGOT)
    clauses = sat.encode(grid)
    model = sat.dpll(clauses, grid)
    assert all(any((lit > 0) == (abs(lit) in model) for lit in clause) for clause in clauses)
    assert len(model) == 81


def test_dpll_detects_contradiction():
    assert sat.dpll(sat.encode(parse("55" + "." * 79)), parse("55" + "." * 79)) is None


def test_extended_encoding_gives_the_same_solution():
    grid = parse(EULER)
    assert sat.solve(grid, _tracer(), extended=True).solution == sat.solve(grid, _tracer()).solution


def test_unique_puzzle_is_entailed():
    grid = parse(EULER)
    assert sat.is_unique(grid, solve_grid(grid, "mac").solution)


def test_puzzle_with_many_solutions_is_not_entailed():
    grid = parse("." * 16)
    assert not sat.is_unique(grid, solve_grid(grid, "mac").solution)


def test_a_full_grid_is_trivially_unique():
    grid = parse("1234341221434321")
    assert sat.is_unique(grid, solve_grid(grid, "mac").solution)


def _tracer():
    from support.trace import Tracer
    return Tracer(max_events=0)
