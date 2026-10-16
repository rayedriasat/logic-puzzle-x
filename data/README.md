# Data

Datasets used by LogicPuzzleX. Large raw downloads live in `data/raw/`, which is git-ignored (the course manual excludes large data files); only small, cited samples are committed.

| Path | Contents | Source |
|---|---|---|
| `sudoku/famous.txt` | 3 well-known 9×9 puzzles, each checked to have exactly one solution | Project Euler #96 (grid 01); "AI Escargot" by A. Inkala (2006); A. Inkala's 2012 "world's hardest Sudoku" |
| `sudoku/rated_sample.csv` | *(Phase 1)* stratified sample of rated puzzles, columns `id,puzzle,rating,bucket` | To be chosen from the candidates below; license checked and cited |
| `kakuro/*.txt` | *(Phase 2)* Kakuro puzzles, checked unique by our solver | Our generator, plus cited public puzzles |
| `results/*.csv` | *(Phases 1–3)* benchmark outputs behind every report figure | `python main.py bench` |

## Formats

**Sudoku (`.txt`)**: one puzzle per line, `<grid> <name>`. The grid is row-major with `.` for empty cells (81 characters for 9×9). Lines starting with `#` are comments.

**Kakuro (`.txt`)**: one row per line, cells separated by spaces. `#` is a black cell, `.` a white cell, and `D\R` a clue cell with down-sum `D` and right-sum `R` (`-` when absent). Example row: `# 16\- 24\- #`.

## Candidate rated Sudoku sources (verify license and format before use)
- `grantm/sudoku-exchange-puzzle-bank` on GitHub: easy / medium / hard / diabolical files with ratings.
- Kaggle, "3 million Sudoku puzzles with ratings" (D. Radcliffe).
- P. Norvig's `top95.txt` and `hardest.txt` (norvig.com).
