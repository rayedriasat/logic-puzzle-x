"""The JSON API's logic, with no web framework attached.

Two front ends call it: support/server.py (FastAPI, for `python main.py`) and support/web/pyworker.js,
which runs this module in the browser with Pyodide so the site can be hosted as static files.
Bad input raises ApiError; each front end turns that into its own error response.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from . import sat
from .explain import explain
from .generator import generate_sudoku
from .sudoku import Grid, parse, solution_string, solve_grid
from .trace import Tracer

VERSION = "0.1.0"
DATA_DIR = Path(__file__).parents[1] / "data" / "sudoku"
ALGORITHMS = ("bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll")
DIFFICULTIES = ("easy", "medium", "hard", "extreme")
MAX_CHARS = 1024  # a 16x16 grid with spaces fits; anything longer is not a puzzle we can solve in time
RACE_TIMEOUT = 4.0
GENERATE_BUDGET = 25.0
LIVE_SIZES = (4, 6, 9)  # 16x16 takes minutes, so those are generated offline into data/


class ApiError(ValueError):
    """A request the API cannot serve; status is the HTTP status it maps to."""

    def __init__(self, detail: str, status: int = 422):
        super().__init__(detail)
        self.detail, self.status = detail, status


def parse_puzzle(text: str) -> Grid:
    try:
        return parse(text)
    except ValueError as error:
        raise ApiError(str(error)) from error


def run_solver(grid: Grid, algorithm: str, trace: bool, timeout: float) -> tuple:
    tracer = Tracer(max_events=100_000 if trace else 0)
    result = solve_grid(grid, algorithm, tracer, timeout)
    body = {
        "puzzle": {"type": "sudoku", "size": grid.size, "box": grid.box, "grid": str(grid)},
        "algorithm": algorithm,
        "status": result.status,
        "solution": solution_string(result.solution, grid.size) if result.solution else None,
        "stats": result.stats,
        "events": tracer.events,
        "truncated": tracer.truncated,
    }
    return body, result, tracer


def health() -> dict:
    return {"status": "ok", "version": VERSION}


def puzzles(difficulty: str | None = None, size: int | None = None, limit: int = 50) -> list:
    """Sample puzzles from data/: famous ones, the rated sample and generated ones."""
    found = []
    for line in (DATA_DIR / "famous.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            grid, name = line.split()
            found.append({"id": name, "puzzle": grid, "difficulty": "famous", "size": 9})
    if (DATA_DIR / "rated_sample.csv").exists():
        with open(DATA_DIR / "rated_sample.csv", newline="", encoding="utf-8") as f:
            found += [{"id": r["id"], "puzzle": r["puzzle"], "difficulty": r["bucket"], "size": 9}
                      for r in csv.DictReader(f)]
    for path in sorted((DATA_DIR / "generated").glob("*.txt")):
        n = int(path.stem)
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            grid, grade = line.split()
            found.append({"id": f"generated-{n}-{i}", "puzzle": grid, "difficulty": grade, "size": n})
    found = [p for p in found if (not difficulty or p["difficulty"] == difficulty) and (not size or p["size"] == size)]
    return random.sample(found, min(max(limit, 0), len(found)))


def solve(puzzle: str, algorithm: str = "mac", trace: bool = True, explain_steps: bool = False,
          prove: bool = False, timeout: float = 10.0) -> dict:
    grid = parse_puzzle(puzzle)
    body, result, tracer = run_solver(grid, algorithm, trace, timeout)
    if not trace:
        del body["events"]
    if explain_steps and trace:
        body["explanation"] = explain(tracer.events, grid)
    if prove and result.status == "solved":
        try:
            body["unique"] = sat.is_unique(grid, result.solution, timeout)
        except TimeoutError:
            body["unique"] = None
    return body


def race(puzzle: str, algorithms: list[str]) -> dict:
    grid = parse_puzzle(puzzle)
    return {"results": [run_solver(grid, a, True, RACE_TIMEOUT)[0] for a in algorithms]}


def generate(size: int = 9, difficulty: str = "medium", seed: int | None = None) -> dict:
    puzzle, solution, grade = generate_sudoku(size, difficulty, seed, budget=GENERATE_BUDGET)
    return {"type": "sudoku", "size": puzzle.size, "box": puzzle.box, "puzzle": str(puzzle),
            "solution": solution_string(solution, puzzle.size), "grade": grade, "requested": difficulty,
            "clues": sum(1 for v in puzzle.cells if v), "unique": True}


# --- Browser entry point -------------------------------------------------------------------------
# The FastAPI server validates with pydantic; in the browser these checks stand in for it.

def _check(ok: bool, detail: str) -> None:
    if not ok:
        raise ApiError(detail)


def _puzzle_field(body: dict) -> str:
    puzzle = body.get("puzzle")
    _check(isinstance(puzzle, str) and len(puzzle) <= MAX_CHARS, "puzzle must be a string of at most 1024 characters")
    return puzzle


def handle(method: str, url: str, body_json: str | None = None) -> str:
    """Serve one API request given as method, URL path with query, and JSON body; returns
    JSON {"status": http_status, "body": ...}."""
    from urllib.parse import parse_qs, urlsplit

    parts = urlsplit(url)
    query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
    body = json.loads(body_json) if body_json else {}
    try:
        route = (method.upper(), parts.path.rstrip("/"))
        if route == ("GET", "/api/health"):
            out = health()
        elif route == ("GET", "/api/puzzles"):
            out = puzzles(query.get("difficulty") or None, int(query["size"]) if query.get("size") else None,
                          int(query.get("limit", 50)))
        elif route == ("POST", "/api/solve"):
            algorithm, timeout = body.get("algorithm", "mac"), body.get("timeout", 10.0)
            _check(algorithm in ALGORITHMS, f"unknown algorithm: {algorithm}")
            _check(isinstance(timeout, (int, float)) and 0 < timeout <= 30, "timeout must be in (0, 30] seconds")
            out = solve(_puzzle_field(body), algorithm, bool(body.get("trace", True)), bool(body.get("explain", False)),
                        bool(body.get("prove", False)), float(timeout))
        elif route == ("POST", "/api/race"):
            algorithms = body.get("algorithms")
            _check(isinstance(algorithms, list) and 1 <= len(algorithms) <= 4 and all(a in ALGORITHMS for a in algorithms),
                   "algorithms must list 1 to 4 known algorithm ids")
            out = race(_puzzle_field(body), algorithms)
        elif route == ("POST", "/api/generate"):
            size, difficulty, seed = body.get("size", 9), body.get("difficulty", "medium"), body.get("seed")
            _check(size in LIVE_SIZES, "size must be 4, 6 or 9")
            _check(difficulty in DIFFICULTIES, f"unknown difficulty: {difficulty}")
            out = generate(size, difficulty, seed)
        else:
            raise ApiError("Not Found", 404)
        return json.dumps({"status": 200, "body": out})
    except ApiError as error:
        return json.dumps({"status": error.status, "body": {"detail": error.detail}})
