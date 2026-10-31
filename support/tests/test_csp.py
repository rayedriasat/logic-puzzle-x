"""The factor-graph model and the class's Australia map-coloring example."""
import pytest

from support.csp import CSP, AllDifferent, Factor, NotEqual
from support.solver import ALGORITHMS, solve

REGIONS = ["WA", "NT", "SA", "Q", "NSW", "V", "T"]
BORDERS = [("WA", "NT"), ("WA", "SA"), ("NT", "SA"), ("NT", "Q"), ("SA", "Q"), ("SA", "NSW"), ("SA", "V"),
           ("Q", "NSW"), ("NSW", "V")]


def australia() -> CSP:
    index = {r: i for i, r in enumerate(REGIONS)}
    return CSP([{"red", "green", "blue"}] * 7, [NotEqual(index[a], index[b]) for a, b in BORDERS], REGIONS)


def test_factor_arity_and_scope():
    assert NotEqual(0, 1).arity == 2
    assert AllDifferent((0, 1, 2)).arity == 3


def test_weight_is_the_product_of_factors():
    csp = australia()
    assert csp.weight({0: "red", 1: "green", 2: "blue"}) == 1
    assert csp.weight({0: "red", 1: "red"}) == 0


def test_dependent_factors_need_every_other_variable_assigned():
    csp = australia()
    sa = REGIONS.index("SA")
    assert {f.scope for f in csp.dependent_factors({0: "red"}, sa)} == {(0, sa)}


def test_delta_checks_only_dependent_factors():
    csp = australia()
    assert csp.delta({0: "red"}, 1, "green") == 1
    assert csp.delta({0: "red"}, 1, "red") == 0


def test_markov_blanket_of_south_australia():
    sa = REGIONS.index("SA")
    assert {REGIONS[i] for i in australia().neighbors[sa]} == {"WA", "NT", "Q", "NSW", "V"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_australia_has_18_colorings(algorithm):
    # SA and its ring fix the mainland to 6 colorings; Tasmania is free, 6 x 3 = 18
    result = solve(australia(), algorithm, limit=100)
    assert result.status == "solved"
    assert len(result.solutions) == 18
    assert all(australia().weight(x) == 1 for x in result.solutions)


def test_two_colors_are_not_enough():
    csp = australia()
    csp.domains = [{"red", "green"} for _ in csp.domains]
    assert solve(csp, "mac").status == "unsat"


def test_generic_revise_drops_values_without_support():
    domains = [{1, 2, 3}, {1}]
    removed = Factor((0, 1), lambda x, y: x > y).revise(domains)
    assert domains[0] == {2, 3} and removed == [(0, 1)]


def test_not_equal_revise_prunes_only_from_singletons():
    domains = [{1}, {1, 2}, {2, 3}]
    assert NotEqual(0, 1).revise(domains) == [(1, 1)]
    assert NotEqual(1, 2).revise(domains) == [(2, 2)]
    assert domains == [{1}, {2}, {3}]
