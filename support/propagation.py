"""Constraint propagation: forward checking, AC-3 / MAC and the hidden-single rule.

Course link: Vol. 3, "update domains of unassigned variables" step of the CSP pseudocode.
Owner: Member B. Phase 1 (forward checking) and Phase 2 (AC-3, MAC, hidden singles).

Planned API:
    forward_check(csp, domains, var, value, tracer) -> bool   # False = a domain became empty
    ac3(csp, domains, queue=None, tracer=None) -> bool
"""
