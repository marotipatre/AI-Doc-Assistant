import { expect, test } from "@playwright/test";

test("theme choice persists across the public pages and workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: /theme/i }).first().click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.goto("/guide");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.goto("/workspace?demo=1");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: /theme/i }).first().click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("small screens keep page content inside the viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  for (const path of [
    "/",
    "/guide",
    "/workspace?demo=1",
    "/workspace?demo=1&view=sources",
  ]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    const size = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(size.document, path).toBeLessThanOrEqual(size.viewport + 1);
  }
});

test("unknown pages provide a working way back", async ({ page }) => {
  await page.goto("/this-page-does-not-exist");
  await expect(
    page.getByRole("heading", { name: /This path leads/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open workspace" }).click();
  await expect(page).toHaveURL(/\/workspace/);
  await expect(
    page.getByRole("heading", {
      name: "Create instructions for your repository.",
    }),
  ).toBeVisible();
});
