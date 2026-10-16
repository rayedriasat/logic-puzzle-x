"""Factor-graph CSP model: variables, domains, factors and weight(x).

Course link: Vol. 3, factor graphs and CSPs (scope, arity, weight, dependent factors D(x, X_i)).
Owner: Member A. Phase 1 (plan.md sections 3.3 and 6).

Planned API:
    Factor(scope, predicate, name)   .is_satisfied(assignment) -> bool   .revise(domains) -> removals
    CSP(variables, domains, factors) .weight(assignment) -> 0 | 1         .dependent_factors(assignment, var)
"""
