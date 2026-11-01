"""The trace contract the UI depends on: replaying events by the frame rule rebuilds the search."""
import pytest

from support.sudoku import parse, solve_grid
from support.trace import Tracer

ESCARGOT = "1....7.9..3..2...8..96..5....53..9...1..8...26....4...3......1..4......7..7...3.."


def replay(grid, events) -> tuple:
    """Python twin of Replay in web/replay.js: "B" undoes every prune since its "A"."""
    n = grid.size
    values = list(grid.cells)
    domains = [set(range(1, n + 1)) if not v else set() for v in grid.cells]
    frames = [[]]
    for event in events:
        if event[0] == "A":
            _, var, value = event
            assert values[var] == 0, "assigned an occupied cell"
            values[var] = value
            frames.append([])
        elif event[0] == "P":
            _, var, value, _ = event
            if value in domains[var]:
                domains[var].discard(value)
                frames[-1].append((var, value))
        elif event[0] == "B":
            assert values[event[1]] != 0, "backtracked an empty cell"
            values[event[1]] = 0
            for var, value in frames.pop():
                domains[var].add(value)
    return values, domains, frames


@pytest.mark.parametrize("algorithm", ["bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll"])
def test_replaying_the_trace_lands_on_the_solution(algorithm):
    grid = parse(ESCARGOT)
    tracer = Tracer(max_events=10_000_000)
    result = solve_grid(grid, algorithm, tracer, timeout=60)
    values, domains, frames = replay(grid, tracer.events)
    assert values == [result.solution[i] for i in range(81)]
    assert len(frames) == 1 + sum(1 for v in grid.cells if not v)
    if algorithm != "bt":  # the winning value was never pruned from its own cell
        assert all(result.solution[i] in domains[i] for i in range(81) if not grid.cells[i])


@pytest.mark.parametrize("algorithm", ["mrv", "mac+", "dpll"])
def test_a_failed_puzzle_undoes_every_assignment(algorithm):
    grid = parse("12345678." + "........9" + "." * 63)
    tracer = Tracer()
    assert solve_grid(grid, algorithm, tracer, timeout=30).status == "unsat"
    values, _, frames = replay(grid, tracer.events)
    assert list(values) == list(grid.cells)
    assert len(frames) == 1


def test_event_cap_truncates_but_keeps_counting():
    tracer = Tracer(max_events=10)
    for _ in range(25):
        tracer.assign(0, 1)
    assert len(tracer.events) == 10
    assert tracer.truncated
    assert tracer.stats()["nodes"] == 25


def test_max_events_zero_records_nothing_and_is_not_truncated():
    tracer = Tracer(max_events=0)
    tracer.assign(0, 1)
    assert tracer.events == [] and not tracer.truncated
