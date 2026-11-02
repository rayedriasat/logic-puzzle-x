"""FastAPI app: JSON API for the solver plus the static web UI in support/web/.

Routes follow plan.md section 3.7. The handlers' logic lives in support/api.py, which the static
build (support/site.py) also runs in the browser. Solving runs in FastAPI's thread pool, always under a timeout.
"""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import api, benchmark
from .api import MAX_CHARS, ApiError

WEB_DIR = Path(__file__).parent / "web"
ROOT = Path(__file__).parents[1]
# Files the landing page shows, served from where they live in the repo rather than copied into web/.
MEDIA = {
    "demo.mp4": ROOT / "others" / "demo_video.mp4",
    "poster.jpg": ROOT / "others" / "demo_poster.jpg",
    "e1_nodes.png": ROOT / "data" / "results" / "e1_nodes.png",
    "e4_scale.png": ROOT / "data" / "results" / "e4_scale.png",
}

Algorithm = Literal["bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll"]

app = FastAPI(title="LogicPuzzleX", version=api.VERSION)


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


def _call(fn, *args):
    try:
        return fn(*args)
    except ApiError as error:
        raise HTTPException(status_code=error.status, detail=error.detail) from error


@app.get("/api/health")
def health() -> dict:
    return api.health()


@app.get("/api/puzzles")
def puzzles(type: Literal["sudoku"] = "sudoku", difficulty: str | None = None, size: int | None = None,
            limit: int = 50) -> list:
    """Sample puzzles from data/: famous ones, the rated sample and generated ones."""
    return api.puzzles(difficulty, size, limit)


@app.post("/api/solve")
def solve(request: SolveRequest) -> dict:
    return _call(api.solve, request.puzzle, request.algorithm, request.trace, request.explain, request.prove,
                 request.timeout)


@app.post("/api/race")
def race(request: RaceRequest) -> dict:
    return _call(api.race, request.puzzle, request.algorithms)


@app.post("/api/generate")
def generate(request: GenerateRequest) -> dict:
    return api.generate(request.size, request.difficulty, request.seed)


@app.get("/api/benchmarks")
def benchmarks() -> dict:
    return benchmark.summary()


@app.get("/media/{name}")
def media(name: str) -> FileResponse:
    path = MEDIA.get(name)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


# Mounted last so the /api routes above take priority over static files.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
