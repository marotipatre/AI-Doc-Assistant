import { expect, test } from "@playwright/test";
import { demoOverview } from "../lib/demo-data";

test("returning sessions require selection and disconnect clears the workspace", async ({
  page,
}) => {
  const repo = {
    ...demoOverview.repository,
    id: "private-project",
    is_demo: false,
    private: true,
  };
  let connected = true;
  const imported: string[] = [];
  await page.addInitScript(() =>
    localStorage.setItem(
      "repolens:workspace",
      JSON.stringify({ mode: "live", id: "private-project" }),
    ),
  );
  await page.route("**/api/backend/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown;
    if (path.endsWith("/auth/session"))
      body = {
        authenticated: connected,
        user: connected ? { login: "alex", id: "1" } : null,
        github_configured: true,
      };
    else if (path.endsWith("/auth/repositories"))
      body = [
        {
          full_name: "alex/first",
          html_url: "https://github.com/alex/first",
          default_branch: "main",
          private: false,
        },
        {
          full_name: "alex/second",
          html_url: "https://github.com/alex/second",
          default_branch: "develop",
          private: true,
        },
      ];
    else if (path.endsWith("/auth/logout")) {
      connected = false;
      return route.fulfill({ status: 204 });
    } else if (
      path.endsWith("/repositories") &&
      route.request().method() === "GET"
    )
      body = connected ? [repo] : [];
    else if (path.endsWith("/repositories")) {
      imported.push(route.request().postDataJSON().url);
      body = repo;
    } else if (path.endsWith("/index"))
      body = {
        id: "job",
        stage: "ready",
        status: "ready",
        progress: 100,
        warnings: [],
      };
    else if (path.endsWith("/skill-edits"))
      body = {
        content: "## Project checks\n\nReview the documented tests.",
        sources: [],
      };
    else if (path.endsWith("/overview"))
      body = { ...demoOverview, repository: repo };
    else
      return route.fulfill({
        status: 404,
        json: { detail: "Unexpected route" },
      });
    await route.fulfill({ json: body });
  });
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", {
      name: "Create instructions for your repository.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "GitHub: alex" }),
  ).toBeVisible();
  expect(imported).toHaveLength(0);
  await page
    .locator(
      'nav[aria-label="Workspace pages"] a[href="/workspace/repository"]',
    )
    .click();
  await page
    .getByLabel("Select GitHub repository")
    .selectOption("https://github.com/alex/second");
  await expect(page.getByLabel("GitHub repository URL")).toHaveValue(
    "https://github.com/alex/second",
  );
  await expect(page.getByLabel("Branch or ref (optional)")).toHaveValue(
    "develop",
  );
  await page
    .getByRole("button", { name: "Read repository", exact: true })
    .click();
  await expect(page.getByLabel("SKILL.md document")).toBeVisible();
  expect(imported).toEqual(["https://github.com/alex/second"]);
  await page.getByLabel("What should change?").fill("Add project checks");
  await page.getByRole("button", { name: "Suggest edit", exact: true }).click();
  await expect(
    page.getByLabel("Suggested text — review before applying"),
  ).toHaveValue(/Project checks/);
  await page.getByRole("button", { name: "Apply change", exact: true }).click();
  await page.getByText("Preview download", { exact: true }).click();
  await expect(page.locator(".readiness-pack > details pre")).toContainText(
    "## Project checks",
  );
  await page.getByRole("button", { name: "GitHub: alex" }).click();
  await page
    .getByRole("button", { name: "Disconnect GitHub", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Connect GitHub", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("GitHub repository URL")).toHaveValue("");
  await expect(page.getByLabel("SKILL.md document")).toHaveCount(0);
  await page.reload();
  await expect(page.getByLabel("GitHub repository URL")).toHaveValue("");
  await expect(page.getByLabel("Select GitHub repository")).toHaveCount(0);
});

test("suggestions require apply, support undo, and preserve manual changes", async ({
  page,
}) => {
  await page.goto("/workspace?demo=1");
  const document = page.getByLabel("SKILL.md document");
  await document.fill("# Project\n\nKeep this instruction.");
  await page.getByLabel("What should change?").fill("Add a review checklist");
  await page.getByRole("button", { name: "Suggest edit", exact: true }).click();
  await expect(
    page.getByLabel("Suggested text — review before applying"),
  ).toBeVisible();
  await expect(document).toHaveValue("# Project\n\nKeep this instruction.");
  await page.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(document).toHaveValue(
    /Keep this instruction\.[\s\S]*Review checklist/,
  );
  await page.getByRole("button", { name: "Undo suggestion" }).click();
  await expect(document).toHaveValue("# Project\n\nKeep this instruction.");
  await page.getByLabel("What should change?").fill("Add checks");
  await page.getByRole("button", { name: "Suggest edit", exact: true }).click();
  await expect(
    page.getByLabel("Suggested text — review before applying"),
  ).toBeVisible();
  await document.fill("# My manual revision");
  await page.getByRole("button", { name: "Apply change", exact: true }).click();
  await expect(page.locator(".document-chat [role=alert]")).toContainText(
    "document changed",
  );
  await expect(document).toHaveValue("# My manual revision");
});
