import { chromium } from "@playwright/test";
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 1020 },
  deviceScaleFactor: 1,
});
await page.goto("http://127.0.0.1:3000/workspace?demo=1");
await page.getByRole("heading", { name: "The big picture._" }).waitFor();
await page.screenshot({ path: "/tmp/repolens-desktop.png", fullPage: true });
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({ path: "/tmp/repolens-mobile.png", fullPage: true });
await browser.close();
