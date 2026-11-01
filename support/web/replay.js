// Trace replay: rebuilds board state from the solver's event log (plan.md section 3.6).
// One engine drives every animation; Race mode is just several of these side by side.

export const DIGITS = "123456789ABCDEFGHIJKLMNOP";
export const digitOf = (ch) => DIGITS.indexOf(ch) + 1; // 0 for "."

export class Replay {
  constructor(puzzle, result) {
    this.size = puzzle.size;
    this.grid = puzzle.grid;
    this.events = result.events;
    this.result = result;
    this.reset();
  }

  reset() {
    const full = (1 << this.size) - 1;
    this.values = Int32Array.from(this.grid, digitOf);
    this.candidates = Int32Array.from(this.values, (v) => (v ? 0 : full)); // bit v-1 = value v still possible
    this.frames = [[]]; // frames.at(-1) holds the prunes a "B" must undo
    this.pos = 0;
    this.nodes = this.backtracks = this.prunes = 0;
    this.solved = false;
  }

  get done() { return this.pos >= this.events.length; }

  /** Apply one event; returns the event so the caller can animate it. */
  step() {
    const event = this.events[this.pos++];
    const [kind, cell, value] = event;
    if (kind === "A") {
      this.values[cell] = value;
      this.frames.push([]);
      this.nodes++;
    } else if (kind === "P") {
      const bit = 1 << (value - 1);
      if (this.candidates[cell] & bit) {
        this.candidates[cell] &= ~bit;
        this.frames.at(-1).push(cell, bit);
      }
      this.prunes++;
    } else if (kind === "B") {
      const frame = this.frames.pop();
      for (let i = 0; i < frame.length; i += 2) this.candidates[frame[i]] |= frame[i + 1];
      this.values[cell] = 0;
      this.backtracks++;
    } else if (kind === "S") {
      this.solved = true;
    }
    return event;
  }

  /** Jump to any position: replaying 100k events from the start costs about a millisecond. */
  seek(pos) {
    if (pos < this.pos) this.reset();
    while (this.pos < pos && !this.done) this.step();
  }
}

/** Plays replays at one shared events-per-second rate on animation frames. */
export class Player {
  constructor(replays, onFrame) {
    this.replays = replays;
    this.onFrame = onFrame; // (touchedEventsPerReplay, batchSize) after each batch
    this.speed = 40;
    this.playing = false;
    this.budget = 0;
    this.last = 0;
  }

  play() {
    if (this.playing || this.replays.every((r) => r.done)) return;
    this.playing = true;
    this.last = performance.now();
    requestAnimationFrame((t) => this.tick(t));
  }

  pause() { this.playing = false; }

  tick(now) {
    if (!this.playing) return;
    this.budget += ((now - this.last) / 1000) * this.speed;
    this.last = now;
    const count = Math.floor(this.budget);
    if (count > 0) {
      this.budget -= count;
      this.advance(count);
    }
    if (this.replays.every((r) => r.done)) {
      this.playing = false;
      this.onFrame(null, 0);
      return;
    }
    requestAnimationFrame((t) => this.tick(t));
  }

  advance(count) {
    const batches = this.replays.map((r) => {
      const events = [];
      for (let i = 0; i < count && !r.done; i++) events.push(r.step());
      return events;
    });
    this.onFrame(batches, count);
  }
}
