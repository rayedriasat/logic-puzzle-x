# Data

Datasets used by LogicPuzzleX. Large raw downloads live in `data/raw/`, which is git-ignored (the course manual excludes large data files); only small, cited samples are committed.

| Path | Contents | Source |
|---|---|---|
| `sudoku/famous.txt` | 3 well-known 9×9 puzzles, each checked to have exactly one solution | Project Euler #96 (grid 01); "AI Escargot" by A. Inkala (2006); A. Inkala's 2012 "world's hardest Sudoku" |
| `sudoku/rated_sample.csv` | Stratified sample of 1000 rated puzzles (250 per bucket), columns `id,puzzle,rating,bucket` | D. Radcliffe, ["3 million Sudoku puzzles with ratings"](https://www.kaggle.com/datasets/radcliffe/3-million-sudoku-puzzles-with-ratings), Kaggle, CC0-1.0 |
| `sudoku/generated/<N>.txt` | Puzzles from our generator, `<grid> <grade>` per line, for N = 4, 6, 9, 16 | `python main.py bench --exp generate` |
| `kakuro/*.txt` | *(Phase 2)* Kakuro puzzles, checked unique by our solver | Our generator, plus cited public puzzles |
| `results/` | Benchmark CSVs and report figures, plus `machine.txt` (where they ran) and `kaggle_run.txt` (the runs behind them) | `python main.py bench` |

## Rebuilding the rated sample

The dataset's rating is the mean search-tree depth of an automated solver, from 0 to 8.5. Buckets: `easy` = 0, `medium` ≤ 2, `hard` ≤ 4, `extreme` > 4. Sampling is seeded, so these commands reproduce the committed file:

```bash
kaggle datasets download radcliffe/3-million-sudoku-puzzles-with-ratings -p data/raw --unzip
python main.py bench --exp sample --raw data/raw/sudoku-3m.csv
```

## Rebuilding the results

Run in this order; `e2` reads `e1.csv`, and `e4` and `e5` read what `generate` writes. The committed results used these settings on Kaggle T4 sessions (the solvers are pure Python, so only the CPU matters). `sample`, `e1`, `e2` and `e3` come from one run, and `generate`, `e4` and `e5` from a later run on the same machine type; `results/kaggle_run.txt` records both:

```bash
python main.py bench --exp generate --limit 100
python main.py bench --exp e5
python main.py bench --exp e4 --limit 40 --timeout 10 --algos bt,fc,mrv,lcv,mac,mac+,dpll
python main.py bench --exp e3 --limit 200 --timeout 10
python main.py bench --exp e1 --limit 1000 --timeout 10 --algos bt,fc,mrv,lcv,mac,mac+,dpll
python main.py bench --exp e2
```

## Formats

**Sudoku (`.txt`)**: one puzzle per line, `<grid> <name or grade>`. The grid is row-major with `.` for empty cells (81 characters for 9×9); digits above 9 are the letters A–P. Lines starting with `#` are comments.

**Kakuro (`.txt`)**: one row per line, cells separated by spaces. `#` is a black cell, `.` a white cell, and `D\R` a clue cell with down-sum `D` and right-sum `R` (`-` when absent). Example row: `# 16\- 24\- #`.
