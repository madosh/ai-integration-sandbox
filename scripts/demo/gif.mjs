// Convert the recorded webm (from record.mjs) into an optimized GIF for the README.
//
//   npm run gif                     # uses ffmpeg on PATH, or $FFMPEG_PATH,
//                                   # or the ffmpeg Playwright already downloaded.
//
// Two-pass palette (palettegen + paletteuse) keeps the GIF small and crisp.

import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir, tmpdir } from "node:os";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, "out");
const GIF = resolve(HERE, "../../docs/demo.gif");
const FPS = 12;
const WIDTH = 900;

function findWebm() {
  const files = readdirSync(OUT)
    .filter((f) => f.endsWith(".webm"))
    .map((f) => join(OUT, f))
    .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
  if (!files.length) throw new Error(`no .webm found in ${OUT} — run 'npm run record' first`);
  return files[0];
}

// Recursively look for a Playwright-bundled ffmpeg under a root (best-effort).
function searchPlaywright(root) {
  if (!root || !existsSync(root)) return null;
  const stack = [root];
  const exe = process.platform === "win32" ? "ffmpeg-win64.exe" : "ffmpeg-linux";
  while (stack.length) {
    const dir = stack.pop();
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const e of entries) {
      const p = join(dir, e.name);
      if (e.isFile() && e.name.startsWith("ffmpeg")) return p;
      if (e.isDirectory() && (e.name.includes("ffmpeg") || e.name.includes("playwright") || dir === root))
        stack.push(p);
    }
  }
  return null;
}

function resolveFfmpeg() {
  if (process.env.FFMPEG_PATH && existsSync(process.env.FFMPEG_PATH)) return process.env.FFMPEG_PATH;
  try {
    execFileSync("ffmpeg", ["-version"], { stdio: "ignore" });
    return "ffmpeg";
  } catch {
    /* not on PATH */
  }
  for (const root of [join(tmpdir(), "cursor-sandbox-cache"), join(homedir(), "AppData/Local/ms-playwright")]) {
    const found = searchPlaywright(root);
    if (found) return found;
  }
  throw new Error("ffmpeg not found. Install it or set FFMPEG_PATH.");
}

const webm = findWebm();
const ffmpeg = resolveFfmpeg();
const vf =
  `fps=${FPS},scale=${WIDTH}:-1:flags=lanczos,` +
  `split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3`;

console.log(`ffmpeg: ${ffmpeg}`);
console.log(`in:     ${webm}`);
execFileSync(ffmpeg, ["-y", "-i", webm, "-vf", vf, "-loop", "0", GIF], { stdio: "inherit" });
console.log(`out:    ${GIF} (${(statSync(GIF).size / 1024).toFixed(0)} KB)`);
