"""Sudoku encoding for every box size."""
import pytest

from support.sudoku import format_grid, parse, peers, solution_string, solve_grid, to_csp, units

EMPTY_9 = "." * 81
FOUR = "1...  ..2.  .3..  ...4"
SIX = "1.....  ...2..  ..3...  ....4.  .5....  .....6"


def test_parse_accepts_dots_zeros_and_whitespace():
    assert parse("1.0.\n....\n....\n...4").cells[:4] == (1, 0, 0, 0)


@pytest.mark.parametrize("text, size, box", [("." * 16, 4, (2, 2)), ("." * 36, 6, (2, 3)), (EMPTY_9, 9, (3, 3)),
                                             ("." * 256, 16, (4, 4))])
def test_parse_infers_size_and_box(text, size, box):
    grid = parse(text)
    assert (grid.size, grid.box) == (size, box)


@pytest.mark.parametrize("text", ["", "123", "." * 80, "x" + "." * 80, "G" + "." * 15, "." * 676])
def test_parse_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse(text)


def test_parse_rejects_a_box_that_does_not_fit():
    with pytest.raises(ValueError):
        parse(EMPTY_9, box=(2, 3))


def test_9x9_model_size_matches_the_plan():
    csp = to_csp(parse(EMPTY_9))
    assert csp.n == 81
    assert len(csp.factors) == 810
    assert all(len(neighbors) == 20 for neighbors in csp.neighbors)


def test_global_model_has_27_alldifferent_factors():
    csp = to_csp(parse(EMPTY_9), global_alldiff=True)
    assert len(csp.factors) == 27
    assert all(f.arity == 9 and f.permutation for f in csp.factors)
    assert all(len(neighbors) == 20 for neighbors in csp.neighbors)


def test_peers_is_the_markov_blanket():
    assert len(peers(40)) == 20
    assert {39, 41, 31, 49, 30} <= peers(40)
    assert 40 not in peers(40)
    assert len(peers(0, 4)) == 7
    assert len(peers(0, 6)) == 5 + 5 + 2


def test_units_partition_each_6x6_box_shape():
    boxes = [cells for name, cells in units(6, (2, 3)) if name.startswith("box")]
    assert len(boxes) == 6
    assert sorted(c for box in boxes for c in box) == list(range(36))
    assert boxes[0] == (0, 1, 2, 6, 7, 8)


def test_givens_are_conditioned():
    csp = to_csp(parse("1" + "." * 15))
    assert csp.domains[0] == {1}
    assert csp.given == {0: 1}


def test_factor_names_identify_the_unit():
    csp = to_csp(parse(EMPTY_9))
    assert {f.name.split()[0] for f in csp.factors} == {"row", "col", "box"}


@pytest.mark.parametrize("text", [FOUR, SIX])
def test_small_grids_solve_and_keep_their_givens(text):
    grid = parse(text)
    result = solve_grid(grid, "mac")
    assert result.status == "solved"
    assert all(result.solution[i] == v for i, v in enumerate(grid.cells) if v)


def test_16x16_solves_with_letter_digits():
    solution = solution_string(solve_grid(parse("." * 256), "mac+").solution, 16)
    assert set(solution) == set("123456789ABCDEFG")


def test_solution_string_round_trips_through_parse():
    text = solution_string(solve_grid(parse(EMPTY_9), "mac").solution, 9)
    assert str(parse(text)) == text


def test_format_grid_draws_box_lines():
    lines = format_grid("1234341221434321").splitlines()
    assert lines[0] == "1 2 | 3 4"
    assert set(lines[2]) == {"-"}
