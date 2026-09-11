import { test, expect } from "@playwright/test";

test("landing preview responds to clicks and links into real workspace pages", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Edit instructions/ }).click();
  await expect(page.locator(".preview-editor")).toContainText(
    "Task: add authentication tests",
  );
  await page.getByRole("button", { name: /Download file/ }).click();
  await expect(page.locator(".preview-editor")).toContainText("SKILL.md");
  await page.getByRole("link", { name: "Open this example" }).click();
  await expect(
    page.getByRole("heading", { name: "Create and edit SKILL.md" }),
  ).toBeVisible();
});

test("cards can be moved and reviewed; route navigation preserves the task draft", async ({
  page,
}) => {
  await page.goto("/workspace?demo=1");
  await page
    .getByText("Reference files used in this document", { exact: true })
    .click();
  const cards = page.locator(".studio-evidence-card");
  await expect(cards.first()).toContainText("Agent instructions");
  await page
    .getByRole("button", { name: "Move Agent instructions later" })
    .click();
  await expect(cards.first()).toContainText("Setup documentation");
  await cards.first().getByRole("button", { name: "View files" }).click();
  await expect(
    cards
      .first()
      .getByRole("link", { name: /README/ })
      .first(),
  ).toBeVisible();
  await page.getByLabel("Describe your task").fill("Preserve this draft");
  await page.getByRole("link", { name: /Repository files/ }).click();
  await expect(page).toHaveURL(/\/workspace\/evidence/);
  await expect(page.getByLabel("Search files")).toBeVisible();
  await page.getByRole("link", { name: /SKILL.md editor/ }).click();
  await expect(page.getByLabel("Describe your task")).toHaveValue(
    "Preserve this draft",
  );
  await page
    .locator(
      'nav[aria-label="Workspace pages"] a[href="/workspace/repository"]',
    )
    .click();
  await expect(page).toHaveURL(/\/workspace\/repository/);
  await expect(page.getByLabel("GitHub repository URL")).toBeVisible();
});

test("all product pages fit a narrow viewport and respect reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const path of [
    "/",
    "/guide",
    "/workspace?demo=1",
    "/workspace/evidence?demo=1",
    "/workspace/repository?demo=1",
  ]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
      path,
    ).toBe(true);
  }
});

test("desktop drag handles reorder evidence cards", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop-chromium",
    "Touch users have explicit move buttons.",
  );
  await page.goto("/workspace?demo=1");
  await page
    .getByText("Reference files used in this document", { exact: true })
    .click();
  await page
    .getByRole("button", { name: "Drag Agent instructions", exact: true })
    .dragTo(page.locator(".studio-evidence-card").nth(1));
  await expect(page.locator(".studio-evidence-card").first()).toContainText(
    "Setup documentation",
  );
});
