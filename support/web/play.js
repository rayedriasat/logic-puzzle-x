// Play tab: the human solves, the engine watches in real time and gives reasoned hints.
import { post, store, toast } from "./api.js";
import { Board, peersOf } from "./board.js";
import { DIGITS, digitOf } from "./replay.js";

const $ = (id) => document.getElementById(id);
const name = (cell, size) => `r${Math.floor(cell / size) + 1}c${(cell % size) + 1}`;

const state = { puzzle: null, board: null, values: [], notes: [], history: [], notesMode: false, won: false,
                started: 0, timer: 0, checkId: 0 };

function grid() {
  return Array.from(state.values, (v) => (v ? DIGITS[v - 1] : ".")).join("");
}

function conflicts() {
  const { size } = state.puzzle;
  const bad = [];
  state.values.forEach((value, cell) => {
    if (!value) return;
    for (const peer of peersOf(cell, size)) if (state.values[peer] === value) { bad.push(cell); break; }
  });
  return bad;
}

function paint() {
  const { board, values, notes, puzzle } = state;
  board.paint(values, notes);
  board.mark("conflict", conflicts());
  const picked = values[board.selected];
  board.mark("same", picked ? values.flatMap((v, i) => (v === picked ? [i] : [])) : []);
  document.querySelectorAll("#pad button").forEach((button) => {
    const value = Number(button.dataset.value);
    const left = puzzle.size - values.filter((v) => v === value).length;
    button.querySelector("small").textContent = left > 0 ? left : "✓";
    button.disabled = left <= 0;
  });
}

function setVerdict(kind, text) {
  const el = $("play-verdict");
  el.className = `verdict ${kind}`;
  el.textContent = text;
}

/** Ask the engine after every move whether the board can still be finished. */
async function liveCheck() {
  const id = ++state.checkId;
  if (conflicts().length) return setVerdict("bad", "Clash: the same digit twice in a row, column or box");
  setVerdict("idle", "Checking…");
  try {
    const body = await post("/api/solve", { puzzle: grid(), algorithm: "mac+", trace: false, timeout: 5 });
    if (id !== state.checkId) return;
    const ms = body.stats.ms.toFixed(1);
    if (body.status === "solved") setVerdict("good", `Still solvable (checked in ${ms} ms)`);
    else if (body.status === "unsat") setVerdict("bad", "No solution from here: one of your digits is wrong");
    else setVerdict("idle", "Too open to check yet");
  } catch (error) {
    if (id === state.checkId) setVerdict("idle", error.message);
  }
}

function won() {
  if (state.values.includes(0) || conflicts().length) return false;
  state.won = true;
  clearInterval(state.timer);
  state.board.ripple();
  setVerdict("good", `Solved in ${$("play-clock").textContent}`);
  return true;
}

function setCell(cell, value) {
  if (state.board.given[cell] || state.won) return;
  state.history.push({ cell, value: state.values[cell], notes: state.notes[cell] });
  if (state.notesMode && value) {
    if (!state.values[cell]) state.notes[cell] ^= 1 << (value - 1);
    state.history.pop();
    paint();
    return;
  }
  state.values[cell] = value;
  state.notes[cell] = 0;
  $("play-hint").textContent = "";
  paint();
  if (!won()) liveCheck();
}

function undo() {
  const last = state.history.pop();
  if (!last || state.won) return;
  state.values[last.cell] = last.value;
  state.notes[last.cell] = last.notes;
  paint();
  liveCheck();
}

async function hint() {
  $("play-hint").textContent = "Thinking…";
  const body = await post("/api/solve", { puzzle: grid(), algorithm: "mac+", explain: true, timeout: 5 });
  if (body.status === "unsat") {
    $("play-hint").textContent = "This board has no solution. Undo until the check above says it is solvable again.";
    return;
  }
  if (body.status !== "solved") {
    $("play-hint").textContent = "The board is too open for a hint yet.";
    return;
  }
  const steps = body.explanation;
  const forced = steps.find((s) => s.kind === "naked" || s.kind === "hidden");
  const useForced = forced && forced === steps[0];
  const step = useForced ? forced : steps[0];
  if (!step) return;
  state.board.select(step.var);
  paint();
  $("play-hint").textContent = useForced ? step.text
    : `${name(step.var, state.puzzle.size)} = ${body.solution[step.var]}: no simple rule forces a cell here, so this comes from search`;
}

function check() {
  const wrong = [];
  post("/api/solve", { puzzle: state.puzzle.grid, algorithm: "mac+", trace: false, timeout: 5 }).then((body) => {
    if (!body.solution) return toast("This puzzle has no solution");
    state.values.forEach((value, cell) => {
      if (value && !state.board.given[cell] && DIGITS[value - 1] !== body.solution[cell]) wrong.push(cell);
    });
    state.board.mark("conflict", wrong);
    $("play-hint").textContent = wrong.length ? `${wrong.length} digit(s) differ from the solution, marked in red.`
      : "Every digit so far matches the solution.";
  }).catch((error) => toast(error.message));
}

function restart() {
  const { puzzle } = state;
  state.values = Array.from(puzzle.grid, digitOf);
  state.notes = new Array(puzzle.size ** 2).fill(0);
  state.history = [];
  state.won = false;
  state.started = Date.now();
  clearInterval(state.timer);
  state.timer = setInterval(tick, 1000);
  tick();
  state.board = new Board($("play-board"), puzzle, {
    onSelect: (cell) => { state.board.select(cell); paint(); },
    onHover: (cell, peers) => {
      $("play-caption").textContent = cell === null
        ? "Hover a cell to see its Markov blanket."
        : `${name(cell, puzzle.size)}: its ${peers} peers are its Markov blanket`;
    },
  });
  $("pad").style.setProperty("--pad-cols", Math.ceil(Math.sqrt(puzzle.size)));
  $("pad").replaceChildren(...Array.from({ length: puzzle.size }, (_, i) => {
    const button = document.createElement("button");
    button.dataset.value = i + 1;
    button.innerHTML = `${DIGITS[i]}<small></small>`;
    button.addEventListener("click", () => {
      if (state.board.selected != null) setCell(state.board.selected, i + 1);
      else toast("Pick a cell first");
    });
    return button;
  }));
  $("play-hint").textContent = "";
  paint();
  liveCheck();
}

function tick() {
  const seconds = Math.floor((Date.now() - state.started) / 1000);
  $("play-clock").textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function keydown(event) {
  if (!state.board) return false;
  const { size } = state.puzzle;
  const key = event.key.toUpperCase();
  const cell = state.board.selected ?? 0;
  const moves = { ARROWLEFT: -1, ARROWRIGHT: 1, ARROWUP: -size, ARROWDOWN: size };
  if (key in moves) {
    const next = cell + moves[key];
    if (next >= 0 && next < size ** 2) { state.board.select(next); paint(); }
    return true;
  }
  if (key === "BACKSPACE" || key === "DELETE" || key === "0") { setCell(cell, 0); return true; }
  if (key === "N") { toggleNotes(); return true; }
  const value = DIGITS.slice(0, size).indexOf(key) + 1;
  if (value && state.board.selected != null) { setCell(cell, value); return true; }
  return false;
}

function toggleNotes() {
  state.notesMode = !state.notesMode;
  $("play-notes").setAttribute("aria-pressed", state.notesMode);
}

export function initPlay(openSolve) {
  store.onPuzzle((puzzle) => { state.puzzle = puzzle; restart(); });
  $("play-notes").addEventListener("click", toggleNotes);
  $("play-erase").addEventListener("click", () => state.board.selected != null && setCell(state.board.selected, 0));
  $("play-undo").addEventListener("click", undo);
  $("play-hint-btn").addEventListener("click", () => hint().catch((error) => toast(error.message)));
  $("play-check").addEventListener("click", check);
  $("play-restart").addEventListener("click", restart);
  $("play-finish").addEventListener("click", () => openSolve(grid()));
}
