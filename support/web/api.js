// Thin wrappers around the JSON API, plus the puzzle every tab shares.
import { boxShape } from "./board.js";
import { DIGITS } from "./replay.js";

// The static build has no server: the same Python API runs in Web Workers (see config.js).
// Each worker handles one request at a time, so slow jobs (uniqueness proofs, generation) get their
// own worker and never hold up the quick solves that Play and Watch it think wait on.
const workers = {};
let nextId = 0;
const pending = new Map();

function startWorker() {
  const worker = new Worker(new URL("./pyworker.js", import.meta.url), { type: "module" });
  worker.onmessage = ({ data }) => {
    const { resolve, reject } = pending.get(data.id);
    pending.delete(data.id);
    if (data.status === 0) return reject(new Error(`Solver failed to start: ${data.error}`));
    if (data.status !== 200) {
      return reject(new Error(typeof data.body?.detail === "string" ? data.body.detail : `Request failed (${data.status})`));
    }
    resolve(data.body);
  };
  return worker;
}

function workerRequest(path, options = {}) {
  const body = options.body ?? null;
  const slow = path === "/api/generate" || (body !== null && JSON.parse(body).prove === true);
  const lane = slow ? "slow" : "fast";
  workers[lane] ??= startWorker();
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    workers[lane].postMessage({ id, method: options.method ?? "GET", url: path, body });
  });
}

async function request(path, options) {
  if (window.LPX_BACKEND === "pyodide") {
    // Benchmarks are precomputed into a JSON file at build time; everything else runs in the worker.
    if (path === "/api/benchmarks") path = "benchmarks.json";
    else return workerRequest(path, options);
  }
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  return body;
}

export const get = (path) => request(path);
export const post = (path, body) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

/** Normalize a grid string the same way support/sudoku.py parse() does. */
export function toPuzzle(text, name = "") {
  const grid = text.replace(/\s/g, "").toUpperCase().replaceAll("0", ".");
  const size = Math.round(Math.sqrt(grid.length));
  if (!grid || size * size !== grid.length) throw new Error(`A Sudoku has N×N cells; got ${grid.length} characters`);
  const allowed = `.${DIGITS.slice(0, size)}`;
  const bad = [...new Set(grid)].filter((ch) => !allowed.includes(ch));
  if (bad.length) throw new Error(`Not valid in a ${size}×${size} Sudoku: ${bad.join(" ")}`);
  return { size, box: boxShape(size), grid, name };
}

/** The current puzzle, shared across tabs. Views subscribe with onPuzzle(). */
export const store = {
  puzzle: null,
  listeners: [],
  onPuzzle(fn) { this.listeners.push(fn); },
  setPuzzle(puzzle) {
    this.puzzle = puzzle;
    this.listeners.forEach((fn) => fn(puzzle));
  },
};

export function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 3600);
}
