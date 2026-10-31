"""Search event recorder and statistics (the data the UI replays).

Events: ["A", var, value] assign · ["P", var, value, reason] prune · ["B", var] backtrack · ["S"] solved.
The UI undoes every prune made since the matching "A" when it replays a "B" (plan.md section 3.6).
"""
from __future__ import annotations

import time


class Tracer:
    """Counts search effort and logs up to `max_events` events (0 = count only, for benchmarks)."""

    def __init__(self, max_events: int = 100_000):
        self.max_events = max_events
        self.events: list = []
        self.truncated = False
        self.nodes = self.backtracks = self.prunes = self.checks = 0
        self._start = time.perf_counter()

    def _log(self, event: list) -> None:
        if len(self.events) < self.max_events:
            self.events.append(event)
        elif self.max_events:
            self.truncated = True

    def assign(self, var: int, value) -> None:
        self.nodes += 1
        self._log(["A", var, value])

    def prune(self, var: int, value, reason: str) -> None:
        self.prunes += 1
        self._log(["P", var, value, reason])

    def backtrack(self, var: int) -> None:
        self.backtracks += 1
        self._log(["B", var])

    def solved(self) -> None:
        self._log(["S"])

    def stats(self) -> dict:
        return {"nodes": self.nodes, "backtracks": self.backtracks, "checks": self.checks, "prunes": self.prunes,
                "ms": round((time.perf_counter() - self._start) * 1000, 3)}
