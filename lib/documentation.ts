import catalog from "@/api/app/documentation_catalog.json";
import type { DocumentationReference, Overview } from "./dto";
export function repositoryDocumentation(
  overview: Overview,
): DocumentationReference[] {
  if (overview.documentation) return overview.documentation;
  return overview.skills.flatMap((skill) => {
    const entry = catalog.find((item) => item.name === skill.name);
    return entry
      ? [
          {
            name: entry.name,
            category: entry.category,
            kind: "Official documentation",
            url: entry.url,
            evidence: skill.evidence,
          },
        ]
      : [];
  });
}
export function documentationMarkdown(overview: Overview) {
  const links = repositoryDocumentation(overview);
  return `## Developer documentation\n\n${links.length ? links.map((item) => `- [${item.name} — ${item.kind}](${item.url})\n  Repository references: ${item.evidence.map((source) => `${source.path}:${source.start_line}`).join(", ")}`).join("\n") : "No documentation links were mapped from this snapshot."}\n\nLinks use a curated catalog or package registry. Select the documentation version matching the project. A detected reference does not prove the technology is used in production. External documentation pages have not been ingested.\n`;
}
