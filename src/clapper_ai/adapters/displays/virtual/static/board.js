// Virtual split-flap board: renders grids of tile codes on a <canvas>
// and flips tiles to their new value when a new grid arrives.
//
// Tile codes mirror src/clapper_ai/domain/tile_codes.py:
//   0 blank, 1-26 A-Z, 27-36 digits 1..9,0, 63-69 color tiles.

"use strict";

// --- code table (mirror of domain/tile_codes.py) ----------------------------

const CODE_TO_CHAR = { 0: " " };
"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").forEach((ch, i) => { CODE_TO_CHAR[i + 1] = ch; });
"1234567890".split("").forEach((ch, i) => { CODE_TO_CHAR[i + 27] = ch; });

const COLOR_TILES = {
  63: "#e03e36", // red
  64: "#e87e26", // orange
  65: "#e8c231", // yellow
  66: "#3ba550", // green
  67: "#3673c6", // blue
  68: "#8a4fc8", // violet
  69: "#e8e6e3", // white
};

// --- board geometry and drawing ---------------------------------------------

const TILE_W = 40;
const TILE_H = 56;
const GAP = 5;
const FLIP_MS = 260;      // duration of one tile's flip
const STAGGER_MS = 7;     // delay between neighbouring tiles, for the wave

const canvas = document.getElementById("board");
const ctx = canvas.getContext("2d");
const status = document.getElementById("status");

let rows = 0;
let cols = 0;
// Per tile: the code currently shown, the code to flip to, and when the flip starts.
let tiles = [];

function resizeBoard(newRows, newCols) {
  rows = newRows;
  cols = newCols;
  canvas.width = cols * (TILE_W + GAP) + GAP;
  canvas.height = rows * (TILE_H + GAP) + GAP;
  tiles = Array.from({ length: rows * cols }, () => ({ shown: 0, target: 0, flipAt: null }));
}

function showGrid(grid) {
  const now = performance.now();
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const tile = tiles[r * cols + c];
      const code = grid[r][c];
      if (code !== tile.target) {
        tile.target = code;
        tile.flipAt = now + (r * cols + c) * STAGGER_MS;
      }
    }
  }
}

function drawTile(x, y, code, squish) {
  // squish is the vertical scale during a flip: 1 → 0 → 1.
  const h = TILE_H * squish;
  const yMid = y + TILE_H / 2;

  ctx.fillStyle = COLOR_TILES[code] || "#26272c";
  roundRect(x, yMid - h / 2, TILE_W, h, 4);
  ctx.fill();

  const char = CODE_TO_CHAR[code];
  if (char && char !== " " && !(code in COLOR_TILES)) {
    ctx.fillStyle = "#f2f0eb";
    ctx.font = `bold ${Math.round(30 * squish)}px ui-monospace, Menlo, Consolas, monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(char, x + TILE_W / 2, yMid + 1);
  }

  // The horizontal split line that makes it read as a split-flap tile.
  if (squish > 0.5) {
    ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
    ctx.fillRect(x, yMid - 0.75, TILE_W, 1.5);
  }
}

function roundRect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, Math.max(h, 1), r);
}

function frame(now) {
  ctx.fillStyle = "#17181c";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const tile = tiles[r * cols + c];
      const x = GAP + c * (TILE_W + GAP);
      const y = GAP + r * (TILE_H + GAP);

      if (tile.flipAt === null || now < tile.flipAt) {
        drawTile(x, y, tile.shown, 1);
        continue;
      }
      const t = (now - tile.flipAt) / FLIP_MS;
      if (t >= 1) {
        tile.shown = tile.target;
        tile.flipAt = null;
        drawTile(x, y, tile.shown, 1);
      } else if (t < 0.5) {
        drawTile(x, y, tile.shown, 1 - t * 2);       // old face folds away
      } else {
        drawTile(x, y, tile.target, t * 2 - 1);      // new face unfolds
      }
    }
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

// --- WebSocket wiring --------------------------------------------------------

function connect() {
  const socket = new WebSocket(`ws://${location.host}/ws`);

  socket.onmessage = (event) => {
    const { rows: r, cols: c, grid } = JSON.parse(event.data);
    if (r !== rows || c !== cols) resizeBoard(r, c);
    showGrid(grid);
  };
  socket.onopen = () => { status.textContent = "connected — type in the terminal"; };
  socket.onclose = () => {
    status.textContent = "disconnected — retrying…";
    setTimeout(connect, 1000);
  };
}
connect();
