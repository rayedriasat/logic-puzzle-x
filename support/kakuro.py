"""Kakuro <-> CSP: every run of white cells gets a sum factor and pairwise "not equal" factors.

Text format: "#" black, "." white, "D\\R" clue (down-sum D, right-sum R, "-" if absent).
Owner: Member B. Phase 2; plan.md section 3.5.

Planned API:
    parse(text) -> KakuroGrid    to_csp(grid) -> CSP    SumFactor.revise() uses precomputed digit combinations
"""
