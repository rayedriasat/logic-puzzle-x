"""Constraint propagation: forward checking, AC-3 / MAC and the hidden-single rule.

Course link: Vol. 3, "update domains of unassigned variables" step of the CSP pseudocode.
All functions shrink `domains` in place, log prunes on `tracer`, and return False on an empty domain.
"""
from __future__ import annotations


def _revise(csp, f, domains, tracer) -> list:
    csp.checks += 1
    removed = f.revise(domains)
    for var, value in removed:
        tracer.prune(var, value, f.name)
    return removed


def forward_check(csp, domains: list, var: int, tracer) -> bool:
    """Prune only the factors touching the variable just assigned (domains[var] is a singleton)."""
    for f in csp.factors_of[var]:
        for u, _ in _revise(csp, f, domains, tracer):
            if not domains[u]:
                return False
    return True


def ac3(csp, domains: list, tracer, queue=None) -> bool:
    """AC-3: revise factors until a fixed point, re-queueing the factors of every shrunken variable."""
    queue = list(csp.factors if queue is None else queue)
    queued = set(map(id, queue))
    while queue:
        f = queue.pop()
        queued.discard(id(f))
        for u, _ in _revise(csp, f, domains, tracer):
            if not domains[u]:
                return False
            for g in csp.factors_of[u]:
                if id(g) not in queued and (len(domains[u]) == 1 or not g.singleton_only):
                    queued.add(id(g))
                    queue.append(g)
    return True


def hidden_singles(csp, domains: list, tracer) -> set | None:
    """A value with one possible cell in a permutation factor must go there.

    Returns the variables that were narrowed, or None when a value has no cell left.
    """
    changed = set()
    for f in csp.factors:
        if not getattr(f, "permutation", False):
            continue
        places = {}
        for u in f.scope:
            for value in domains[u]:
                places.setdefault(value, []).append(u)
        if len(places) < len(f.scope):
            return None
        for value, cells in places.items():
            if len(cells) == 1 and len(domains[cells[0]]) > 1:
                u = cells[0]
                for other in domains[u] - {value}:
                    tracer.prune(u, other, f"hidden {f.name}")
                domains[u] = {value}
                changed.add(u)
    return changed


def global_propagate(csp, domains: list, tracer, queue=None) -> bool:
    """mac+: AC-3 and hidden singles, alternating until neither finds anything new."""
    while True:
        if not ac3(csp, domains, tracer, queue):
            return False
        changed = hidden_singles(csp, domains, tracer)
        if changed is None:
            return False
        if not changed:
            return True
        queue = [f for u in changed for f in csp.factors_of[u]]
