/** Record the illustrative local workflow without accessing provider credentials. */
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
await mkdir("artifacts", { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1020 },
  recordVideo: { dir: "artifacts", size: { width: 1440, height: 1020 } },
  reducedMotion: "reduce",
});
const page = await context.newPage();
const video = page.video();
await page.goto("http://127.0.0.1:3000/workspace?demo=1");
await page.getByRole("heading", { name: "The big picture._" }).waitFor();
await page.screenshot({ path: "artifacts/repolens-overview.png" });
await page.waitForTimeout(1200);
await page
  .getByRole("textbox", { name: "Ask a question about this repository" })
  .fill("Where is authentication handled?");
await page.getByRole("button", { name: "Send question", exact: true }).click();
await page.locator(".message-citations button").first().waitFor();
await page.waitForTimeout(1200);
await page.locator(".message-citations button").first().click();
await page.waitForTimeout(1500);
await page.screenshot({ path: "artifacts/repolens-evidence.png" });
await page
  .getByRole("button", { name: "Close inspector panel", exact: true })
  .click();
await page.getByRole("tab", { name: /^Skills/ }).click();
await page.waitForTimeout(1500);
await page.screenshot({ path: "artifacts/repolens-skills.png" });
const download = page.waitForEvent("download");
await page
  .getByRole("button", { name: "Export context", exact: true })
  .first()
  .click();
await (await download).saveAs("artifacts/repolens-context.md");
await page.waitForTimeout(800);
await context.close();
if (video) await video.saveAs("artifacts/repolens-demo.webm");
await browser.close();
console.log(
  "Saved illustrative demo recording, screenshots, and context export in artifacts/.",
);
