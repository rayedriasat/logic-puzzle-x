// Generate tab: new puzzles with exactly one solution, graded Easy to Extreme.
import { post, toast, toPuzzle, store } from "./api.js";
import { Board } from "./board.js";
import { digitOf } from "./replay.js";

const $ = (id) => document.getElementById(id);
let current = null;

async function generate() {
  $("generate-run").disabled = true;
  $("generate-info").textContent = "Filling a grid, then removing clues while the solution stays unique…";
  $("generate-actions").hidden = true;
  try {
    const body = await post("/api/generate", { size: Number($("generate-size").value), difficulty: $("generate-difficulty").value });
    current = toPuzzle(body.puzzle, `Generated ${body.size}×${body.size} ${body.grade}`);
    const board = new Board($("generate-board"), current, { marks: false });
    board.paint(Int32Array.from(current.grid, digitOf), new Int32Array(current.size ** 2));
    const note = body.grade === body.requested ? "" : ` · closest to ${body.requested} a ${body.size}×${body.size} grid reached`;
    $("generate-info").innerHTML = `<strong>${body.grade}</strong> · ${body.clues} clues${note}<br>
      Unique ✓: KB ∪ {¬s} is unsatisfiable, so KB ⊨ s`;
    $("generate-actions").hidden = false;
  } catch (error) {
    toast(error.message);
    $("generate-info").textContent = error.message;
  } finally {
    $("generate-run").disabled = false;
  }
}

export function initGenerate(openTab) {
  $("generate-run").addEventListener("click", generate);
  $("generate-play").addEventListener("click", () => { store.setPuzzle(current); openTab("play"); });
  $("generate-watch").addEventListener("click", () => { store.setPuzzle(current); openTab("solve", true); });
}
