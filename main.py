"""LogicPuzzleX entry point.

Run `python main.py` to open the web app, or use a sub-command:
    serve      launch the web app (default)
    solve      solve one puzzle from the command line
    bench      run the experiments behind the report figures
    generate   create new puzzles with a unique solution
"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser

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


def planned(name: str):
    """Placeholder for sub-commands that are scheduled in plan.md but not built yet."""

    def run(args: argparse.Namespace) -> int:
        print(f"'{name}' is planned but not implemented yet; see plan.md, section 6.")
        return 2

    return run


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
    p.set_defaults(func=planned("solve"))

    p = sub.add_parser("bench", help="run experiments and write data/results/")
    p.add_argument("--exp", default="e1", help="experiment id (e1-e5, see plan.md section 4)")
    p.add_argument("--algos", default="bt,fc,mrv,mac,dpll", help="comma-separated algorithm ids")
    p.add_argument("--limit", type=int, default=200, help="max puzzles per run")
    p.add_argument("--timeout", type=float, default=10.0, help="seconds allowed per puzzle")
    p.set_defaults(func=planned("bench"))

    p = sub.add_parser("generate", help="generate puzzles with a unique solution")
    p.add_argument("--type", choices=PUZZLE_TYPES, default="sudoku")
    p.add_argument("--size", type=int, default=9)
    p.add_argument("--difficulty", choices=DIFFICULTIES, default="medium")
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(func=planned("generate"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:  # bare `python main.py` launches the web app
        args = parser.parse_args(["serve"])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
