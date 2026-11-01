// Thin wrappers around the JSON API, plus the puzzle every tab shares.
import { boxShape } from "./board.js";
import { DIGITS } from "./replay.js";

async function request(path, options) {
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
