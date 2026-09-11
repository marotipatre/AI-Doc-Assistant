/** Local visual review only: no chat submissions or model requests. */
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

await mkdir("artifacts/ui-review", { recursive: true });
const browser = await chromium.launch();
const errors: string[] = [];
for (const theme of ["dark", "light"]) {
  for (const device of ["desktop", "mobile"]) {
    const context = await browser.newContext({
      viewport:
        device === "desktop"
          ? { width: 1440, height: 1050 }
          : { width: 390, height: 844 },
      reducedMotion: "reduce",
    });
    await context.addInitScript((value) => {
      localStorage.setItem("repolens:theme", value);
    }, theme);
    const page = await context.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    for (const [name, route] of [
      ["home", "/"],
      ["guide", "/guide"],
      ["workspace", "/workspace?demo=1"],
      ["connect", "/workspace?connect=1"],
    ]) {
      if (
        process.argv.includes("--workspace-only") &&
        !["workspace", "connect"].includes(name)
      )
        continue;
      await page.goto("http://127.0.0.1:3000" + route);
      await page.locator("main").waitFor();
      if (name === "connect") await page.getByRole("dialog").waitFor();
      await page.screenshot({
        path: `artifacts/ui-review/${name}-${device}-${theme}.png`,
        fullPage: true,
      });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth + 1,
      );
      if (overflow)
        errors.push(`Horizontal overflow: ${name} ${device} ${theme}`);
    }
    await context.close();
  }
}
await browser.close();
console.log(
  JSON.stringify({ screenshots: "artifacts/ui-review", errors }, null, 2),
);
if (errors.length) process.exitCode = 1;
