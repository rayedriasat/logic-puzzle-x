// Race tab: the same puzzle replayed by several algorithms at one events-per-second rate.
import { post, store, toast } from "./api.js";
import { Board } from "./board.js";
import { Player, Replay } from "./replay.js";

const $ = (id) => document.getElementById(id);
const LABELS = { bt: "Naive", fc: "Forward checking", mrv: "MRV", lcv: "MRV + LCV", mac: "MAC", "mac+": "MAC+", dpll: "SAT (DPLL)" };

let player = null;

function buildCard(result, puzzle) {
  const card = document.createElement("article");
  card.className = "race-card";
  card.innerHTML = `<header><h3>${LABELS[result.algorithm]}</h3><span class="rank"></span></header>
    <div class="race-board"></div>
    <p class="race-stats"><span class="nodes">0</span> nodes · <span class="backs">0</span> backtracks</p>
    <p class="race-note"></p>`;
  const entry = {
    card, result,
    board: new Board(card.querySelector(".race-board"), puzzle),
    replay: new Replay(puzzle, result),
    place: 0,
  };
  return entry;
}

function finishNote({ status, stats, truncated }) {
  const ms = stats.ms.toFixed(1);
  return {
    solved: `Finished in ${ms} ms${truncated ? "; replay capped at 100k events" : ""}`,
    timeout: `Stopped at the ${(stats.ms / 1000).toFixed(0)} s limit, unsolved`,
    unsat: `No solution (${ms} ms)`,
  }[status];
}

function paintCard(entry) {
  const { board, replay, card } = entry;
  board.paint(replay.values, replay.candidates);
  card.querySelector(".nodes").textContent = replay.nodes.toLocaleString();
  card.querySelector(".backs").textContent = replay.backtracks.toLocaleString();
}

async function start() {
  player?.pause();
  const algorithms = [...document.querySelectorAll("#race-picks select")].map((s) => s.value);
  $("race-start").disabled = true;
  $("race-status").textContent = "Running every solver on the server…";
  try {
    const puzzle = store.puzzle;
    const { results } = await post("/api/race", { puzzle: puzzle.grid, algorithms });
    const entries = results.map((r) => buildCard(r, puzzle));
    $("race-grid").replaceChildren(...entries.map((e) => e.card));
    let finished = 0;
    player = new Player(entries.map((e) => e.replay), (batches) => {
      entries.forEach((entry) => {
        paintCard(entry);
        if (entry.replay.done && !entry.place) {
          entry.place = ++finished;
          const solved = entry.result.status === "solved" && !entry.result.truncated;
          entry.card.querySelector(".rank").textContent = solved ? `#${finished}` : "cut off";
          entry.card.querySelector(".race-note").textContent = finishNote(entry.result);
          entry.card.classList.toggle("won", solved && finished === 1);
          if (solved) entry.board.ripple();
        }
      });
      if (!batches) $("race-status").textContent = "Race over. Every board replayed at the same event rate.";
    });
    player.speed = Number($("race-speed").value);
    player.play();
    $("race-status").textContent = "Same puzzle, same event rate.";
  } catch (error) {
    toast(error.message);
    $("race-status").textContent = error.message;
  } finally {
    $("race-start").disabled = false;
  }
}

export function initRace() {
  const defaults = ["bt", "fc", "mrv", "mac"];
  $("race-picks").replaceChildren(...defaults.map((value, i) => {
    const label = document.createElement("label");
    label.textContent = `Board ${i + 1} `;
    const select = document.createElement("select");
    select.innerHTML = Object.entries(LABELS).map(([id, text]) => `<option value="${id}">${text}</option>`).join("");
    select.value = value;
    label.append(select);
    return label;
  }));
  $("race-start").addEventListener("click", start);
  $("race-speed").addEventListener("change", () => { if (player) player.speed = Number($("race-speed").value); });
  store.onPuzzle(() => {
    player?.pause();
    $("race-grid").replaceChildren();
    $("race-status").textContent = "Press Start to run all four on this puzzle.";
  });
}
