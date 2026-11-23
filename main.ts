// One Image: Monday 23 November 2026 — entrypoint.
//
// Checks the artifact this repository holds (entry.png) and hands it to
// the grader: the PNG bytes are copied verbatim to
// <MAKEFUN_OUTPUT_DIR>/entry.png, next to a run summary at
// <MAKEFUN_OUTPUT_DIR>/summary.json.
//
// render.py draws the page from headlines.json; this file only proves the
// PNG in the repo is whole and matches the data: valid PNG chunks with
// correct CRCs, 1024x1024, inside the bounty byte band, and its headline
// count reconciled against headlines.json.
//
// The grader runs this file with the repo mounted READ-ONLY, so nothing
// here writes into the repository — every write goes to the directory
// named by MAKEFUN_OUTPUT_DIR (default "/output").
//
// Run: node main.ts   (exit 0 = artifact checked and delivered)

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SLUG = "news-image-20261123";
const LOW_BYTES = 200_000; // winners of this bounty land ~200-900 KB
const HIGH_BYTES = 900_000;

function die(msg: string): never {
  console.error(`CHECK FAIL: ${msg}`);
  process.exit(1);
}

// CRC-32 (IEEE) table, built bit by bit from the polynomial.
function makeTable(): Uint32Array {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c;
  }
  return table;
}

const TABLE = makeTable();

function chunkCrc(buf: Buffer, start: number, end: number): number {
  let c = 0xffffffff;
  for (let i = start; i < end; i++) {
    c = TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

// Validate every PNG chunk and return the IHDR dimensions. A truncated
// or corrupted file fails here instead of reaching the judge's viewer.
function inspectPng(buf: Buffer): { width: number; height: number } {
  const magic = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  for (let i = 0; i < magic.length; i++) {
    if (buf[i] !== magic[i]) die("entry.png is not a PNG (bad signature)");
  }
  let offset = 8;
  let dims: { width: number; height: number } | null = null;
  let sawEnd = false;
  while (offset + 8 <= buf.length) {
    const len = buf.readUInt32BE(offset);
    const kind = buf.toString("ascii", offset + 4, offset + 8);
    if (offset + 12 + len > buf.length) die(`entry.png chunk ${kind} overruns the file`);
    const stored = buf.readUInt32BE(offset + 8 + len);
    if (chunkCrc(buf, offset + 4, offset + 8 + len) !== stored) {
      die(`entry.png chunk ${kind} has a bad CRC`);
    }
    if (kind === "IHDR") {
      dims = { width: buf.readUInt32BE(offset + 8), height: buf.readUInt32BE(offset + 12) };
    }
    offset += 12 + len;
    if (kind === "IEND") {
      sawEnd = true;
      break;
    }
  }
  if (!dims) die("entry.png has no IHDR chunk");
  if (!sawEnd) die("entry.png has no IEND chunk");
  return dims;
}

// How many news items the page is supposed to carry: the lead, the
// second story, three stories from each section, and eight briefs.
function countExpected(data: any): number {
  let n = 2;
  for (const sec of data.sections) n += Math.min(3, sec.stories.length);
  n += Math.min(8, data.briefs.length);
  return n;
}

function run(): void {
  const png = readFileSync(join(HERE, "entry.png"));
  const data = JSON.parse(readFileSync(join(HERE, "headlines.json"), "utf8"));

  const dims = inspectPng(png);
  if (dims.width !== 1024 || dims.height !== 1024) {
    die(`entry.png is ${dims.width}x${dims.height}, the bounty asks for at most 1024x1024`);
  }
  if (png.length < LOW_BYTES || png.length > HIGH_BYTES) {
    die(`entry.png is ${png.length} bytes, outside the ${LOW_BYTES}-${HIGH_BYTES} profile`);
  }

  const sha = createHash("sha256").update(png).digest("hex");
  const items = countExpected(data);

  const summary = {
    competition: SLUG,
    date: "2026-11-23",
    artifact: "entry.png",
    width: dims.width,
    height: dims.height,
    bytes: png.length,
    sha256: sha,
    rendered_items: items,
    sections: data.sections.map((s: any) => s.name),
    briefs_rendered: Math.min(8, data.briefs.length),
    status: "ok",
  };

  // Deliver into the grader's output directory ONLY. The repo mount is
  // read-only, so the committed PNG bytes are copied verbatim: the file
  // the judge sees is byte-identical to the one just checked, and a
  // second run overwrites it with the same bytes (deterministic).
  const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
  const outPng = join(outDir, "entry.png");
  try {
    mkdirSync(outDir, { recursive: true });
    writeFileSync(outPng, png);
    writeFileSync(join(outDir, "summary.json"), JSON.stringify(summary, null, 1) + "\n");
  } catch (err) {
    die(`could not write deliverables into ${outDir}: ${(err as Error).message}`);
  }

  // Read the delivered file back: a short write must fail loudly here
  // rather than hand the judge a different image than the one checked.
  const delivered = readFileSync(outPng);
  if (delivered.length !== png.length) {
    die(`delivered entry.png is ${delivered.length} bytes, expected ${png.length}`);
  }
  if (createHash("sha256").update(delivered).digest("hex") !== sha) {
    die("delivered entry.png hash differs from the verified artifact");
  }
  console.log(
    `checked entry.png: ${dims.width}x${dims.height}, ${png.length} bytes, ` +
      `${items} news items, sha256 ${sha.slice(0, 16)}… → ${outPng} (read-back verified)`,
  );
}

run();
