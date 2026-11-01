"""Plain-English deductions."""
from support.explain import explain
from support.sudoku import parse, solve_grid
from support.trace import Tracer

EASY = "..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3.."
HARD = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."


def steps_for(text: str, algorithm: str) -> list:
    grid = parse(text)
    tracer = Tracer()
    solve_grid(grid, algorithm, tracer, timeout=30)
    return explain(tracer.events, grid)


def test_propagation_makes_every_step_a_naked_single_on_an_easy_puzzle():
    assert {s["kind"] for s in steps_for(EASY, "mac")} == {"naked"}


def test_naive_backtracking_has_nothing_to_cite():
    assert {s["kind"] for s in steps_for(EASY, "bt")} == {"guess", "backtrack"}


def test_hidden_single_names_its_unit():
    hidden = [s for s in steps_for(HARD, "mac+") if s["kind"] == "hidden"]
    assert hidden
    assert any(word in hidden[0]["text"] for word in ("row", "col", "box"))
    assert "can still hold" in hidden[0]["text"]


def test_steps_point_at_their_events():
    grid = parse(HARD)
    tracer = Tracer()
    solve_grid(grid, "mac", tracer)
    for step in explain(tracer.events, grid):
        event = tracer.events[step["event"]]
        assert event[0] == ("B" if step["kind"] == "backtrack" else "A")
        assert event[1] == step["var"]


def test_16x16_digits_print_as_letters():
    assert any("= G" in s["text"] for s in steps_for("." * 256, "mac+"))
