// Placeholder landing page: draws a preview board and checks that the API is up.
const PREVIEW = "8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..";

function drawBoard(grid) {
  const board = document.getElementById("board");
  [...grid].forEach((ch, i) => {
    const row = Math.floor(i / 9);
    const col = i % 9;
    const cell = document.createElement("div");
    cell.className = "cell";
    if (ch !== ".") cell.classList.add("given");
    if (col === 2 || col === 5) cell.classList.add("box-right");
    if (row === 2 || row === 5) cell.classList.add("box-bottom");
    cell.textContent = ch === "." ? "" : ch;
    cell.style.animationDelay = `${(row + col) * 35}ms`;
    board.appendChild(cell);
  });
}

async function checkHealth() {
  const status = document.getElementById("status");
  const text = document.getElementById("status-text");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    status.classList.add("ok");
    text.textContent = `Solver API online · v${data.version}`;
  } catch {
    status.classList.add("down");
    text.textContent = "Solver API offline";
  }
}

drawBoard(PREVIEW);
checkHealth();
