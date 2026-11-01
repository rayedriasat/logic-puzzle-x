"""Backtracking search over partial assignments, with pluggable heuristics.

Course link: Vol. 1 backtracking / DFS; Vol. 3 CSP algorithm pseudocode (Backtrack(x, Domains), delta, lookahead).
One recursive search; each --algo id only picks a variable order, a value order and an inference step.
`nodes` counts assignments that passed the delta check (search-tree nodes, one "A" event each).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .propagation import ac3, forward_check, global_propagate
from .trace import Tracer


def _static(csp, x, domains):
    return next(v for v in range(csp.n) if v not in x)


def _mrv(csp, x, domains):
    """Fail-first: smallest domain, ties broken by most unassigned neighbors (degree)."""
    free = [v for v in range(csp.n) if v not in x]
    size = min(len(domains[v]) for v in free)
    ties = [v for v in free if len(domains[v]) == size]
    return max(ties, key=lambda v: sum(u not in x for u in csp.neighbors[v]))


def _ascending(csp, x, domains, var):
    return sorted(domains[var])


def _lcv(csp, x, domains, var):
    """Try first the value that rules out the fewest options for unassigned neighbors."""
    free = [u for u in csp.neighbors[var] if u not in x]
    return sorted(domains[var], key=lambda value: (sum(value in domains[u] for u in free), value))


def _no_inference(csp, domains, var, tracer):
    return True


def _mac(csp, domains, var, tracer):
    return ac3(csp, domains, tracer, csp.factors_of[var])


def _mac_plus(csp, domains, var, tracer):
    return global_propagate(csp, domains, tracer, csp.factors_of[var])


# id -> (variable order, value order, inference after each assignment); plan.md section 3.4
ALGORITHMS = {
    "bt": (_static, _ascending, _no_inference),
    "fc": (_static, _ascending, forward_check),
    "mrv": (_mrv, _ascending, forward_check),
    "lcv": (_mrv, _lcv, forward_check),
    "mac": (_mrv, _lcv, _mac),
    "mac+": (_mrv, _lcv, _mac_plus),
}


@dataclass
class SolveResult:
    status: str                        # "solved" | "unsat" | "timeout"
    solution: dict | None
    stats: dict
    tracer: Tracer
    solutions: list = field(default_factory=list)  # up to `limit` solutions


class _Timeout(Exception):
    pass


def solve(csp, algorithm: str = "mac", tracer=None, timeout=None, limit: int = 1, rng=None) -> SolveResult:
    """Find up to `limit` solutions (limit=2 decides uniqueness). `rng` shuffles value order for the generator."""
    choose, order, infer = ALGORITHMS[algorithm]
    tracer = tracer or Tracer(max_events=0)
    deadline = time.perf_counter() + timeout if timeout else None
    csp.checks = 0
    found = []

    def backtrack(x, domains):
        if len(x) == csp.n:
            found.append(dict(x))
            tracer.solved()
            return len(found) >= limit
        if deadline and time.perf_counter() > deadline:
            raise _Timeout
        var = choose(csp, x, domains)
        values = order(csp, x, domains, var)
        if rng:
            rng.shuffle(values)
        for value in values:
            if not csp.delta(x, var, value):
                continue
            tracer.assign(var, value)
            x[var] = value
            pruned = [set(d) for d in domains]  # Domains' in the class pseudocode
            pruned[var] = {value}
            if infer(csp, pruned, var, tracer) and backtrack(x, pruned):
                return True
            del x[var]
            tracer.backtrack(var)
        return False

    x = dict(csp.given)
    domains = csp.copy_domains()
    status = "unsat"
    try:
        if csp.is_consistent(x) and _propagate_givens(csp, domains, x, algorithm, tracer):
            backtrack(x, domains)
        status = "solved" if found else "unsat"
    except _Timeout:
        status = "timeout"  # also when limit=2 found one: a second solution was not ruled out
    tracer.checks = csp.checks
    return SolveResult(status, found[0] if found else None, tracer.stats(), tracer, found)


def _propagate_givens(csp, domains, x, algorithm, tracer) -> bool:
    """Root node: the same inference as the search, applied to the conditioned givens."""
    if algorithm == "bt":
        return True
    if algorithm == "mac":
        return ac3(csp, domains, tracer)
    if algorithm == "mac+":
        return global_propagate(csp, domains, tracer)
    return all(forward_check(csp, domains, var, tracer) for var in x)
