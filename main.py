"""LogicPuzzleX entry point.

Run `python main.py` to open the web app, or use a sub-command:
    serve      launch the web app (default)
    solve      solve one puzzle from the command line
    bench      run the experiments behind the report figures
    generate   create new puzzles with a unique solution
    site       build the static website (for GitHub Pages) into site/
"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

ALGORITHMS = ["bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll"]
PUZZLE_TYPES = ["sudoku", "kakuro"]
DIFFICULTIES = ["easy", "medium", "hard", "extreme"]


def serve(args: argparse.Namespace) -> int:
    """Start the FastAPI server and open the UI in a browser tab."""
    import uvicorn

    from support.server import app

    url = f"http://{args.host}:{args.port}"
    print(f"LogicPuzzleX running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def kakuro_planned() -> int:
    print("Kakuro is planned but not implemented yet; see plan.md, section 6.")
    return 2


def read_puzzle(text: str) -> str:
    """The argument itself, or the first puzzle line of a file in the data/ format."""
    path = Path(text)
    if not path.is_file():
        return text
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(line.split()[0] for line in lines if line.strip() and not line.startswith("#"))


def solve(args: argparse.Namespace) -> int:
    if args.type == "kakuro":
        return kakuro_planned()
    from support.explain import explain
    from support.sudoku import format_grid, parse, solution_string, solve_grid
    from support.trace import Tracer

    try:
        grid = parse(read_puzzle(args.puzzle))
    except ValueError as error:
        print(f"Invalid puzzle: {error}")
        return 2
    tracer = Tracer(max_events=100_000 if args.explain else 0)
    result = solve_grid(grid, args.algo, tracer, args.timeout)
    if args.explain:
        for step in explain(tracer.events, grid):
            print(step["text"])
    if result.solution:
        print(format_grid(solution_string(result.solution, grid.size), grid.box))
    print(result.status, " ".join(f"{key}={value}" for key, value in result.stats.items()))
    return 0 if result.status == "solved" else 1


def bench(args: argparse.Namespace) -> int:
    from support.benchmark import run

    print(run(args.exp, args.algos.split(","), args.limit, args.timeout, args.workers, args.raw))
    return 0


def generate(args: argparse.Namespace) -> int:
    if args.type == "kakuro":
        return kakuro_planned()
    from support.generator import generate_sudoku

    for _ in range(args.count):
        puzzle, _, grade = generate_sudoku(args.size, args.difficulty)
        print(puzzle, grade)
    return 0


def site(args: argparse.Namespace) -> int:
    from support.site import build

    out = build(Path(args.out))
    print(f"Static site written to {out}/. Preview: python -m http.server -d {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="LogicPuzzleX: one constraint engine for Sudoku and Kakuro.",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    p = sub.add_parser("serve", help="launch the web app (default)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    p.set_defaults(func=serve)

    p = sub.add_parser("solve", help="solve one puzzle")
    p.add_argument("puzzle", help="puzzle string or path to a puzzle file")
    p.add_argument("--type", choices=PUZZLE_TYPES, default="sudoku")
    p.add_argument("--algo", choices=ALGORITHMS, default="mac")
    p.add_argument("--explain", action="store_true", help="print human-readable deductions")
    p.add_argument("--timeout", type=float, default=60.0, help="seconds allowed")
    p.set_defaults(func=solve)

    p = sub.add_parser("bench", help="run experiments and write data/results/")
    p.add_argument("--exp", default="e1", help="e1-e5 (plan.md section 4), generate, or sample (see data/README.md)")
    p.add_argument("--algos", default="bt,fc,mrv,mac,dpll", help="comma-separated algorithm ids")
    p.add_argument("--limit", type=int, default=200, help="max puzzles per run")
    p.add_argument("--timeout", type=float, default=10.0, help="seconds allowed per puzzle")
    p.add_argument("--workers", type=int, help="worker processes (default: all CPUs)")
    p.add_argument("--raw", help="raw CSV for --exp sample")
    p.set_defaults(func=bench)

    p = sub.add_parser("generate", help="generate puzzles with a unique solution")
    p.add_argument("--type", choices=PUZZLE_TYPES, default="sudoku")
    p.add_argument("--size", type=int, default=9)
    p.add_argument("--difficulty", choices=DIFFICULTIES, default="medium")
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(func=generate)

    p = sub.add_parser("site", help="build the static website (landing page + app) for GitHub Pages")
    p.add_argument("--out", default="site", help="output folder")
    p.set_defaults(func=site)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:  # bare `python main.py` launches the web app
        args = parser.parse_args(["serve"])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
