"""Experiments E1-E5 from plan.md section 4: run solvers and write CSVs to data/results/ (figures in figures.py).

`--exp sample` builds data/sudoku/rated_sample.csv from the raw download (see data/README.md).
Runs are timed in worker processes; each row is flushed at once, so a cut-off run keeps its results.
"""
from __future__ import annotations

import csv
import multiprocessing
import os
import platform
import random
import statistics
import time
from pathlib import Path

import numpy as np

from . import figures, sat
from .figures import ALGOS, RESULTS
from .generator import GRADES, generate_sudoku
from .sudoku import Grid, parse, solve_grid, to_csp

ROOT = Path(__file__).resolve().parents[1]
SUDOKU = ROOT / "data" / "sudoku"
SEED = 440
RUNS = 3  # wall time is the median of 3 runs; a timeout is recorded once
FIELDS = ["id", "bucket", "rating", "algo", "status", "nodes", "backtracks", "checks", "prunes", "ms"]
# algo id -> formulation; ":global" means 27 AllDifferent factors, or for dpll the extended CNF
FORMULATIONS = {"binary": "mac", "global": "mac:global", "global+hidden": "mac+", "cnf": "dpll", "cnf-extended": "dpll:global"}
SIZES = {4: 10, 6: 12, 9: 40, 16: 8}  # generated puzzles per size for E4


def bucket(rating: float) -> str:
    """Map the dataset's 0-8.5 rating (mean search depth; 43% are 0) to our four grades."""
    return "easy" if rating == 0 else "medium" if rating <= 2 else "hard" if rating <= 4 else "extreme"


def make_sample(raw, per_bucket: int = 250) -> Path:
    """Reservoir-sample each bucket of the raw CSV (columns id,puzzle,solution,clues,difficulty)."""
    rng = random.Random(SEED)
    kept = {b: [] for b in GRADES}
    seen = dict.fromkeys(GRADES, 0)
    with open(raw, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            b = bucket(float(row["difficulty"]))
            seen[b] += 1
            if len(kept[b]) < per_bucket:
                kept[b].append(row)
            elif (j := rng.randrange(seen[b])) < per_bucket:
                kept[b][j] = row
    print("bucket sizes in the raw data:", seen)
    path = SUDOKU / "rated_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["id", "puzzle", "rating", "bucket"])
        for b in GRADES:
            out.writerows([f"{b}-{i:03}", r["puzzle"], r["difficulty"], b] for i, r in enumerate(kept[b]))
    return path


def load_rated(limit=None) -> list:
    with open(SUDOKU / "rated_sample.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if limit:  # stay stratified: an equal share of every bucket
        share = max(1, limit // len(GRADES))
        rows = [r for b in GRADES for r in [x for x in rows if x["bucket"] == b][:share]]
    return rows


def load_generated(size: int) -> list:
    path = SUDOKU / "generated" / f"{size}.txt"
    return [line.split() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _measure(job: tuple) -> dict:
    meta, puzzle, algo, timeout = job
    grid = parse(puzzle)
    name, _, variant = algo.partition(":")
    times = []
    for _ in range(RUNS):
        result = solve_grid(grid, name, timeout=timeout, global_alldiff=True if variant else None)
        times.append(result.stats["ms"])
        if result.status == "timeout":
            break
    return {**meta, "algo": algo, "status": result.status, **result.stats, "ms": round(statistics.median(times), 3)}


def _sweep(function, jobs: list, workers, path=None, fields=None) -> list:
    """Run jobs in shuffled order (a cut-off run stays unbiased), streaming rows into `path`."""
    jobs = random.Random(SEED).sample(jobs, len(jobs))
    rows = []
    out = open(path, "w", newline="", encoding="utf-8") if path else None
    writer = csv.DictWriter(out, fields, extrasaction="ignore") if path else None
    if writer:
        writer.writeheader()
    with multiprocessing.Pool(workers or os.cpu_count()) as pool:
        for i, row in enumerate(pool.imap_unordered(function, jobs), 1):
            rows.append(row)
            if writer:
                writer.writerow(row)
                out.flush()
            if i % 200 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} done", flush=True)
    if out:
        out.close()
    return rows


def _write(name: str, rows: list) -> Path:
    path = RESULTS / name
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _read(name: str) -> list:
    with open(RESULTS / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def e1(algorithms, limit, timeout, workers) -> Path:
    """RQ1 ablation: every configuration on the rated sample."""
    jobs = [({"id": r["id"], "bucket": r["bucket"], "rating": r["rating"]}, r["puzzle"], a, timeout)
            for r in load_rated(limit) for a in algorithms]
    path = RESULTS / "e1.csv"
    rows = _sweep(_measure, jobs, workers, path, FIELDS)
    figures.e1_nodes(rows, algorithms)
    figures.e1_overview(rows, algorithms)
    return path


def _ranks(values) -> np.ndarray:
    """1-based ranks with ties averaged."""
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts)
    return ((2 * ends - counts + 1) / 2)[inverse]


def spearman(x, y) -> float:
    if len(set(x)) < 2 or len(set(y)) < 2:
        return float("nan")
    return float(np.corrcoef(_ranks(x), _ranks(y))[0, 1])


def e2() -> Path:
    """RQ2: rating vs effort, and the share of puzzles solved with zero backtracks. Reads e1.csv."""
    rows = _read("e1.csv")
    table = []
    for a in [x for x in ALGOS if any(r["algo"] == x for r in rows)]:
        runs = [r for r in rows if r["algo"] == a]
        solved = [r for r in runs if r["status"] == "solved"]
        entry = {"algo": a, "n_solved": len(solved),
                 "spearman": round(spearman([float(r["rating"]) for r in solved], [int(r["nodes"]) for r in solved]), 3)}
        for b in GRADES:
            group = [r for r in runs if r["bucket"] == b]
            entry[f"zero_backtrack_{b}"] = round(sum(r["status"] == "solved" and r["backtracks"] == "0" for r in group)
                                                 / max(1, len(group)), 3)
        table.append(entry)

    figures.e2_rating_vs_nodes(rows)
    figures.e2_zero_backtracks(table)
    return _write("e2.csv", table)


def _median(rows, key: str) -> float:
    return round(statistics.median(float(r[key]) for r in rows), 3) if rows else float("nan")


def _aggregate(runs: list) -> dict:
    timeouts = sum(r["status"] == "timeout" for r in runs)
    return {"runs": len(runs), "median_nodes": _median(runs, "nodes"), "median_ms": _median(runs, "ms"),
            "timeout_pct": round(100 * timeouts / len(runs), 1)}


def e3(limit, timeout, workers) -> Path:
    """RQ3: the same puzzles under each formulation."""
    sample = load_rated(limit)
    jobs = [({"id": r["id"]}, r["puzzle"], a, timeout) for r in sample for a in FORMULATIONS.values()]
    rows = _sweep(_measure, jobs, workers)
    empty = Grid(9, (3, 3), (0,) * 81)
    sizes = {"binary": (81, len(to_csp(empty).factors)), "global": (81, len(to_csp(empty, True).factors)),
             "global+hidden": (81, len(to_csp(empty, True).factors)), "cnf": (729, len(sat.encode(empty))),
             "cnf-extended": (729, len(sat.encode(empty, True)))}
    table = [{"formulation": name, "algo": a, "variables": sizes[name][0], "factors_or_clauses": sizes[name][1],
              **_aggregate([r for r in rows if r["algo"] == a])} for name, a in FORMULATIONS.items()]
    figures.e3_formulations(table)
    return _write("e3.csv", table)


def e4(algorithms, limit, timeout, workers) -> Path:
    """RQ4: effort from 4x4 to 16x16 on generated puzzles (Kakuro joins in Phase 2)."""
    jobs = []
    for size in SIZES:
        puzzles = load_generated(size)
        sample = random.Random(SEED).sample(puzzles, min(limit, len(puzzles)))
        jobs += [({"id": f"{size}-{i}", "size": size}, grid, a, timeout)
                 for i, (grid, _) in enumerate(sample) for a in algorithms]
    rows = _sweep(_measure, jobs, workers)
    table = [{"size": size, "algo": a, **_aggregate([r for r in rows if r["size"] == size and r["algo"] == a])}
             for size in SIZES for a in algorithms]
    figures.e4_scale(table, algorithms, list(SIZES))
    return _write("e4.csv", table)


def _generate(job: tuple) -> dict:
    size, difficulty, seed, budget = job
    start = time.perf_counter()
    puzzle, solution, found = generate_sudoku(size, difficulty, seed=seed, budget=budget)
    seconds = round(time.perf_counter() - start, 3)
    return {"size": size, "requested": difficulty, "grade": found, "clues": sum(1 for v in puzzle.cells if v),
            "seconds": seconds, "sat_unique": size <= 9 and sat.is_unique(puzzle, solution), "puzzle": str(puzzle)}


def _generate_jobs(size: int, per_grade: int) -> list:
    """Every job gets its own seed: a shared one digs the same puzzle when a harder grade falls back."""
    grades = GRADES if size in (6, 9) else ["hard"]  # 4x4 stops at easy; 16x16 digs on a time budget
    share = per_grade if size == 9 else SIZES[size] // len(grades)
    budget = 900 if size == 16 else 60
    return [(size, g, SEED + n, budget) for n, g in enumerate(g for g in grades for _ in range(share))]


def generate_all(per_grade: int, workers) -> None:
    """Fill data/sudoku/generated/{size}.txt; `--limit` is the 9x9 count per grade for E5."""
    (SUDOKU / "generated").mkdir(exist_ok=True)
    for size in SIZES:
        rows = _sweep(_generate, _generate_jobs(size, per_grade), workers)
        lines = sorted(f"{r['puzzle']} {r['grade']}" for r in rows)
        (SUDOKU / "generated" / f"{size}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if size == 9:
            _write("e5_runs.csv", [{k: v for k, v in r.items() if k != "puzzle"} for r in rows])


def e5() -> Path:
    """Generator quality, from e5_runs.csv."""
    rows = _read("e5_runs.csv")
    table = [{"requested": g, "puzzles": len(group), "hit_rate": round(sum(r["grade"] == g for r in group) / len(group), 3),
              "median_clues": _median(group, "clues"), "median_seconds": _median(group, "seconds"),
              "sat_verified_pct": round(100 * sum(r["sat_unique"] == "True" for r in group) / len(group), 1)}
             for g in GRADES if (group := [r for r in rows if r["requested"] == g])]
    figures.e5_clues(rows, table)
    return _write("e5.csv", table)


def machine() -> Path:
    path = RESULTS / "machine.txt"
    path.write_text(f"{platform.platform()} | {platform.python_version()} | {os.cpu_count()} logical CPUs\n", encoding="utf-8")
    return path


def run(experiment="e1", algorithms=None, limit=200, timeout=10.0, workers=None, raw=None) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    algorithms = algorithms or ALGOS
    machine()
    if experiment == "sample":
        return make_sample(raw or ROOT / "data" / "raw" / "sudoku-3m.csv")
    if experiment == "generate":
        generate_all(limit, workers)
        return SUDOKU / "generated"
    return {"e1": lambda: e1(algorithms, limit, timeout, workers), "e2": e2, "e3": lambda: e3(limit, timeout, workers),
            "e4": lambda: e4(algorithms, limit, timeout, workers), "e5": e5}[experiment]()


def summary() -> dict:
    """What the Benchmarks tab shows: E1 aggregated per algorithm and bucket, E2-E5 as written."""
    out = {"machine": None}
    if (RESULTS / "machine.txt").exists():
        out["machine"] = (RESULTS / "machine.txt").read_text(encoding="utf-8").strip()
    if (RESULTS / "e1.csv").exists():
        rows = _read("e1.csv")
        out["e1"] = [{"algo": a, "bucket": b, **_aggregate(group)} for a in ALGOS for b in GRADES
                     if (group := [r for r in rows if r["algo"] == a and r["bucket"] == b])]
    for name in ("e2", "e3", "e4", "e5"):
        if (RESULTS / f"{name}.csv").exists():
            out[name] = _read(f"{name}.csv")
    return out
