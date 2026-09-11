"use client";
import { useState } from "react";
import { ArrowUpRight, BookOpen } from "lucide-react";
import type { Overview } from "@/lib/dto";
import { repositoryDocumentation } from "@/lib/documentation";
export function TechnologyDocumentation({ overview }: { overview: Overview }) {
  const [query, setQuery] = useState("");
  const links = repositoryDocumentation(overview);
  const visible = links.filter((item) =>
    `${item.name} ${item.category}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <section className="technology-docs">
      <div className="studio-section-title">
        <div>
          <span className="mini-label">DEVELOPER REFERENCES</span>
          <h2>Documentation for this repository</h2>
        </div>
        <BookOpen size={22} />
      </div>
      <p>
        Open the documentation for technologies referenced in the project files.
        Check the documentation version against the project’s dependencies.
      </p>
      <label htmlFor="documentation-search">Find a technology</label>
      <input
        id="documentation-search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Python, a framework, a model, or a blockchain tool"
      />
      {!visible.length && (
        <p>
          No matching documentation links. Only recognized references and
          supported dependency manifests are included.
        </p>
      )}
      <div className="technology-grid">
        {visible.map((item) => (
          <article key={`${item.name}:${item.url}`}>
            <span className="mini-label">{item.category}</span>
            <h3>{item.name}</h3>
            <a
              className="button secondary"
              href={item.url}
              target="_blank"
              rel="noreferrer"
            >
              {item.kind === "Package registry"
                ? "Open package page"
                : "Open official documentation"}
              <ArrowUpRight size={14} />
            </a>
            {item.kind === "Package registry" && (
              <p>
                A verified documentation URL is not mapped yet. The package page
                may link to the maintainer’s documentation.
              </p>
            )}
            <details>
              <summary>Why is this listed?</summary>
              {item.evidence.map((source) => (
                <p key={source.id}>
                  {source.path}:{source.start_line}–{source.end_line}
                </p>
              ))}
            </details>
          </article>
        ))}
      </div>
      <p>
        These links do not fetch external documentation or change the
        repository. Package-registry links are labeled separately from official
        documentation.
      </p>
    </section>
  );
}
