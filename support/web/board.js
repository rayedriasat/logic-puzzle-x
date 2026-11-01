// The Sudoku board: one component for Play, Solve, Race, Explain and Generate.
import { DIGITS } from "./replay.js";

export function boxShape(size) {
  let rows = Math.floor(Math.sqrt(size));
  while (size % rows) rows--;
  return [rows, size / rows];
}

/** Markov blanket of a cell: every other cell in its row, column or box. */
export function peersOf(cell, size) {
  const [br, bc] = boxShape(size);
  const row = Math.floor(cell / size), col = cell % size;
  const found = new Set();
  for (let i = 0; i < size; i++) {
    found.add(row * size + i);
    found.add(i * size + col);
    const r = row - (row % br) + Math.floor(i / bc), c = col - (col % bc) + (i % bc);
    found.add(r * size + c);
  }
  found.delete(cell);
  return found;
}

const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export class Board {
  constructor(root, puzzle, { marks = true, onSelect = null, onHover = null } = {}) {
    this.size = puzzle.size;
    this.marks = marks;
    this.onSelect = onSelect;
    this.given = Array.from(puzzle.grid, (ch) => ch !== ".");
    this.shown = new Array(this.size ** 2).fill(null);
    this.markup = new Map();
    const [br, bc] = boxShape(this.size);

    this.el = document.createElement("div");
    this.el.className = "board";
    this.el.style.setProperty("--n", this.size);
    this.el.style.setProperty("--mark-cols", Math.ceil(Math.sqrt(this.size)));
    this.el.setAttribute("role", "grid");
    this.el.setAttribute("aria-label", `${this.size} by ${this.size} Sudoku board`);
    this.cells = [...puzzle.grid].map((ch, i) => {
      const cell = document.createElement("div");
      const row = Math.floor(i / this.size), col = i % this.size;
      cell.className = "cell";
      cell.setAttribute("role", "gridcell");
      cell.classList.toggle("given", ch !== ".");
      cell.classList.toggle("box-right", (col + 1) % bc === 0 && col + 1 < this.size);
      cell.classList.toggle("box-bottom", (row + 1) % br === 0 && row + 1 < this.size);
      cell.dataset.cell = i;
      this.el.append(cell);
      return cell;
    });

    if (onSelect) {
      this.el.tabIndex = 0;
      this.el.addEventListener("click", (e) => {
        const cell = e.target.closest(".cell");
        if (cell) onSelect(Number(cell.dataset.cell));
      });
    }
    this.el.addEventListener("pointerover", (e) => {
      const cell = e.target.closest(".cell");
      if (!cell) return;
      const index = Number(cell.dataset.cell);
      this.highlightPeers(index);
      onHover?.(index, peersOf(index, this.size).size);
    });
    this.el.addEventListener("pointerleave", () => {
      this.highlightPeers(this.selected ?? null);
      onHover?.(null, 0);
    });
    root.replaceChildren(this.el);
  }

  marksHtml(mask, gone) {
    const key = mask * 70000 + gone;
    if (this.markup.has(key)) return this.markup.get(key);
    let html = '<span class="marks">';
    for (let v = 0; v < this.size; v++) {
      const bit = 1 << v;
      html += mask & bit ? `<i>${DIGITS[v]}</i>` : gone & bit ? `<i class="gone">${DIGITS[v]}</i>` : "<i></i>";
    }
    html += "</span>";
    if (!gone) this.markup.set(key, html);
    return html;
  }

  /** Draw values and candidate masks. Only cells that changed touch the DOM. */
  paint(values, candidates, { animate = false } = {}) {
    for (let i = 0; i < this.cells.length; i++) {
      const value = values[i], mask = candidates[i];
      const key = value ? -value : mask;
      const before = this.shown[i];
      if (key === before) continue;
      this.shown[i] = key;
      const el = this.cells[i];
      if (value) {
        el.textContent = DIGITS[value - 1];
        el.classList.toggle("solver", !this.given[i]);
        if (animate && !this.given[i] && !calm()) {
          el.animate([{ transform: "scale(.5)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }], 160);
        }
      } else {
        el.classList.remove("solver");
        const gone = animate && before > 0 ? before & ~mask : 0;
        el.innerHTML = this.marks && (mask || gone) ? this.marksHtml(mask, gone) : "";
      }
    }
  }

  flash(cell) {
    if (calm()) return;
    this.cells[cell].animate([
      { background: "var(--rose-soft)", transform: "translateX(-2px)" },
      { background: "var(--rose-soft)", transform: "translateX(2px)", offset: 0.35 },
      { background: "transparent", transform: "translateX(0)" },
    ], 260);
  }

  ripple() {
    if (calm()) return;
    const center = (this.size - 1) / 2;
    this.cells.forEach((el, i) => {
      const distance = Math.hypot(Math.floor(i / this.size) - center, (i % this.size) - center);
      el.animate([{ background: "transparent" }, { background: "var(--emerald-soft)" }, { background: "transparent" }],
        { duration: 650, delay: distance * (540 / this.size) });
    });
  }

  select(cell) {
    this.selected = cell;
    this.cells.forEach((el, i) => el.classList.toggle("selected", i === cell));
    this.highlightPeers(cell);
    if (cell !== null) this.el.setAttribute("aria-activedescendant", (this.cells[cell].id ||= `cell-${cell}`));
  }

  highlightPeers(cell) {
    const peers = cell === null ? new Set() : peersOf(cell, this.size);
    this.cells.forEach((el, i) => el.classList.toggle("peer", peers.has(i)));
  }

  /** Put `className` on exactly these cells. */
  mark(className, cells) {
    const set = new Set(cells);
    this.cells.forEach((el, i) => el.classList.toggle(className, set.has(i)));
  }

  setEntry(cell, given) {
    this.given[cell] = given;
    this.cells[cell].classList.toggle("given", given);
  }
}
