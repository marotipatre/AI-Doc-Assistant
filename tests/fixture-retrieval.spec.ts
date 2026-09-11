import { expect, test } from "@playwright/test";
import { searchDemoSources } from "../lib/api-client";
import golden from "./golden-questions.json";

test("illustrative fixture retrieval matches its golden evidence paths", async ({}, testInfo) => {
  const results = golden.questions.map((item) => {
    const start = performance.now();
    const sources = searchDemoSources(item.question);
    const elapsedMs = performance.now() - start;
    const retrieved = new Set(sources.map((source) => source.path));
    const hits = item.expected_paths.filter((path) =>
      retrieved.has(path),
    ).length;
    if (item.answerable) {
      expect(sources.length, item.question).toBeGreaterThan(0);
      expect(hits, item.question).toBe(item.expected_paths.length);
      for (const source of sources) {
        expect(source.start_line).toBeGreaterThan(0);
        expect(source.end_line).toBeGreaterThanOrEqual(source.start_line);
        expect(source.excerpt).not.toBe("");
        expect(source.commit_sha).toBe("demo-snapshot");
      }
    } else expect(sources, item.question).toHaveLength(0);
    return {
      question: item.question,
      answerable: item.answerable,
      retrieved_paths: [...retrieved],
      expected_path_recall: item.expected_paths.length
        ? hits / item.expected_paths.length
        : null,
      latency_ms: elapsedMs,
    };
  });
  await testInfo.attach("fixture-retrieval-evaluation", {
    body: JSON.stringify(
      {
        mode: "deterministic browser fixture; no model or vector database",
        limitations:
          "Expected-path recall is measured on four authored questions. Citation precision and generated answer groundedness are not evaluated by this test.",
        results,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
});
