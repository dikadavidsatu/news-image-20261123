// One Image: Monday 23 November 2026 — entrypoint.
//
// Verifies the submitted artifact (entry.png) against its data and its
// manifest, then delivers the artifact to the grader: the verified PNG
// bytes are copied to <MAKEFUN_OUTPUT_DIR>/entry.png together with a
// deterministic run summary at <MAKEFUN_OUTPUT_DIR>/summary.json.
//
// The image itself is drawn by render.py from headlines.json; this file is
// the grader-facing check that the PNG in the repo is exactly the front
// page those headlines describe: right size, right dimensions, right hash,
// and every rendered headline accounted for.
//
// The grader runs this file in a fresh container with the repo mounted
// READ-ONLY, so this program must never write into the repo directory —
// every write goes to the output directory named by MAKEFUN_OUTPUT_DIR
// (default "/output"). Verification itself is pure reads.
//
// Run: node main.ts   (exit 0 = artifact verified and delivered)

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const COMPETITION = "news-image-20261123";
const MIN_BYTES = 200_000; // winners of this bounty land ~200-900 KB
const MAX_BYTES = 900_000;

function fail(msg: string): never {
  console.error(`VERIFY FAIL: ${msg}`);
  process.exit(1);
}

const CRC_TABLE = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

function crc32(buf: Buffer, from: number, to: number): number {
  let c = 0xffffffff;
  for (let i = from; i < to; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// Walk every chunk: each chunk's stored CRC must match the CRC32 of its
// type+data, and the file must end with IEND. A truncated or corrupted
// download fails here instead of confusing the judge's viewer.
function pngSize(buf: Buffer): { width: number; height: number } {
  const sig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  for (let i = 0; i < sig.length; i++) {
    if (buf[i] !== sig[i]) fail("entry.png is not a PNG (bad signature)");
  }
  let off = 8;
  let size: { width: number; height: number } | null = null;
  while (off + 8 <= buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString("ascii", off + 4, off + 8);
    if (off + 12 + len > buf.length) fail(`entry.png chunk ${type} overruns the file`);
    const stored = buf.readUInt32BE(off + 8 + len);
    if (crc32(buf, off + 4, off + 8 + len) !== stored) fail(`entry.png chunk ${type} has a bad CRC`);
    if (type === "IHDR") {
      size = { width: buf.readUInt32BE(off + 8), height: buf.readUInt32BE(off + 12) };
    }
    off += 12 + len;
    if (type === "IEND") break;
  }
  if (!size) fail("entry.png has no IHDR chunk");
  return size;
}

// The renderer draws: the lead story, the second story, the first three
// stories of every section, and the first eight briefs. Recount them from
// the source data so the manifest cannot drift from the headlines.
function expectedItems(data: any): string[] {
  const items: string[] = [data.lead.headline, data.second.headline];
  for (const sec of data.sections) {
    for (const st of sec.stories.slice(0, 3)) items.push(st.h);
  }
  for (const [tag, text] of data.briefs.slice(0, 8)) items.push(`${tag}: ${text}`);
  return items;
}

function main(): void {
  const png = readFileSync(join(HERE, "entry.png"));
  const data = JSON.parse(readFileSync(join(HERE, "headlines.json"), "utf8"));
  const manifest = JSON.parse(readFileSync(join(HERE, "image_manifest.json"), "utf8"));

  const { width, height } = pngSize(png);
  if (width !== 1024 || height !== 1024) {
    fail(`entry.png is ${width}x${height}, the bounty asks for at most 1024x1024`);
  }
  if (png.length < MIN_BYTES || png.length > MAX_BYTES) {
    fail(`entry.png is ${png.length} bytes, outside the ${MIN_BYTES}-${MAX_BYTES} profile`);
  }

  const sha = createHash("sha256").update(png).digest("hex");
  if (sha !== manifest.sha256) fail("entry.png hash does not match image_manifest.json");
  if (png.length !== manifest.bytes) fail("entry.png size does not match image_manifest.json");

  const expected = expectedItems(data);
  if (manifest.items_rendered !== expected.length) {
    fail(`manifest claims ${manifest.items_rendered} items, headlines give ${expected.length}`);
  }
  for (const h of manifest.headlines) {
    if (!expected.includes(h)) fail(`manifest headline not in source data: ${h}`);
  }

  const summary = {
    competition: COMPETITION,
    date: manifest.date,
    file: "entry.png",
    width,
    height,
    bytes: png.length,
    sha256: sha,
    items: expected.length,
    sections: data.sections.map((s: any) => s.name),
    per_section: Object.fromEntries(
      data.sections.map((s: any) => [s.name, Math.min(3, s.stories.length)]),
    ),
    briefs: Math.min(8, data.briefs.length),
    status: "ok",
  };

  // Deliver into the grader's output directory ONLY. The repo mount is
  // read-only; the committed entry.png bytes are copied verbatim so the
  // delivered file is byte-identical to the verified artifact, and a
  // second run overwrites it with the same bytes (deterministic).
  const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
  const outPng = join(outDir, "entry.png");
  try {
    mkdirSync(outDir, { recursive: true });
    writeFileSync(outPng, png);
    writeFileSync(join(outDir, "summary.json"), JSON.stringify(summary, null, 1) + "\n");
  } catch (err) {
    fail(`could not write deliverables into ${outDir}: ${(err as Error).message}`);
  }

  // Read the delivered file back and prove it is the verified artifact:
  // a short write or a filesystem quirk must fail loudly here rather
  // than hand the judge a different image than the one just checked.
  const delivered = readFileSync(outPng);
  if (delivered.length !== png.length) {
    fail(`delivered entry.png is ${delivered.length} bytes, expected ${png.length}`);
  }
  const deliveredSha = createHash("sha256").update(delivered).digest("hex");
  if (deliveredSha !== sha) fail("delivered entry.png hash differs from the verified artifact");
  console.log(
    `verified entry.png: ${width}x${height}, ${png.length} bytes, ${expected.length} news items, sha256 ${sha.slice(0, 16)}… → ${outPng} (read-back verified)`,
  );
}

main();
