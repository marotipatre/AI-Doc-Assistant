import { test, expect } from "@playwright/test";
import { demoOverview } from "../lib/demo-data";
import { readinessPack } from "../lib/readiness-pack";

test("documentation links appear in the editor and exported Markdown", async ({
  page,
}) => {
  await page.goto("/workspace?demo=1");
  await expect(
    page.getByRole("heading", { name: "Documentation for this repository" }),
  ).toBeVisible();
  const links = page.locator(".technology-grid a");
  expect(await links.count()).toBeGreaterThan(0);
  expect(readinessPack(demoOverview).markdown).toContain(
    "## Developer documentation",
  );
  await expect(page.getByLabel("SKILL.md document")).toHaveValue(
    /## Developer documentation/,
  );
  await page.getByLabel("Find a technology").fill("unmatched-technology");
  await expect(page.locator(".technology-grid article")).toHaveCount(0);
});

test("repository questions retrieve example references and can be added to the document", async ({
  page,
}) => {
  await page.goto("/workspace?demo=1");
  await expect(
    page.getByRole("heading", { name: "Create and edit SKILL.md" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Ask repository" }).click();
  await page.getByLabel("Your question").fill("How do I run the tests?");
  await page.getByRole("button", { name: "Ask question", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Add answer to SKILL.md" }),
  ).toBeVisible();
  await page.getByText(/Referenced files \(/).click();
  await expect(page.locator(".answer-reference").first()).toBeVisible();
  await page.getByRole("button", { name: "Add answer to SKILL.md" }).click();
  await page.getByRole("link", { name: /SKILL.md editor/ }).click();
  await expect(page.getByLabel("SKILL.md document")).toHaveValue(
    /## Repository question/,
  );
});
