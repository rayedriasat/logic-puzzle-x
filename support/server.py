"""FastAPI app: JSON API for the solver plus the static web UI in support/web/.

Planned routes (plan.md section 3.7): /api/puzzles, /api/solve, /api/race,
/api/generate, /api/benchmarks. Owner: Member D.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="LogicPuzzleX", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


# Mounted last so the /api routes above take priority over static files.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
