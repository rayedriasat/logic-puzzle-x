"""FastAPI app: JSON API for the solver plus the static web UI in support/web/.

Routes follow plan.md section 3.7. Solving runs in FastAPI's thread pool, always under a timeout.
"""
import csv
import random
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import benchmark, sat
from .explain import explain
from .generator import GRADES, generate_sudoku
from .sudoku import Grid, box_shape, parse, solution_string, solve_grid
from .trace import Tracer

WEB_DIR = Path(__file__).parent / "web"
DATA_DIR = Path(__file__).parents[1] / "data" / "sudoku"
MAX_CHARS = 1024  # a 16x16 grid with spaces fits; anything longer is not a puzzle we can solve in time
RACE_TIMEOUT = 4.0
GENERATE_BUDGET = 25.0

Algorithm = Literal["bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll"]

app = FastAPI(title="LogicPuzzleX", version="0.1.0")


class SolveRequest(BaseModel):
    type: Literal["sudoku"] = "sudoku"
    puzzle: str = Field(max_length=MAX_CHARS)
    algorithm: Algorithm = "mac"
    trace: bool = True
    explain: bool = False
    prove: bool = False  # also prove uniqueness by entailment
    timeout: float = Field(default=10.0, gt=0, le=30)


class RaceRequest(BaseModel):
    type: Literal["sudoku"] = "sudoku"
    puzzle: str = Field(max_length=MAX_CHARS)
    algorithms: list[Algorithm] = Field(min_length=1, max_length=4)


class GenerateRequest(BaseModel):
    type: Literal["sudoku"] = "sudoku"
    size: Literal[4, 6, 9] = 9  # 16x16 takes minutes, so those are generated offline into data/
    difficulty: Literal["easy", "medium", "hard", "extreme"] = "medium"
    seed: int | None = None


def _parse(text: str) -> Grid:
    try:
        return parse(text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _solve(grid: Grid, algorithm: str, trace: bool, timeout: float) -> tuple:
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


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/api/puzzles")
def puzzles(type: Literal["sudoku"] = "sudoku", difficulty: str | None = None, size: int | None = None,
            limit: int = 50) -> list:
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


@app.post("/api/solve")
def solve(request: SolveRequest) -> dict:
    grid = _parse(request.puzzle)
    body, result, tracer = _solve(grid, request.algorithm, request.trace, request.timeout)
    if not request.trace:
        del body["events"]
    if request.explain and request.trace:
        body["explanation"] = explain(tracer.events, grid)
    if request.prove and result.status == "solved":
        try:
            body["unique"] = sat.is_unique(grid, result.solution, request.timeout)
        except TimeoutError:
            body["unique"] = None
    return body


@app.post("/api/race")
def race(request: RaceRequest) -> dict:
    grid = _parse(request.puzzle)
    return {"results": [_solve(grid, a, True, RACE_TIMEOUT)[0] for a in request.algorithms]}


@app.post("/api/generate")
def generate(request: GenerateRequest) -> dict:
    puzzle, solution, grade = generate_sudoku(request.size, request.difficulty, request.seed, budget=GENERATE_BUDGET)
    return {"type": "sudoku", "size": puzzle.size, "box": puzzle.box, "puzzle": str(puzzle),
            "solution": solution_string(solution, puzzle.size), "grade": grade, "requested": request.difficulty,
            "clues": sum(1 for v in puzzle.cells if v), "unique": True}


@app.get("/api/benchmarks")
def benchmarks() -> dict:
    return benchmark.summary()


# Mounted last so the /api routes above take priority over static files.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
