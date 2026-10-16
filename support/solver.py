"""Backtracking search over partial assignments, with pluggable heuristics.

Course link: Vol. 1 backtracking / DFS; Vol. 3 CSP algorithm pseudocode.
Owner: Member A. Phase 1 (bt, fc, mrv) and Phase 2 (lcv, mac, mac+); plan.md section 3.4.

Planned API:
    solve(csp, algorithm="mac", tracer=None, timeout=None, limit=1) -> SolveResult
        algorithm in {"bt", "fc", "mrv", "lcv", "mac", "mac+"}; limit=2 counts solutions for uniqueness.
"""
