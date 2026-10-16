"""Search event recorder and statistics (the data the UI replays).

Events: ["A", var, value] assign · ["P", var, value, reason] prune · ["B", var] backtrack · ["S"] solved.
Owner: Member A. Phase 1; format in plan.md section 3.6 (cap of ~100k events, then `truncated`).

Planned API:
    Tracer(max_events=100_000)  .assign() .prune() .backtrack() .solved()  .stats  .to_json()
"""
