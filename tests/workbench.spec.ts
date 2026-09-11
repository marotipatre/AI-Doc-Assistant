import { expect, test } from "@playwright/test";
import { demoOverview } from "../lib/demo-data";

test("workspace has one handoff flow without chat or technology dashboards", async ({
  page,
}) => {
  await page.goto("/workspace?demo=1");
  await expect(
    page.getByRole("heading", {
      name: "Create and edit SKILL.md",
    }),
  ).toBeVisible();
  await expect(page.getByRole("tab")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Export context", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: /Repository files/ }).click();
  await page.getByLabel("Search files").fill("no-such-file-xyz");
  await expect(page.getByText("No files match your search.")).toBeVisible();
});

test("empty live workspace is reachable with one demo toggle and indexes a repository", async ({
  page,
}) => {
  const repo = { ...demoOverview.repository, id: "live-test", is_demo: false };
  let indexed = false;
  await page.route("**/api/backend/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown;
    if (path.endsWith("/auth/session"))
      body = { authenticated: false, user: null, github_configured: false };
    else if (
      path.endsWith("/repositories") &&
      route.request().method() === "GET"
    )
      body = indexed ? [repo] : [];
    else if (
      path.endsWith("/repositories") &&
      route.request().method() === "POST"
    )
      body = repo;
    else if (path.endsWith("/index")) {
      indexed = true;
      body = {
        id: "job",
        repository_id: repo.id,
        stage: "ready",
        status: "ready",
        progress: 100,
        warnings: [],
      };
    } else if (path.endsWith("/overview"))
      body = { ...demoOverview, repository: repo };
    else
      return route.fulfill({
        status: 404,
        json: { detail: `Unexpected request ${path}` },
      });
    await route.fulfill({ json: body });
  });
  await page.goto("/workspace?demo=1");
  await page.getByRole("switch", { name: "Demo mode" }).click();
  await expect(
    page.getByRole("switch", { name: "Demo mode" }),
  ).not.toBeChecked();
  await page
    .getByLabel("GitHub repository URL")
    .fill("https://github.com/acme/repo");
  await page
    .getByRole("button", { name: "Read repository", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Download SKILL.md" }),
  ).toBeEnabled();
  await page.getByRole("switch", { name: "Demo mode" }).click();
  await expect(page.getByRole("switch", { name: "Demo mode" })).toBeChecked();
  await page.getByRole("switch", { name: "Demo mode" }).click();
  await expect(
    page.getByRole("button", { name: "Sync repository" }),
  ).toBeVisible();
});
