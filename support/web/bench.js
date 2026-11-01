// Benchmarks tab: the experiment results in data/results/. Tables always render; charts need the Chart.js CDN.
import { get } from "./api.js";

const $ = (id) => document.getElementById(id);
const ALGOS = ["bt", "fc", "mrv", "lcv", "mac", "mac+", "dpll"];
const BUCKETS = ["easy", "medium", "hard", "extreme"];
// Fixed per algorithm, matching the report figures. Dark steps are chosen for the dark surface.
const COLORS = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9"],
};

let charts = [];
let data = null;

const isLight = () => document.documentElement.dataset.theme === "light";
const color = (algo) => COLORS[isLight() ? "light" : "dark"][ALGOS.indexOf(algo)];

function table(rows, columns) {
  const head = columns.map(([, title]) => `<th scope="col">${title}</th>`).join("");
  const body = rows.map((row) => `<tr>${columns.map(([key]) => `<td>${row[key] ?? "–"}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function chartDefaults() {
  const css = getComputedStyle(document.documentElement);
  const text = css.getPropertyValue("--muted").trim();
  const grid = css.getPropertyValue("--line").trim();
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: text, boxWidth: 12 } } },
    scales: {
      x: { ticks: { color: text }, grid: { display: false } },
      y: { type: "logarithmic", ticks: { color: text, maxTicksLimit: 7 }, grid: { color: grid } },
    },
  };
}

function draw() {
  charts.forEach((chart) => chart.destroy());
  charts = [];
  if (!window.Chart || !data) return;
  const present = ALGOS.filter((a) => data.e1?.some((r) => r.algo === a));
  if (data.e1) {
    charts.push(new Chart($("chart-e1"), {
      type: "bar",
      data: {
        labels: BUCKETS,
        datasets: present.map((a) => ({
          label: a,
          data: BUCKETS.map((b) => data.e1.find((r) => r.algo === a && r.bucket === b)?.median_nodes ?? null),
          backgroundColor: color(a),
          borderRadius: 4,
          borderSkipped: "bottom",
          borderColor: "transparent",
          borderWidth: 1,
        })),
      },
      options: chartDefaults(),
    }));
  }
  if (data.e4) {
    const sizes = [...new Set(data.e4.map((r) => r.size))];
    const options = chartDefaults();
    const row = (a, n) => data.e4.find((r) => r.algo === a && r.size === n);
    charts.push(new Chart($("chart-e4"), {
      type: "line",
      data: {
        labels: sizes.map((n) => `${n}×${n}`),
        datasets: ALGOS.filter((a) => data.e4.some((r) => r.algo === a)).map((a) => ({
          label: a,
          data: sizes.map((n) => Number(row(a, n)?.median_ms)),
          borderColor: color(a),
          backgroundColor: color(a),
          // hollow: the median run hit the time limit, so this is a lower bound
          pointBackgroundColor: sizes.map((n) => (Number(row(a, n)?.timeout_pct) >= 50 ? "transparent" : color(a))),
          borderWidth: 2,
          pointRadius: 4,
        })),
      },
      options,
    }));
  }
}

function render() {
  const ready = data && (data.e1 || data.e3 || data.e4 || data.e5);
  $("bench-empty").hidden = Boolean(ready);
  $("bench-body").hidden = !ready;
  if (!ready) return;
  $("bench-machine").textContent = data.machine ? `Measured on: ${data.machine}` : "";
  if (data.e1) {
    const rows = ALGOS.filter((a) => data.e1.some((r) => r.algo === a)).map((a) => {
      const row = { algo: a };
      for (const r of data.e1.filter((x) => x.algo === a)) {
        row[`ms_${r.bucket}`] = r.median_ms.toLocaleString();
        row[`to_${r.bucket}`] = `${r.timeout_pct}%`;
      }
      return row;
    });
    $("table-e1").innerHTML = table(rows, [["algo", "Algorithm"],
      ...BUCKETS.flatMap((b) => [[`ms_${b}`, `${b} ms`], [`to_${b}`, "timeouts"]])]);
  }
  if (data.e2) {
    $("table-e2").innerHTML = table(data.e2, [["algo", "Algorithm"], ["n_solved", "Solved"], ["spearman", "Spearman ρ"],
      ...BUCKETS.map((b) => [`zero_backtrack_${b}`, `No backtrack, ${b}`])]);
  }
  if (data.e3) {
    $("table-e3").innerHTML = table(data.e3, [["formulation", "Formulation"], ["variables", "Variables"],
      ["factors_or_clauses", "Factors / clauses"], ["median_nodes", "Median nodes"], ["median_ms", "Median ms"], ["timeout_pct", "Timeout %"]]);
  }
  if (data.e4) {
    $("table-e4").innerHTML = table(data.e4, [["size", "N"], ["algo", "Algorithm"], ["median_nodes", "Median nodes"],
      ["median_ms", "Median ms"], ["timeout_pct", "Timeout %"]]);
  }
  if (data.e5) {
    $("table-e5").innerHTML = table(data.e5, [["requested", "Requested"], ["puzzles", "Puzzles"], ["hit_rate", "Hit rate"],
      ["median_clues", "Median clues"], ["median_seconds", "Median seconds"], ["sat_verified_pct", "SAT verified %"]]);
  }
  draw();
}

export async function showBench() {
  if (data) { draw(); return; }
  try {
    data = await get("/api/benchmarks");
    render();
  } catch {
    $("bench-empty").hidden = false;
  }
}

export const redrawBench = () => { if (data) draw(); };
