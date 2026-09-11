import { test, expect } from "@playwright/test";

test("readiness handoff exports evidence without model requests", async ({
  page,
}) => {
  let messages = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().includes("/messages"))
      messages++;
  });
  await page.goto("/workspace?demo=1&view=pack");
  await expect(
    page.getByRole("heading", {
      name: "Create and edit SKILL.md",
    }),
  ).toBeVisible();
  await page.getByLabel("Describe your task").fill("Add authentication tests");
  await page.getByText("Preview download").click();
  await expect(page.locator(".readiness-pack pre")).toContainText(
    "Add authentication tests",
  );
  await expect(page.locator(".readiness-pack pre")).toContainText(
    "SAMPLE DATA",
  );
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download SKILL.md" }).click();
  expect((await download).suggestedFilename()).toBe("SKILL.md");
  await page.getByRole("button", { name: "Check download version" }).click();
  await expect(page.locator(".readiness-pack [role=status]")).toContainText(
    "used this repository version",
  );
  expect(messages).toBe(0);
  await expect(page.getByRole("switch", { name: "Demo mode" })).toBeChecked();
  await page.setViewportSize({ width: 360, height: 800 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("pack preserves evidence, marks gaps, and ignores filler-only task text", async () => {
  const { readinessPack } = await import("../lib/readiness-pack");
  const { demoOverview } = await import("../lib/demo-data");
  const pack = readinessPack(demoOverview, "please add this and that");
  expect(pack.relevant).toHaveLength(0);
  expect(pack.markdown).toContain("Setup and instruction excerpts");
  expect(pack.markdown).toContain(demoOverview.repository.commit_sha);
  const empty = readinessPack({ ...demoOverview, sources: [], skills: [] });
  expect(empty.groups.every((group) => group.evidence.length === 0)).toBe(true);
  expect(empty.markdown).toContain("No setup excerpts available");
  expect(empty.markdown).not.toContain("npm install");
});
