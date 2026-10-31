<div align="center">

# LogicPuzzleX

**One constraint engine. Many puzzles. Watch it think.**

An AI system that solves **Sudoku** and **Kakuro** as constraint satisfaction problems, using backtracking search, constraint propagation and propositional logic, and shows its reasoning live in the browser.

*CSE 440: Artificial Intelligence · North South University · Section ‹X› · Group ‹N›*

</div>

> **Status: in development.** The roadmap is in [plan.md](plan.md). A demo GIF and the one-minute video will appear here in the final phase.

## Highlights

| Feature | What it does | Status |
|---|---|---|
| Watch it think | Animated replay of the search: candidates vanish as constraints propagate, cells flash on backtrack | Planned (Phase 1) |
| Algorithm race | Naive backtracking vs forward checking vs MRV vs MAC on the same puzzle, side by side | Planned (Phase 2) |
| One engine, many puzzles | Sudoku 4×4 to 16×16 and Kakuro, all modeled as factor graphs | Planned (Phases 1–2) |
| Logic track | Sudoku → CNF, solved with our DPLL; uniqueness proved by entailment | Planned (Phase 2) |
| Explain mode | Every deduction in plain English ("r5c3 = 7: only place in box 4 for a 7") | Planned (Phase 3) |
| Generator | New puzzles with exactly one solution, graded Easy → Extreme | Planned (Phase 3) |
| Benchmarks | Reproducible experiments behind every figure in our report | Planned (Phases 1–3) |

## How it works

Each puzzle becomes a **factor graph**: variables `X_i` with domains, and factors `f_j(x) ∈ {0, 1}`. A complete assignment `x` solves the puzzle when

```text
weight(x) = f_1(x) · f_2(x) · … · f_m(x) = 1
```

A 9×9 Sudoku has 81 variables and 810 binary "≠" factors; Kakuro adds a sum factor for every run. The solver climbs an **algorithm ladder**:

| ID | Technique |
|---|---|
| `bt` | Naive backtracking (depth-first over partial assignments) |
| `fc` | + Forward checking |
| `mrv` | + Minimum remaining values (degree tie-break) |
| `lcv` | + Least constraining value |
| `mac` | Maintaining arc consistency (AC-3 after every assignment) |
| `mac+` | + Global all-different reasoning (hidden singles) |
| `dpll` | Propositional encoding solved with DPLL (unit propagation) |

## Quick start

Requires Python 3.12. With [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
uv pip install -r requirements.txt
python main.py
```

With plain pip:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The web app opens at <http://127.0.0.1:8000>; API docs are at `/docs`.

## Usage

```text
python main.py                                   # launch the web app
python main.py solve "<puzzle>" --algo mac       # solve from the command line
python main.py bench --algos bt,fc,mrv,mac       # run experiments, write data/results/
python main.py generate --difficulty hard        # create a puzzle with a unique solution
python -m pytest -q                              # run the tests
```

## Repository structure

Organized as the course manual requires:

```text
├── main.py            # entry point: serve | solve | bench | generate
├── README.md          # this file
├── requirements.txt   # Python libraries
├── data/              # datasets (see data/README.md)
├── support/           # all other code: CSP engine, puzzles, SAT, web UI, tests
└── others/            # reports (PDF), presentations (PPTX), demo video
```

## Code tour

*Filled in as modules land.* This table is the route for our 4-minute code walkthrough, with links straight to the key functions.

| Step | File | What to look at |
|---|---|---|
| 1 | [main.py](main.py) | CLI and how the app starts |
| 2 | [support/csp.py](support/csp.py) | Factor graph model, `weight(x)` |
| 3 | [support/solver.py](support/solver.py) | Backtracking search and heuristics |
| 4 | [support/propagation.py](support/propagation.py) | Forward checking, AC-3 |
| 5 | [support/sudoku.py](support/sudoku.py) · [support/kakuro.py](support/kakuro.py) | Puzzle → factors |
| 6 | [support/sat.py](support/sat.py) | CNF encoding, DPLL |
| 7 | [support/server.py](support/server.py) · [support/web/](support/web/) | API and UI |

## Team

| Name | Student ID | Role |
|---|---|---|
| Md Shihabul Alam Shihab | 2233115642 | CSP engine and search |
| Rayed Riasat Rabbi  | 2311649042 | Puzzle modeling, propagation, generator |
| Rifat Imtiaze Ruddro | 2311474642 | Logic track, explanations, experiments |
| Sayma Akhter Snigdha | 1620838042 | Web app, demo video, integration |

## References

Full list in our final report. Key sources: Russell & Norvig, *AIMA* (Ch. 6–7); Mackworth (1977) on AC-3; Haralick & Elliott (1980) on forward checking; Davis, Logemann & Loveland (1962) on DPLL; Simonis (2005) and Lynce & Ouaknine (2006) on Sudoku as CSP and SAT; the CSE 440 course notes.

## Acknowledgements

Course: CSE 440, North South University. AI tools: Claude (Anthropic) helped draft the project plan and the repository scaffold; all solver code and experiments are written and verified by the team.
