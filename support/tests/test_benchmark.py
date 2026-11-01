"""Experiment helpers that decide what the report's numbers mean."""
import math

import numpy as np
import pytest

from support import benchmark
from support.benchmark import _aggregate, _measure, _ranks, bucket, spearman

EULER = "..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3.."
INKALA = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4.."


@pytest.mark.parametrize("rating, expected", [(0, "easy"), (0.1, "medium"), (2, "medium"), (2.1, "hard"), (4, "hard"),
                                              (4.1, "extreme"), (8.5, "extreme")])
def test_buckets(rating, expected):
    assert bucket(rating) == expected


def test_ranks_average_ties():
    assert _ranks([10, 20, 20, 30]).tolist() == [1, 2.5, 2.5, 4]


def test_spearman_is_rank_based():
    x = [1, 2, 3, 4, 5]
    assert spearman(x, [v ** 3 for v in x]) == pytest.approx(1)
    assert spearman(x, [-v for v in x]) == pytest.approx(-1)
    assert np.isclose(spearman([1, 2, 3, 4], [1, 3, 2, 4]), 0.8)


def test_spearman_of_a_constant_is_undefined():
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3]))


def test_timeout_is_recorded_once_with_its_status():
    row = _measure(({"id": "x"}, INKALA, "bt", 0.01))
    assert row["status"] == "timeout"
    assert row["ms"] < 1000


def test_global_variant_changes_the_formulation_not_the_answer():
    assert _measure(({"id": "x"}, EULER, "mac:global", 10))["status"] == "solved"
    assert _measure(({"id": "x"}, EULER, "dpll:global", 10))["status"] == "solved"


def test_aggregate_keeps_timeouts_visible():
    runs = [{"nodes": "10", "ms": "1", "status": "solved"}, {"nodes": "30", "ms": "3", "status": "timeout"}]
    assert _aggregate(runs) == {"runs": 2, "median_nodes": 20, "median_ms": 2, "timeout_pct": 50.0}


@pytest.mark.parametrize("size", benchmark.SIZES)
def test_generation_jobs_never_share_a_seed(size):
    jobs = benchmark._generate_jobs(size, 5)
    assert len({seed for _, _, seed, _ in jobs}) == len(jobs)


@pytest.mark.parametrize("size, expected", [(4, 10), (6, 12), (9, 20), (16, 8)])
def test_generation_jobs_cover_the_full_count(size, expected):
    assert len(benchmark._generate_jobs(size, 5)) == expected


def test_sample_is_stratified(tmp_path, monkeypatch):
    raw = tmp_path / "raw.csv"
    lines = ["id,puzzle,solution,clues,difficulty"]
    lines += [f"{i},{EULER},x,32,{rating}" for i, rating in enumerate([0, 1, 3, 5] * 5)]
    raw.write_text("\n".join(lines))
    monkeypatch.setattr(benchmark, "SUDOKU", tmp_path)
    benchmark.make_sample(raw, per_bucket=3)
    rows = benchmark.load_rated()
    assert len(rows) == 12
    assert len(benchmark.load_rated(limit=4)) == 4
    assert {r["bucket"] for r in benchmark.load_rated(limit=4)} == set(benchmark.GRADES)
