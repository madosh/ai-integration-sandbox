// Convert Mermaid -> authentic hand-drawn Excalidraw SVG.
//
// Uses the official Excalidraw libraries (@excalidraw/mermaid-to-excalidraw +
// @excalidraw/excalidraw exportToSvg) inside a real headless Chromium (via
// Playwright), so the output is identical to what excalidraw.com produces:
// rough.js sketchy strokes + the Excalifont hand-drawn font, embedded in the
// SVG so the file is fully self-contained (offline, Medium-ready).
//
// Run:  npm install  &&  npm run gen

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { diagrams } from "./diagrams.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = resolve(HERE, "../../docs/diagrams");

const EXC = "0.17.6";
const M2E = "1.1.2";
const ASSET_PATH = `https://cdn.jsdelivr.net/npm/@excalidraw/excalidraw@${EXC}/dist/`;
const FONT_URL = `https://cdn.jsdelivr.net/npm/@excalidraw/excalidraw@${EXC}/dist/excalidraw-assets/Virgil.woff2`;

// Excalidraw 0.17 emits an @font-face whose src is an (often broken) external
// URL. Fetch the hand-drawn font once and inline it as base64 so each SVG is
// fully self-contained: renders identically offline and when pasted elsewhere.
async function inlineFont(svg, dataUri) {
  return svg.replace(
    /src:\s*url\("[^"]*Virgil\.woff2"\)/g,
    `src: url("${dataUri}") format("woff2")`,
  );
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });

  process.stdout.write("Fetching hand-drawn font ... ");
  const fontRes = await fetch(FONT_URL);
  if (!fontRes.ok) throw new Error(`font fetch failed: ${fontRes.status}`);
  const fontB64 = Buffer.from(await fontRes.arrayBuffer()).toString("base64");
  const fontDataUri = `data:font/woff2;base64,${fontB64}`;
  console.log(`ok (${(fontB64.length / 1024).toFixed(1)} KB base64)`);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on("console", (m) => console.log(`  [page:${m.type()}] ${m.text()}`));
  page.on("pageerror", (e) => console.log(`  [pageerror] ${e.message}`));

  // A real secure origin avoids opaque-origin module-import quirks.
  await page.goto("https://example.com", { waitUntil: "domcontentloaded" });

  for (const [name, definition] of Object.entries(diagrams)) {
    process.stdout.write(`Converting ${name} ... `);
    const svg = await page.evaluate(
      async ({ definition, assetPath, excVersion, m2eVersion }) => {
        globalThis.EXCALIDRAW_ASSET_PATH = assetPath;
        const [{ parseMermaidToExcalidraw }, exc] = await Promise.all([
          import(`https://esm.sh/@excalidraw/mermaid-to-excalidraw@${m2eVersion}`),
          import(`https://esm.sh/@excalidraw/excalidraw@${excVersion}`),
        ]);
        // esm.sh nests the CJS-built package under `default`.
        const api = typeof exc.convertToExcalidrawElements === "function" ? exc : exc.default;
        const { convertToExcalidrawElements, exportToSvg } = api;
        const { elements, files } = await parseMermaidToExcalidraw(definition, {
          themeVariables: { fontSize: "16px" },
        });
        const els = convertToExcalidrawElements(elements);

        // ── Recolor for a dark background ──────────────────────────────
        // We export WITHOUT dark-mode (no invert filter) and instead set
        // explicit colors, so nodes are vibrant and text/arrows stay legible.
        const palette = [
          { s: "#4dabf7", f: "#12283f" }, // blue
          { s: "#69db7c", f: "#123020" }, // green
          { s: "#ffd43b", f: "#302a12" }, // amber
          { s: "#ff8787", f: "#301a1a" }, // red
          { s: "#b197fc", f: "#241f3d" }, // violet
          { s: "#ffa94d", f: "#302113" }, // orange
          { s: "#66d9e8", f: "#123033" }, // cyan
        ];
        const NODE = new Set(["rectangle", "ellipse", "diamond"]);
        const CONTAINER_STROKE = "#8aa0c2";
        const ARROW = "#94a3b8";
        const LEAF_TEXT = "#f8fafc";
        const EDGE_TEXT = "#cbd5e1";

        const byId = new Map(els.map((e) => [e.id, e]));
        const shapes = els.filter((e) => NODE.has(e.type));
        const containsOther = (a) =>
          shapes.some(
            (b) =>
              b !== a &&
              b.x >= a.x - 1 &&
              b.y >= a.y - 1 &&
              b.x + b.width <= a.x + a.width + 1 &&
              b.y + b.height <= a.y + a.height + 1,
          );

        const colorOf = new Map();
        let leaf = 0;
        for (const el of shapes) {
          if (containsOther(el)) {
            el.strokeColor = CONTAINER_STROKE;
            el.backgroundColor = "transparent";
            el.strokeWidth = 2;
            colorOf.set(el.id, CONTAINER_STROKE);
          } else {
            const c = palette[leaf++ % palette.length];
            el.strokeColor = c.s;
            el.backgroundColor = c.f;
            el.fillStyle = "solid";
            el.strokeWidth = 2;
            colorOf.set(el.id, c.s);
          }
        }
        for (const el of els) {
          if (el.type === "arrow" || el.type === "line") {
            el.strokeColor = ARROW;
          } else if (el.type === "text") {
            const parent = el.containerId ? colorOf.get(el.containerId) : null;
            el.strokeColor = parent
              ? parent === CONTAINER_STROKE
                ? CONTAINER_STROKE
                : LEAF_TEXT
              : EDGE_TEXT;
          }
        }

        const svgEl = await exportToSvg({
          elements: els,
          files: files ?? null,
          exportPadding: 18,
          appState: {
            exportBackground: false,
            exportWithDarkMode: false,
            viewBackgroundColor: "transparent",
          },
        });
        return svgEl.outerHTML;
      },
      { definition, assetPath: ASSET_PATH, excVersion: EXC, m2eVersion: M2E },
    );

    const withFont = await inlineFont(svg, fontDataUri);
    const file = resolve(OUT_DIR, `${name}.svg`);
    writeFileSync(file, withFont, "utf8");
    console.log(`ok (${(withFont.length / 1024).toFixed(1)} KB) -> ${file}`);
  }

  await browser.close();
  console.log("\nDone.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
