import type { Art, MonsterLine } from "./roster";

// Pixel sprites, drawn from a line's Art spec. Pure and deterministic, safe for
// client code. Creatures face the viewer and are mirrored about the centre
// (tails stick out to the right). Later forms are drawn bigger and fiercer.
//
// Each cell holds a colour role (PX); the Sprite component maps roles to
// type colours, so sprites follow the theme tokens.

export const SIZE = 32;
export const PX = { empty: 0, body: 1, light: 2, shade: 3, ink: 4, shine: 5, part: 6, partShade: 7 } as const;

const C = SIZE / 2;
const GROUND = 30;

type Grid = Uint8Array;
type Pt = [number, number];
type Mask = (current: number) => boolean;

const at = (g: Grid, x: number, y: number) => (x >= 0 && x < SIZE && y >= 0 && y < SIZE ? g[y * SIZE + x] : 0);
const put = (g: Grid, x: number, y: number, v: number) => {
  if (x >= 0 && x < SIZE && y >= 0 && y < SIZE) g[y * SIZE + x] = v;
};
const onBody: Mask = (c) => c === PX.body;

function ellipse(g: Grid, cx: number, cy: number, rx: number, ry: number, v: number, mask?: Mask) {
  for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++)
    for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
      const dx = (x + 0.5 - cx) / rx;
      const dy = (y + 0.5 - cy) / ry;
      if (dx * dx + dy * dy <= 1 && (!mask || mask(at(g, x, y)))) put(g, x, y, v);
    }
}

function tri(g: Grid, [a, b, c]: [Pt, Pt, Pt], v: number) {
  const edge = (p: Pt, q: Pt, x: number, y: number) => (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0]);
  const xs = [a[0], b[0], c[0]];
  const ys = [a[1], b[1], c[1]];
  for (let y = Math.floor(Math.min(...ys)); y <= Math.ceil(Math.max(...ys)); y++)
    for (let x = Math.floor(Math.min(...xs)); x <= Math.ceil(Math.max(...xs)); x++) {
      const px = x + 0.5;
      const py = y + 0.5;
      const e = [edge(a, b, px, py), edge(b, c, px, py), edge(c, a, px, py)];
      if (e.every((n) => n >= 0) || e.every((n) => n <= 0)) put(g, x, y, v);
    }
}

/** Draws f once per side: s is -1 (left) or 1 (right); mirror x with C + s * dx. */
const both = (f: (s: 1 | -1) => void) => (f(-1), f(1));

function rng(seed: string) {
  let h = 2166136261;
  for (const ch of seed) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return () => {
    h = (h + 0x6d2b79f5) | 0;
    let t = Math.imul(h ^ (h >>> 15), 1 | h);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Frame = { headY: number; headRx: number; headRy: number; bodyY: number; bodyRx: number; bodyRy: number };

/** Lays out head and body for a build, drawing limbs and the body itself. */
function drawBuild(g: Grid, art: Art, form: number, s: number): Frame {
  const hs = [1.15, 1, 0.95][form];
  switch (art.build) {
    case "blob": {
      const lift = art.tail === "tentacles" ? 4 * s : 0;
      const bodyRx = 9 * s;
      const bodyRy = 7.5 * s;
      const bodyY = GROUND - lift - bodyRy - 0.8;
      if (!lift) both((d) => ellipse(g, C + d * bodyRx * 0.5, GROUND - 1, 2 * s + 0.4, 1.4, PX.body));
      ellipse(g, C, bodyY, bodyRx, bodyRy, PX.body);
      return { headY: bodyY - bodyRy * 0.25, headRx: bodyRx * 0.85, headRy: bodyRy * 0.75, bodyY, bodyRx, bodyRy };
    }
    case "biped": {
      const bodyRx = 5.5 * s;
      const bodyRy = 5.5 * s;
      const bodyY = GROUND - 2.5 * s - bodyRy;
      const headRx = 6.8 * s * hs;
      const headRy = headRx * 0.9;
      both((d) => ellipse(g, C + d * 2.8 * s, GROUND - 2 * s, 1.8 * s + 0.3, 2.3 * s, PX.body));
      both((d) => ellipse(g, C + d * (bodyRx + 0.6 * s), bodyY - s, 1.6 * s + 0.3, 2.6 * s, PX.body));
      ellipse(g, C, bodyY, bodyRx, bodyRy, PX.body);
      const headY = bodyY - bodyRy - headRy * 0.55;
      ellipse(g, C, headY, headRx, headRy, PX.body);
      return { headY, headRx, headRy, bodyY, bodyRx, bodyRy };
    }
    case "quad": {
      const bodyRx = 8.5 * s;
      const bodyRy = 4.8 * s;
      const bodyY = GROUND - 3 * s - bodyRy;
      const headRx = 6.2 * s * hs;
      const headRy = headRx * 0.85;
      both((d) => {
        ellipse(g, C + d * 6.2 * s, GROUND - 2.2 * s, 1.7 * s + 0.3, 2.6 * s, PX.body);
        ellipse(g, C + d * 2.6 * s, GROUND - 2 * s, 1.7 * s + 0.3, 2.4 * s, PX.body);
      });
      ellipse(g, C, bodyY, bodyRx, bodyRy, PX.body);
      const headY = bodyY - bodyRy - headRy * 0.2;
      ellipse(g, C, headY, headRx, headRy, PX.body);
      return { headY, headRx, headRy, bodyY, bodyRx, bodyRy };
    }
    case "bird": {
      const bodyRx = 6.8 * s;
      const bodyRy = 7.2 * s;
      const bodyY = GROUND - 1.6 * s - bodyRy;
      const headRx = 5.8 * s * hs;
      const headRy = headRx * 0.9;
      ellipse(g, C, bodyY, bodyRx, bodyRy, PX.body);
      const headY = bodyY - bodyRy * 0.55;
      ellipse(g, C, headY, headRx, headRy, PX.body);
      return { headY, headRx, headRy, bodyY, bodyRx, bodyRy };
    }
    case "serpent": {
      let y = GROUND;
      for (let i = 0; i <= form; i++) {
        const rx = (9.5 - i * 1.7) * s;
        const ry = 2.8 * s + 0.3;
        ellipse(g, C, y - ry, rx, ry, PX.body);
        y -= ry * 1.45;
      }
      const neckY = y - 2 * s;
      ellipse(g, C, neckY, 2.8 * s, 3.2 * s, PX.body);
      const headRx = 5.6 * s * hs;
      const headRy = headRx * 0.8;
      const headY = neckY - 2.5 * s - headRy * 0.6;
      ellipse(g, C, headY, headRx, headRy, PX.body);
      return { headY, headRx, headRy, bodyY: GROUND - 3 * s, bodyRx: 9.5 * s, bodyRy: 2.8 * s };
    }
  }
}

function drawBehind(g: Grid, art: Art, form: number, s: number, f: Frame) {
  const { bodyY, bodyRx, bodyRy } = f;
  if (art.wings && form + 1 >= art.wings) {
    if (art.build === "bird")
      both((d) =>
        tri(g, [[C + d * bodyRx * 0.5, bodyY - 2.5 * s], [C + d * (bodyRx + 3.8 * s), bodyY + 0.5 * s], [C + d * bodyRx * 0.6, bodyY + bodyRy * 0.75]], PX.part),
      );
    else
      both((d) =>
        tri(g, [[C + d * bodyRx * 0.3, bodyY - bodyRy * 0.7], [C + d * (bodyRx + 7 * s), bodyY - bodyRy - 7 * s], [C + d * (bodyRx + 4.5 * s), bodyY + s]], PX.part),
      );
  }
  if (art.shell) {
    const r = bodyRx * 0.85;
    const y = bodyY - bodyRy * 0.85;
    ellipse(g, C, y, r, r, PX.partShade);
    ellipse(g, C, y, r - 1, r - 1, PX.part);
    ellipse(g, C + 0.5, y + 0.5, r * 0.55, r * 0.55, PX.partShade);
    ellipse(g, C + 0.5, y + 0.5, r * 0.55 - 1, r * 0.55 - 1, PX.part);
  }
  switch (art.tail) {
    case "short":
      ellipse(g, C + bodyRx + 0.5 * s, bodyY - s, 2.2 * s + 0.3, 1.6 * s + 0.3, PX.body);
      break;
    case "long":
      for (let k = 0; k < 5; k++)
        ellipse(g, C + bodyRx * 0.8 + k * 1.9 * s, bodyY + bodyRy * 0.4 - k * k * 0.45 * s, (2.2 - k * 0.32) * s + 0.4, (2.2 - k * 0.32) * s + 0.4, PX.body);
      break;
    case "fluffy":
      ellipse(g, C + bodyRx + 0.8 * s, bodyY + bodyRy * 0.15, 3 * s + 0.3, 3 * s + 0.3, PX.light);
      break;
    case "tentacles":
      for (const k of [-2, -1, 0, 1, 2])
        for (let t = 0; t <= 6 * s; t += 0.5) {
          const x = C + k * 2.4 * s + Math.sin(t * 1.3 + k) * 0.8;
          put(g, Math.floor(x), Math.floor(bodyY + bodyRy * 0.7 + t), PX.part);
        }
      break;
  }
}

function drawEars(g: Grid, art: Art, form: number, s: number, f: Frame) {
  const { headY, headRx, headRy } = f;
  const top = headY - headRy;
  switch (art.ears) {
    case "pointy":
      both((d) => {
        tri(g, [[C + d * headRx * 0.25, top + 2.5], [C + d * headRx * 0.95, top + 3], [C + d * headRx * 0.85, top - 3.5 * s]], PX.body);
        tri(g, [[C + d * headRx * 0.45, top + 2], [C + d * headRx * 0.8, top + 2.3], [C + d * headRx * 0.78, top - 1.5 * s]], PX.light);
      });
      break;
    case "long":
      both((d) => {
        ellipse(g, C + d * headRx * 0.42, top - 3.5 * s, 1.7 * s + 0.4, 5.5 * s, PX.body);
        ellipse(g, C + d * headRx * 0.42, top - 3 * s, 0.7 * s + 0.2, 4 * s, PX.light);
      });
      break;
    case "round":
      both((d) => ellipse(g, C + d * headRx * 0.75, top + 1.2, 2.4 * s + 0.5, 2.4 * s + 0.5, PX.part));
      break;
    case "gills":
      both((d) => {
        for (let k = 0; k < 3; k++)
          ellipse(g, C + d * (headRx + 0.8 * s), headY - headRy * 0.6 + k * 2.3 * s, 2.4 * s + 0.3, 0.9, PX.part);
      });
      break;
    case "horns":
      // Ram horns: a thick arc from the crown, over the top, curling down past the ear.
      both((d) => {
        const r = 1.8 + form * 0.9;
        const cx = C + d * (headRx * 0.6 + r * 0.4);
        const cy = top + 0.5;
        for (let t = 0; t <= 1; t += 0.05) {
          const a = Math.PI - t * 1.5 * Math.PI;
          const w = (1.5 - t * 0.7) * (0.7 + s * 0.4);
          ellipse(g, cx + d * r * Math.cos(a), cy - r * Math.sin(a), w, w, PX.part);
        }
      });
      break;
    case "antenna":
      both((d) => {
        const tx = C + d * (headRx * 0.55 + form * 0.6);
        const ty = top - 3 - form;
        for (let t = 0; t <= 1; t += 0.1) put(g, Math.floor(C + d * headRx * 0.3 + (tx - C - d * headRx * 0.3) * t), Math.floor(top + 1 + (ty - top - 1) * t), PX.ink);
        ellipse(g, tx, ty, 1.3, 1.3, PX.part);
      });
      break;
    case "fin":
      tri(g, [[C - 2.6 * s, top + 1.5], [C + 2.6 * s, top + 1.5], [C, top - 2.5 - 2 * s]], PX.part);
      break;
    case "leaf":
      both((d) => {
        const stem = top - 1 - form;
        tri(g, [[C, top + 2], [C + d * (3 + form * 1.5), stem - 2 - form], [C + d * (4 + form), stem + 1]], PX.part);
      });
      break;
    case "crest":
      for (const [dx, h] of [[-2.2, 2.5], [0, 4], [2.2, 2.5]] as const)
        tri(g, [[C + dx - 1.1, top + 1.5], [C + dx + 1.1, top + 1.5], [C + dx * 1.3, top - h * s - 0.5]], PX.part);
      break;
  }
  if (art.spikes && form === 2)
    for (const [dx, h] of [[-4.5, 2.5], [0, 4], [4.5, 2.5]] as const)
      tri(g, [[C + dx * s - 1.6, top + 1.5], [C + dx * s + 1.6, top + 1.5], [C + dx * s * 1.15, top - h * s]], PX.part);
}

function drawFace(g: Grid, art: Art, form: number, s: number, f: Frame, rand: () => number) {
  const { headY, headRx, headRy, bodyY, bodyRx, bodyRy } = f;
  switch (art.pattern) {
    case "belly":
      ellipse(g, C, bodyY + bodyRy * 0.25, bodyRx * 0.6, bodyRy * 0.62, PX.light, onBody);
      break;
    case "spots":
      for (let i = 0; i < 3 + form * 2; i++) {
        const x = C + (rand() * 2 - 1) * bodyRx * 0.8;
        const y = bodyY + (rand() * 2 - 1) * bodyRy * 0.7;
        const r = 0.8 + rand() * 0.9 * s;
        ellipse(g, x, y, r, r, PX.part, onBody);
      }
      break;
    case "stripes":
      for (let y = Math.floor(headY - headRy); y < SIZE; y += 3)
        for (let x = 0; x < SIZE; x++) if (Math.abs(x + 0.5 - C) > 3 && at(g, x, y) === PX.body) put(g, x, y, PX.part);
      break;
  }

  const eyeH = form === 0 ? 3 : 2;
  const eyeY = Math.round(headY - headRy * 0.1 - eyeH / 2);
  const eyeX = Math.round(C - Math.max(2.5, headRx * 0.42) - 1); // left pixel of the left eye
  if (art.pattern === "mask") both((d) => ellipse(g, C + d * (C - eyeX - 1), eyeY + eyeH / 2, 2.6, 2.4, PX.part));
  for (const x of [eyeX, SIZE - 2 - eyeX])
    for (let dy = 0; dy < eyeH; dy++) put(g, x, eyeY + dy, PX.ink), put(g, x + 1, eyeY + dy, PX.ink);
  put(g, eyeX, eyeY, PX.shine);
  put(g, SIZE - 2 - eyeX, eyeY, PX.shine);
  if (form === 2) {
    // Brows slanting down toward the middle: final forms look fierce.
    for (const [x, y] of [[eyeX - 1, eyeY - 2], [eyeX, eyeY - 2], [eyeX + 1, eyeY - 1], [eyeX + 2, eyeY - 1]])
      put(g, x, y, PX.ink), put(g, SIZE - 1 - x, y, PX.ink);
  }

  const m = eyeY + eyeH + 1;
  switch (art.face) {
    case "beak":
      tri(g, [[C - 2 - s, m - 1], [C + 2 + s, m - 1], [C, m + 2 + s]], PX.part);
      break;
    case "snout":
      ellipse(g, C, m + 0.8, 2.5 * s + 0.8, 1.6 * s + 0.6, PX.light);
      put(g, C - 1, m, PX.ink), put(g, C, m, PX.ink);
      break;
    case "fangs":
      for (let x = C - 2; x < C + 2; x++) put(g, x, m + 1, PX.ink);
      put(g, C - 2, m + 2, PX.shine), put(g, C + 1, m + 2, PX.shine);
      break;
    case "smile":
      put(g, C - 2, m, PX.ink), put(g, C - 1, m + 1, PX.ink), put(g, C, m + 1, PX.ink), put(g, C + 1, m, PX.ink);
      break;
  }
  if (art.build === "bird") both((d) => tri(g, [[C + d * 2 * s - 1, GROUND - 1.6 * s], [C + d * 2 * s + 1, GROUND - 1.6 * s], [C + d * 2 * s, GROUND]], PX.part));
}

/** Shades the lower-right rim of each colour, then outlines the whole figure. */
function finish(g: Grid): Grid {
  const shaded = g.slice();
  for (let y = 0; y < SIZE; y++)
    for (let x = 0; x < SIZE; x++) {
      const v = at(g, x, y);
      if ((v === PX.body || v === PX.part) && (at(g, x + 1, y) === 0 || at(g, x, y + 1) === 0))
        put(shaded, x, y, v === PX.body ? PX.shade : PX.partShade);
    }
  const out = shaded.slice();
  for (let y = 0; y < SIZE; y++)
    for (let x = 0; x < SIZE; x++)
      if (at(shaded, x, y) === 0 && [at(shaded, x - 1, y), at(shaded, x + 1, y), at(shaded, x, y - 1), at(shaded, x, y + 1)].some((v) => v && v !== PX.ink))
        put(out, x, y, PX.ink);
  return out;
}

export function drawSprite(line: MonsterLine, form: number): Grid {
  const g = new Uint8Array(SIZE * SIZE);
  const s = [0.6, 0.8, 1][form];
  const rand = rng(`${line.id}/${form}`);
  // Lay out once on a scratch grid to learn where the head goes, so parts
  // behind the body can be drawn first.
  const frame = drawBuild(new Uint8Array(SIZE * SIZE), line.art, form, s);
  drawBehind(g, line.art, form, s, frame);
  drawEars(g, line.art, form, s, frame);
  drawBuild(g, line.art, form, s);
  drawFace(g, line.art, form, s, frame, rand);
  return finish(g);
}

export type Run = { x: number; y: number; w: number; v: number };

/** A square around the drawn pixels, so small forms fill the frame too. */
export type Box = { x: number; y: number; size: number };

const cache = new Map<string, { runs: Run[]; box: Box }>();

/** The sprite as horizontal runs of one colour role, for compact SVG, plus its bounding square. */
export function spriteRuns(line: MonsterLine, form: number): { runs: Run[]; box: Box } {
  const key = `${line.id}/${form}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const g = drawSprite(line, form);
  const runs: Run[] = [];
  let [x0, y0, x1, y1] = [SIZE, SIZE, 0, 0];
  for (let y = 0; y < SIZE; y++)
    for (let x = 0; x < SIZE; ) {
      const v = g[y * SIZE + x];
      let w = 1;
      while (x + w < SIZE && g[y * SIZE + x + w] === v) w++;
      if (v) {
        runs.push({ x, y, w, v });
        [x0, y0, x1, y1] = [Math.min(x0, x), Math.min(y0, y), Math.max(x1, x + w), Math.max(y1, y + 1)];
      }
      x += w;
    }
  const size = Math.max(x1 - x0, y1 - y0) + 2;
  // Centred across, standing on the bottom edge.
  const box = { x: (x0 + x1 - size) / 2, y: y1 + 1 - size, size };
  const out = { runs, box };
  cache.set(key, out);
  return out;
}
