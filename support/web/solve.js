// Solve tab ("Watch it think") and Explain tab: both replay one solver trace on one board.
import { post, store, toast } from "./api.js";
import { Board } from "./board.js";
import { DIGITS, Player, Replay } from "./replay.js";

const $ = (id) => document.getElementById(id);
const SLOW = 80; // events per second below which each event animates
const LOG_LINES = 200;
const LIST_CAP = 1000; // deductions listed in Explain; the board can still reach the rest with Next

function cellName(cell, size) {
  return `r${Math.floor(cell / size) + 1}c${(cell % size) + 1}`;
}

function logLine([kind, cell, value, reason], size) {
  if (kind === "A") return `assign    ${cellName(cell, size)} = ${DIGITS[value - 1]}`;
  if (kind === "P") return `prune     ${cellName(cell, size)} ≠ ${DIGITS[value - 1]}  (${reason})`;
  if (kind === "B") return `backtrack ${cellName(cell, size)}`;
  return "solved";
}

const solve = { board: null, replay: null, player: null, log: [], algorithm: "mac", proofId: 0 };

function statsUpdate() {
  const { replay } = solve;
  $("stat-nodes").textContent = replay.nodes.toLocaleString();
  $("stat-backtracks").textContent = replay.backtracks.toLocaleString();
  $("stat-prunes").textContent = replay.prunes.toLocaleString();
  $("scrub").value = replay.pos;
  $("scrub-label").textContent = `${replay.pos.toLocaleString()} / ${replay.events.length.toLocaleString()}`;
}

function paintSolve(animate = false) {
  solve.board.paint(solve.replay.values, solve.replay.candidates, { animate });
  statsUpdate();
}

function showLog() {
  $("log").textContent = solve.log.join("\n");
  $("log").scrollTop = $("log").scrollHeight;
}

/** After a jump the log is rebuilt from the events just before the new position. */
function rebuildLog() {
  const { replay } = solve;
  solve.log = replay.events.slice(Math.max(0, replay.pos - LOG_LINES), replay.pos).map((e) => logLine(e, replay.size));
  showLog();
}

function setPlaying(playing) {
  $("play-pause").textContent = playing ? "⏸" : "▶";
  $("play-pause").setAttribute("aria-label", playing ? "Pause" : "Play");
}

function onFrame(batches) {
  const { replay, player } = solve;
  if (!batches) {
    setPlaying(false);
    paintSolve();
    finish();
    return;
  }
  const events = batches[0];
  const animate = player.speed < SLOW;
  paintSolve(animate);
  if (animate) for (const e of events) if (e[0] === "B") solve.board.flash(e[1]);
  solve.log.push(...events.slice(-LOG_LINES).map((e) => logLine(e, replay.size)));
  solve.log = solve.log.slice(-LOG_LINES);
  showLog();
}

function finish() {
  const { replay } = solve;
  if (replay.solved) solve.board.ripple();
  const result = replay.result;
  if (result.truncated && result.solution) {  // the capped log stops short of the end: show the real result
    solve.board.paint(Int32Array.from(result.solution, (ch) => DIGITS.indexOf(ch) + 1), replay.candidates);
  }
}

function summary(body) {
  const ms = body.stats.ms.toLocaleString(undefined, { maximumFractionDigits: 1 });
  const status = { solved: `Solved in ${ms} ms`, unsat: `No solution (${ms} ms)`, timeout: `Gave up after ${ms} ms` }[body.status];
  $("solve-summary").textContent = status + (body.truncated ? " · replay shows the first 100,000 events" : "");
  $("solve-summary").className = `verdict ${body.status === "solved" ? "good" : body.status === "unsat" ? "bad" : "idle"}`;
  $("stat-checks").textContent = body.stats.checks.toLocaleString();
}

/** The SAT proof takes seconds on hard puzzles, so it runs after the replay has started. */
async function prove(puzzle) {
  const id = ++solve.proofId;
  const proof = $("solve-proof");
  proof.textContent = "Proving uniqueness with SAT…";
  try {
    // In-browser Python (static build) runs about 3x slower than the server, so give the proof the API's maximum.
    const timeout = window.LPX_BACKEND === "pyodide" ? 30 : 15;
    const body = await post("/api/solve", { puzzle: puzzle.grid, algorithm: "mac+", trace: false, prove: true, timeout });
    if (id !== solve.proofId) return;
    proof.textContent = body.unique === true ? "Unique ✓: KB ∪ {¬s} is unsatisfiable, so KB ⊨ s"
      : body.unique === false ? "Not unique: DPLL found a second solution, so KB ⊭ s"
      : "Uniqueness not proved in time";
  } catch (error) {
    if (id === solve.proofId) proof.textContent = error.message;
  }
}

async function runSolve() {
  solve.player?.pause();
  $("solve-run").disabled = true;
  $("solve-summary").textContent = "Solving…";
  $("solve-summary").className = "verdict idle";
  $("solve-proof").textContent = "";
  try {
    const puzzle = store.puzzle;
    const body = await post("/api/solve", { puzzle: puzzle.grid, algorithm: solve.algorithm, timeout: 15 });
    solve.replay = new Replay(puzzle, body);
    solve.board = new Board($("solve-board"), puzzle, { onHover: caption("solve-caption", puzzle.size) });
    solve.player = new Player([solve.replay], onFrame);
    fitSpeed(body.events.length);
    solve.log = [];
    $("log").textContent = "";
    $("scrub").max = body.events.length;
    summary(body);
    paintSolve();
    solve.player.play();
    setPlaying(true);
    if (body.status === "solved") prove(puzzle);
  } catch (error) {
    toast(error.message);
    $("solve-summary").textContent = error.message;
  } finally {
    $("solve-run").disabled = false;
  }
}

function caption(id, size) {
  return (cell, peers) => {
    $(id).textContent = cell === null ? "Hover a cell to see its Markov blanket."
      : `${cellName(cell, size)}: its ${peers} peers are its Markov blanket`;
  };
}

const speed = () => 10 ** (1 + Number($("speed").value));

function showSpeed() {
  if (solve.player) solve.player.speed = speed();
  $("speed-label").textContent = `${Math.round(speed() / 10)}×`;
}

/** Start at a rate that replays the whole trace in about 20 seconds. */
function fitSpeed(events) {
  $("speed").value = Math.log10(Math.min(1000, Math.max(4, events / 200)));
  showSpeed();
}

function stepBy(delta) {
  if (!solve.replay) return;
  solve.player.pause();
  setPlaying(false);
  solve.replay.seek(Math.max(0, solve.replay.pos + delta));
  paintSolve(true);
  rebuildLog();
  if (solve.replay.done) finish();
}

export function togglePlayback() {
  const { player, replay } = solve;
  if (!player) return;
  if (player.playing) { player.pause(); setPlaying(false); return; }
  if (replay.done) replay.seek(0);
  player.play();
  setPlaying(player.playing);
}

export function solveKeydown(event) {
  if (event.key === " ") { togglePlayback(); return true; }
  if (event.key === "ArrowLeft") { stepBy(-1); return true; }
  if (event.key === "ArrowRight") { stepBy(1); return true; }
  return false;
}

function choices(rootId, onPick) {
  const root = $(rootId);
  root.addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (!button) return;
    root.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b === button));
    onPick(button.dataset.algo);
  });
}

/* ---------- Explain tab ---------- */

const explain = { board: null, replay: null, steps: [], index: -1, puzzle: null, algorithm: "mac+" };

function showStep(index) {
  const { steps, replay, board } = explain;
  if (!steps.length) return;
  explain.index = Math.max(0, Math.min(index, steps.length - 1));
  const step = steps[explain.index];
  replay.seek(step.event + 1);
  board.paint(replay.values, replay.candidates, { animate: true });
  board.mark("focus", [step.var]);
  if (step.kind === "backtrack") board.flash(step.var);
  $("explain-text").textContent = step.text;
  $("explain-kind").textContent = { naked: "Naked single", hidden: "Hidden single", guess: "Guess", backtrack: "Backtrack" }[step.kind];
  $("explain-kind").dataset.kind = step.kind;
  $("explain-count").textContent = `Step ${explain.index + 1} of ${steps.length.toLocaleString()}`;
  $("explain-list").querySelector(".current")?.classList.remove("current");
  const row = $("explain-list").children[explain.index];
  row?.classList.add("current");
  row?.scrollIntoView({ block: "nearest" });
}

async function runExplain() {
  const puzzle = store.puzzle;
  explain.puzzle = puzzle;
  $("explain-text").textContent = "Solving…";
  $("explain-list").replaceChildren();
  try {
    const body = await post("/api/solve", { puzzle: puzzle.grid, algorithm: explain.algorithm, explain: true, timeout: 15 });
    explain.steps = body.explanation ?? [];
    explain.replay = new Replay(puzzle, body);
    explain.board = new Board($("explain-board"), puzzle);
    explain.board.paint(explain.replay.values, explain.replay.candidates);
    $("explain-list").replaceChildren(...explain.steps.slice(0, LIST_CAP).map((step, i) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.textContent = step.text;
      button.dataset.kind = step.kind;
      button.addEventListener("click", () => showStep(i));
      item.append(button);
      return item;
    }));
    showStep(0);
    if (!explain.steps.length) $("explain-text").textContent = "Nothing to explain: the board is already complete.";
  } catch (error) {
    $("explain-text").textContent = error.message;
  }
}

export function explainKeydown(event) {
  if (event.key === "ArrowLeft") { showStep(explain.index - 1); return true; }
  if (event.key === "ArrowRight") { showStep(explain.index + 1); return true; }
  return false;
}

export function showExplain() {
  if (explain.puzzle !== store.puzzle) runExplain();
}

export function runSolveNow() {
  return runSolve();
}

export function initSolve() {
  choices("solve-algos", (algo) => { solve.algorithm = algo; });
  choices("explain-algos", (algo) => { explain.algorithm = algo; runExplain(); });
  $("solve-run").addEventListener("click", runSolve);
  $("play-pause").addEventListener("click", togglePlayback);
  $("step-back").addEventListener("click", () => stepBy(-1));
  $("step-forward").addEventListener("click", () => stepBy(1));
  $("to-start").addEventListener("click", () => stepBy(-Infinity));
  $("to-end").addEventListener("click", () => stepBy(Number.MAX_SAFE_INTEGER));
  $("speed").addEventListener("input", showSpeed);
  $("scrub").addEventListener("input", () => {
    if (!solve.replay) return;
    solve.player.pause();
    setPlaying(false);
    solve.replay.seek(Number($("scrub").value));
    paintSolve();
    rebuildLog();
  });
  $("explain-prev").addEventListener("click", () => showStep(explain.index - 1));
  $("explain-next").addEventListener("click", () => showStep(explain.index + 1));
  store.onPuzzle((puzzle) => {
    solve.player?.pause();
    solve.proofId++;
    setPlaying(false);
    solve.replay = solve.player = null;
    solve.board = new Board($("solve-board"), puzzle, { onHover: caption("solve-caption", puzzle.size) });
    solve.board.paint(Array.from(puzzle.grid, (ch) => DIGITS.indexOf(ch) + 1), new Int32Array(puzzle.size ** 2));
    $("log").textContent = "";
    $("solve-summary").textContent = "Pick an algorithm and press Solve.";
    $("solve-summary").className = "verdict idle";
    $("solve-proof").textContent = "";
    ["stat-nodes", "stat-backtracks", "stat-prunes", "stat-checks"].forEach((id) => { $(id).textContent = "0"; });
    $("scrub").max = 0;
    $("scrub-label").textContent = "0 / 0";
  });
}
