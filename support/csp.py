"""Factor-graph CSP model: variables, domains, factors and weight(x).

Course link: Vol. 3, factor graphs and CSPs (scope, arity, weight, dependent factors D(x, X_i)).
Owner: Member A. Phase 1 (plan.md sections 3.3 and 6).

Planned API:
    Factor(scope, predicate, name)   .is_satisfied(assignment) -> bool   .revise(domains) -> removals
    CSP(variables, domains, factors) .weight(assignment) -> 0 | 1         .dependent_factors(assignment, var)
"""
"""Factor-graph CSP model: variables, domains, factors and weight(x).

Course link: Vol. 3, factor graphs and CSPs (scope, arity, weight, dependent factors D(x, X_i)).
Owner: Member A. Phase 1 (plan.md sections 3.3 and 6).

API:
    Factor(scope, predicate, name)   .is_satisfied(assignment) -> bool   .revise(domains) -> removals
    CSP(domains, factors)            .weight(assignment) -> 0 | 1        .dependent_factors(assignment, var)
Variables are integer indexes 0..n-1 (the same ids the trace events use). Domains are lists of sets.
"""
from __future__ import annotations

from itertools import product
from typing import Callable


class Factor:
    """f_j(x) in {0, 1}. `predicate` receives the values of `scope` in scope order."""

    def __init__(self, scope, predicate: Callable[..., bool], name: str = "factor"):
        self.scope = tuple(scope)
        self.predicate = predicate
        self.name = name

    @property
    def arity(self) -> int:
        return len(self.scope)

    def is_satisfied(self, assignment: dict) -> bool:
        """`assignment` must hold a value for every variable in the scope."""
        return bool(self.predicate(*(assignment[v] for v in self.scope)))

    def revise(self, domains: list) -> list:
        """Remove values with no support (in place). Returns the removed (var, value) pairs.

        Generic version: keep a value only if some combination of the other
        scope domains satisfies the factor. Subclasses override it with faster rules.
        """
        removed = []
        for var in self.scope:
            others = [u for u in self.scope if u != var]
            for val in list(domains[var]):
                if not self._has_support(var, val, others, domains):
                    domains[var].discard(val)
                    removed.append((var, val))
        return removed

    def _has_support(self, var, val, others, domains) -> bool:
        for combo in product(*(domains[u] for u in others)):
            a = dict(zip(others, combo))
            a[var] = val
            if self.is_satisfied(a):
                return True
        return False

    def __repr__(self) -> str:
        return f"{self.name}{self.scope}"


class NotEqual(Factor):
    """Binary factor [X_a != X_b]."""

    def __init__(self, a: int, b: int):
        super().__init__((a, b), lambda x, y: x != y, "neq")

    def revise(self, domains: list) -> list:
        a, b = self.scope
        removed = []
        for u, w in ((a, b), (b, a)):
            if len(domains[u]) == 1:
                (v,) = tuple(domains[u])
                if v in domains[w]:
                    domains[w].discard(v)
                    removed.append((w, v))
        return removed


class AllDifferent(Factor):
    """Global factor: all variables in the scope take distinct values."""

    def __init__(self, scope, name: str = "alldiff"):
        super().__init__(scope, lambda *vals: len(set(vals)) == len(vals), name)

    def revise(self, domains: list) -> list:
        """Singleton elimination, repeated until nothing changes."""
        removed = []
        changed = True
        while changed:
            changed = False
            for u in self.scope:
                if len(domains[u]) == 1:
                    (v,) = tuple(domains[u])
                    for w in self.scope:
                        if w != u and v in domains[w]:
                            domains[w].discard(v)
                            removed.append((w, v))
                            changed = True
        return removed


class CSP:
    """Variables 0..n-1, their initial domains, and a list of factors."""

    def __init__(self, domains, factors, names=None):
        self.n = len(domains)
        self.domains = [set(d) for d in domains]
        self.factors = list(factors)
        self.names = list(names) if names else [f"X{i}" for i in range(self.n)]
        self.factors_of = [[] for _ in range(self.n)]    # factors whose scope contains X_i
        self.neighbors = [set() for _ in range(self.n)]  # Markov blanket of X_i
        for f in self.factors:
            for v in f.scope:
                self.factors_of[v].append(f)
                self.neighbors[v].update(u for u in f.scope if u != v)
        self.checks = 0                                  # constraint-check counter for stats

    def copy_domains(self) -> list:
        return [set(d) for d in self.domains]

    def condition(self, var: int, value) -> None:
        """Fix a given: X_var = value. Its domain becomes a singleton."""
        self.domains[var] = {value}

    def weight(self, assignment: dict) -> int:
        """prod f_j(x) over factors whose scope is fully assigned (exact weight for a full x)."""
        for f in self.factors:
            if all(v in assignment for v in f.scope):
                self.checks += 1
                if not f.is_satisfied(assignment):
                    return 0
        return 1

    def is_consistent(self, assignment: dict) -> bool:
        return self.weight(assignment) == 1

    def dependent_factors(self, assignment: dict, var: int) -> list:
        """D(x, X_i): factors containing X_i whose other variables are all assigned."""
        return [f for f in self.factors_of[var]
                if all(u == var or u in assignment for u in f.scope)]

    def delta(self, assignment: dict, var: int, value) -> int:
        """delta = prod over D(x, X_i) of f(x U {X_i: v}). 1 means the value is allowed."""
        new = {**assignment, var: value}
        for f in self.dependent_factors(assignment, var):
            self.checks += 1
            if not f.is_satisfied(new):
                return 0
        return 1