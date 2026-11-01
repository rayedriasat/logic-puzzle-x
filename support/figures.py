"""Report figures for experiments E1-E5 (PNG in data/results/). Each algorithm keeps one color in every chart."""
from __future__ import annotations

from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "data" / "results"
ALGOS = ["bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll"]
COLORS = dict(zip(ALGOS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]))
BUCKETS = ["easy", "medium", "hard", "extreme"]


def _figure(name: str, draw, ncols=1, size=(8, 4)) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, ncols, figsize=size, sharey=ncols > 1, squeeze=False)
    draw(axes.ravel())
    for ax in axes.ravel():
        ax.grid(axis="y", color="#e5e4e0", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(RESULTS / name, dpi=200)
    plt.close(fig)


def e1_nodes(rows: list, algorithms: list) -> None:
    """Box plot of search nodes per configuration, one panel per difficulty bucket."""
    def draw(axes):
        for ax, b in zip(axes, BUCKETS):
            group = [[float(r["nodes"]) for r in rows if r["bucket"] == b and r["algo"] == a] for a in algorithms]
            box = ax.boxplot(group, patch_artist=True, widths=0.6, flierprops={"markersize": 2})
            for patch, a in zip(box["boxes"], algorithms):
                patch.set(facecolor=COLORS[a], edgecolor="#52514e", linewidth=0.6)
            ax.set_xticklabels(algorithms, fontsize=8)
            ax.set_yscale("log")
            ax.set_title(b, fontsize=10)
        axes[0].set_ylabel("search nodes (log)")

    _figure("e1_nodes.png", draw, 4, (11, 3.6))


def e1_overview(rows: list, algorithms: list) -> None:
    """Every puzzle in one panel, sized for a single report column."""
    def draw(axes):
        group = [[float(r["nodes"]) for r in rows if r["algo"] == a] for a in algorithms]
        box = axes[0].boxplot(group, patch_artist=True, widths=0.6, flierprops={"markersize": 1.5},
                              medianprops={"color": "#111827"})
        for patch, a in zip(box["boxes"], algorithms):
            patch.set(facecolor=COLORS[a], edgecolor="#52514e", linewidth=0.5)
        axes[0].set_xticklabels(algorithms, fontsize=8)
        axes[0].set_yscale("log")
        axes[0].tick_params(axis="y", labelsize=8)
        axes[0].set_ylabel("search nodes (log)", fontsize=8)

    _figure("e1_overview.png", draw, 1, (3.5, 1.75))


def e2_rating_vs_nodes(rows: list) -> None:
    def draw(axes):
        runs = [r for r in rows if r["algo"] == "mac" and r["status"] == "solved"]
        axes[0].scatter([float(r["rating"]) for r in runs], [int(r["nodes"]) for r in runs], s=8, color=COLORS["mac"],
                        edgecolors="#ffffff", linewidths=0.3)
        axes[0].set(yscale="log", xlabel="dataset rating", ylabel="MAC search nodes (log)")

    _figure("e2_rating_vs_nodes.png", draw)


def e2_zero_backtracks(table: list) -> None:
    def draw(axes):
        width = 0.8 / len(table)
        for i, entry in enumerate(table):
            xs = [j + i * width for j in range(len(BUCKETS))]
            axes[0].bar(xs, [100 * entry[f"zero_backtrack_{b}"] for b in BUCKETS], width * 0.9, label=entry["algo"],
                        color=COLORS[entry["algo"]])
        axes[0].set_xticks([j + 0.4 - width / 2 for j in range(len(BUCKETS))], BUCKETS)
        axes[0].set_ylabel("% solved with zero backtracks")
        axes[0].legend(ncol=len(table), fontsize=8, frameon=False)

    _figure("e2_zero_backtracks.png", draw)


def e3_formulations(table: list) -> None:
    def draw(axes):
        axes[0].bar([t["formulation"] for t in table], [t["median_ms"] for t in table], width=0.6, color=COLORS["bt"])
        axes[0].set_ylabel("median solve time (ms)")

    _figure("e3_formulations.png", draw)


def e4_scale(table: list, algorithms: list, sizes: list) -> None:
    def draw(axes):
        for a in algorithms:
            line = [t for t in table if t["algo"] == a]
            axes[0].plot([t["size"] for t in line], [max(t["median_ms"], 0.01) for t in line], marker="o", linewidth=2,
                         color=COLORS[a], label=a)
            # a median at the time limit is a lower bound, not a measurement
            capped = [t for t in line if t["timeout_pct"] >= 50]
            axes[0].plot([t["size"] for t in capped], [t["median_ms"] for t in capped], "o", color=COLORS[a],
                         markerfacecolor="#ffffff", markeredgewidth=2)
        axes[0].set(yscale="log", xlabel="grid size N", ylabel="median solve time (ms, log)", xticks=sizes)
        axes[0].legend(fontsize=8, frameon=False)
        axes[0].text(0.99, 0.03, "hollow: the median run hit the time limit, so the true time is higher",
                     transform=axes[0].transAxes, ha="right", fontsize=8, color="#52514e")

    _figure("e4_scale.png", draw)


def e5_clues(rows: list, table: list) -> None:
    def draw(axes):
        groups = [[int(r["clues"]) for r in rows if r["requested"] == t["requested"]] for t in table]
        axes[0].boxplot(groups, widths=0.5)
        axes[0].set_xticklabels([t["requested"] for t in table])
        axes[0].set_ylabel("clues")

    _figure("e5_clues.png", draw)
