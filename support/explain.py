"""Turn solver events into human-readable deductions (naked single, hidden single, guess, backtrack).

Course link: Vol. 4, inference rules and derivations (KB |- f).
Replays the event log with the same frame rule as the UI: a "B" undoes every prune since its "A".
"""
from __future__ import annotations

from .sudoku import DIGITS, Grid


def explain(events: list, grid: Grid) -> list:
    """One {"event", "kind", "var", "value", "text"} per assignment or backtrack; kind is naked|hidden|guess|backtrack."""
    n = grid.size
    domains = [{v} if v else set(range(1, n + 1)) for v in grid.cells]
    filled = {cell: v for cell, v in enumerate(grid.cells) if v}
    frames = [[]]   # frames[-1] holds the prunes to restore when the current assignment is undone
    hidden = {}     # var -> unit named by a hidden-single prune
    steps = []
    name = lambda var: f"r{var // n + 1}c{var % n + 1}"

    for i, event in enumerate(events):
        kind = event[0]
        if kind == "P":
            var, value, reason = event[1:]
            if value in domains[var]:
                domains[var].discard(value)
                frames[-1].append((var, value))
            if reason.startswith("hidden "):
                hidden[var] = reason[len("hidden "):]
        elif kind == "A":
            var, value = event[1:]
            rule, unit = _classify(var, value, domains, filled, grid, hidden)
            digit = DIGITS[value - 1]
            text = {
                "naked": f"{name(var)} = {digit}: every other digit is ruled out for this cell",
                "hidden": f"{name(var)} = {digit}: it is the only cell in {unit} that can still hold a {digit}",
                "guess": f"{name(var)} = {digit}: nothing forces this cell, so the solver tries a value",
            }[rule]
            steps.append({"event": i, "kind": rule, "var": var, "value": value, "text": text})
            filled[var] = value
            frames.append([])
        elif kind == "B":
            var = event[1]
            value = filled.pop(var)
            for u, pruned in frames.pop():
                domains[u].add(pruned)
                hidden.pop(u, None)  # the hidden-single reasoning went with the prune
            digit = DIGITS[value - 1]
            steps.append({"event": i, "kind": "backtrack", "var": var, "value": value,
                          "text": f"{name(var)} = {digit} led to a dead end: undo it and everything it caused"})
    return steps


def _classify(var, value, domains, filled, grid, hidden) -> tuple:
    if var in hidden:
        return "hidden", hidden[var]
    if len(domains[var]) == 1:
        return "naked", None
    if len(domains[var]) < grid.size:  # no propagation ran (bt) means full domains and no rule to cite
        for unit_name, unit in grid.units:
            if var in unit and not any(value in domains[u] for u in unit if u != var and u not in filled):
                return "hidden", unit_name
    return "guess", None
