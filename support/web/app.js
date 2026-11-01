// App shell: tabs, the shared puzzle bar, theme and keyboard routing.
import { get, store, toast, toPuzzle } from "./api.js";
import { redrawBench, showBench } from "./bench.js";
import { initGenerate } from "./generate.js";
import { initPlay, keydown as playKeydown } from "./play.js";
import { initRace } from "./race.js";
import { explainKeydown, initSolve, runSolveNow, showExplain, solveKeydown } from "./solve.js";

const $ = (id) => document.getElementById(id);
const INKALA = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..";
const NO_PUZZLE_BAR = new Set(["generate", "bench"]);
let tab = "play";

function openTab(name, run = false) {
  tab = name;
  document.querySelectorAll("[data-tab]").forEach((button) => button.setAttribute("aria-selected", button.dataset.tab === name));
  document.querySelectorAll(".view").forEach((view) => { view.hidden = view.id !== `view-${name}`; });
  $("puzzle-bar").hidden = NO_PUZZLE_BAR.has(name);
  if (name === "explain") showExplain();
  if (name === "bench") showBench();
  if (name === "solve" && run) runSolveNow();
}

/** Presets use data/ when it is there; the three famous puzzles always are. */
async function loadPreset(value) {
  const [kind, a, b] = value.split(":");
  const query = kind === "famous" ? `difficulty=famous&limit=50` : `size=${a}&limit=1${b ? `&difficulty=${b}` : ""}`;
  const found = await get(`/api/puzzles?type=sudoku&${query}`);
  const pick = kind === "famous" ? found.find((p) => p.id === a) : found[0];
  if (!pick) return toast("No sample puzzle of that kind in data/ yet");
  store.setPuzzle({ ...toPuzzle(pick.puzzle, pick.id), preset: true });
}

function loadPasted() {
  try {
    store.setPuzzle(toPuzzle($("paste").value, "Pasted puzzle"));
    openTab(tab === "race" || tab === "explain" ? tab : "play");
  } catch (error) {
    toast(error.message);
  }
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("theme").setAttribute("aria-label", theme === "light" ? "Switch to dark theme" : "Switch to light theme");
  try { localStorage.setItem("lpx-theme", theme); } catch { /* private window: the toggle just is not remembered */ }
  redrawBench();
}

async function checkHealth() {
  const status = $("status");
  try {
    const data = await get("/api/health");
    status.classList.add("ok");
    $("status-text").textContent = `Solver online · v${data.version}`;
  } catch {
    status.classList.add("down");
    $("status-text").textContent = "Solver offline";
  }
}

document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => openTab(button.dataset.tab)));
$("preset").addEventListener("change", (e) => loadPreset(e.target.value).catch((error) => toast(error.message)));
$("paste-load").addEventListener("click", loadPasted);
$("paste").addEventListener("keydown", (e) => { if (e.key === "Enter") loadPasted(); });
$("theme").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light"));

document.addEventListener("keydown", (event) => {
  if (event.target.closest?.("input, select, textarea") || event.ctrlKey || event.metaKey || event.altKey) return;
  const handler = { play: playKeydown, solve: solveKeydown, explain: explainKeydown }[tab];
  if (handler?.(event)) event.preventDefault();
});

initPlay((grid) => {
  store.setPuzzle(toPuzzle(grid, "Your board"));
  openTab("solve", true);
});
initSolve();
initRace();
initGenerate(openTab);
store.onPuzzle((puzzle) => { if (!puzzle.preset) $("preset").value = "custom"; });

let saved = null;
try { saved = localStorage.getItem("lpx-theme"); } catch { /* same as above */ }
setTheme(saved ?? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
store.setPuzzle({ ...toPuzzle(INKALA, "inkala-2012"), preset: true });
checkHealth();
