// Record the dashboard's human-in-the-loop approval flow to a webm video.
//
// Prereqs (all local, offline):
//   .venv python -m uvicorn mock_apis.app:app --port 9000
//   .venv python -m uvicorn aih.service.app:app --port 8000
//   (cd dashboard && npm run dev)          # vite on :5173
//
// Then:  npm install && npm run record
// Output: ./out/*.webm  (convert to GIF with gif.mjs)

import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(HERE, "out");
const URL = process.env.DEMO_URL ?? "http://127.0.0.1:5173";
const size = { width: 1280, height: 820 };

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: size,
    deviceScaleFactor: 2,
    recordVideo: { dir: OUT, size },
  });
  const page = await context.newPage();
  page.on("console", (m) => console.log(`  [page:${m.type()}] ${m.text()}`));
  page.on("pageerror", (e) => console.log(`  [pageerror] ${e.message}`));

  await page.goto(URL, { waitUntil: "domcontentloaded" });
  try {
    await page.getByRole("button", { name: "Start run" }).waitFor({ timeout: 15000 });
  } catch (e) {
    await page.screenshot({ path: resolve(OUT, "debug.png"), fullPage: true });
    console.log("title:", await page.title());
    console.log("bodyText:", (await page.locator("body").innerText()).slice(0, 500));
    throw e;
  }
  await sleep(1200); // let the dashboard settle on screen

  // Kick off a run with a side-effecting goal (pre-filled in the input).
  await page.getByRole("button", { name: "Start run" }).click();

  // The run pauses at the approval gate — this is the moment worth showing.
  const approve = page.getByRole("button", { name: "Approve" });
  await approve.waitFor({ timeout: 20000 });
  await sleep(2600); // dwell on the pending-approval state

  await approve.click();

  // Wait for the run to complete, then dwell so the green status is visible.
  await page.locator(".status.completed").first().waitFor({ timeout: 20000 });
  await sleep(2200);

  await context.close(); // flushes the video to disk
  await browser.close();
  console.log(`Recorded to ${OUT}`);
}

main().catch(async (err) => {
  console.error(err);
  process.exit(1);
});
