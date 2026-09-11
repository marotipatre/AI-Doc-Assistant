"use client";
import { useState } from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Copy,
  FileCode2,
  GripVertical,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { TechnologyDocumentation } from "./technology-documentation";
import { SkillEditor } from "./skill-editor";
import type { Overview } from "@/lib/dto";
import { readinessPack } from "@/lib/readiness-pack";

export function ReadinessPack({
  overview,
  task,
  onTaskChange,
  editedDocument,
  onDocumentChange,
}: {
  overview: Overview;
  task: string;
  onTaskChange: (value: string) => void;
  editedDocument: string | null;
  onDocumentChange: (value: string) => void;
}) {
  const [order, setOrder] = useState([0, 1, 2, 3]);
  const [dragged, setDragged] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  function move(from: number, to: number) {
    if (to < 0 || to > 3) return;
    setOrder((current) => {
      const next = [...current];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
    setNotice("Reference card moved.");
  }
  const [notice, setNotice] = useState("");
  const pack = readinessPack(overview, task);
  const documentContent = editedDocument ?? pack.markdown;
  const ready =
    overview.repository.status === "ready" && overview.sources.length > 0;
  const key = `repolens:pack:${overview.repository.id}`;
  function download() {
    const url = URL.createObjectURL(
      new Blob([documentContent], { type: "text/markdown" }),
    );
    const a = window.document.createElement("a");
    a.href = url;
    a.download = "SKILL.md";
    a.click();
    URL.revokeObjectURL(url);
    try {
      localStorage.setItem(key, overview.repository.commit_sha);
    } catch {}
    setNotice(
      "SKILL.md downloaded. Review it, then save it in your coding tool’s skill directory.",
    );
  }
  function checkFreshness() {
    try {
      const previous = localStorage.getItem(key);
      setNotice(
        !previous
          ? "You have not downloaded this repository’s SKILL.md in this browser."
          : previous === overview.repository.commit_sha
            ? "Your last download used this repository version. Sync repository to check for newer changes on GitHub."
            : "The repository version has changed since your last download. Review the document and download it again.",
      );
    } catch {
      setNotice(
        "Browser storage is unavailable. Compare the commit in your downloaded pack manually.",
      );
    }
  }
  return (
    <section className="readiness-pack studio-pack">
      <div className="studio-page-heading">
        <span className="mini-label">
          <ShieldCheck size={16} /> REPOSITORY INSTRUCTIONS
        </span>
        <h1>Create and edit SKILL.md</h1>
        <p>
          Review the project instructions below. Edit the document directly or
          ask the writing assistant to suggest a change.{" "}
          {overview.repository.is_demo &&
            "You are viewing an example, not one of your repositories."}
        </p>
      </div>
      <ol className="pack-steps">
        <li>Choose a repository</li>
        <li>Review repository files</li>
        <li>Edit and download SKILL.md</li>
      </ol>
      <div className="studio-compose-grid">
        <div className="studio-task-panel">
          <span className="mini-label">OPTIONAL: DESCRIBE YOUR TASK</span>
          <h2>What will you work on?</h2>
          <label htmlFor="handoff-task">Describe your task</label>
          <textarea
            id="handoff-task"
            value={task}
            onChange={(e) => onTaskChange(e.target.value)}
            maxLength={3000}
            disabled={editedDocument !== null}
            placeholder="For example: add password reset to authentication"
          />
          <p>
            {pack.relevant.length} matching file references will be included.
          </p>
          {editedDocument !== null && (
            <p>
              The document has been edited. Make further changes to its task
              section in the editor below.
            </p>
          )}
          <div className="task-suggestions">
            {[
              "Add authentication tests",
              "Review local setup",
              "Update API validation",
            ].map((value) => (
              <button
                key={value}
                disabled={editedDocument !== null}
                onClick={() => onTaskChange(value)}
              >
                {value}
                <ArrowUpRight size={12} />
              </button>
            ))}
          </div>
        </div>
        <div className="studio-export-panel">
          <span className="mini-label">DOWNLOAD</span>
          <div className="export-file-icon">
            <FileCode2 size={30} />
          </div>
          <h2>SKILL.md</h2>
          <p>
            Download the document shown in the editor below. Your edits are
            included.
          </p>
          {!ready && (
            <p role="alert">
              This snapshot is not ready for export. Finish indexing or sync the
              repository first.
            </p>
          )}
          <div className="pack-actions">
            <button
              className="button primary"
              disabled={!ready}
              onClick={download}
            >
              <ArrowDownToLine size={16} /> Download SKILL.md
            </button>
            <button
              className="button secondary"
              disabled={!ready}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(documentContent);
                  setNotice("Document copied.");
                } catch {
                  setNotice("Copy unavailable. Use Download SKILL.md.");
                }
              }}
            >
              <Copy size={16} /> Copy document
            </button>
            <button className="button secondary" onClick={checkFreshness}>
              Check download version
            </button>
          </div>
        </div>
      </div>
      <p role="status" className="pack-notice">
        {notice}
      </p>
      <SkillEditor
        overview={overview}
        value={documentContent}
        onChange={onDocumentChange}
      />
      <TechnologyDocumentation overview={overview} />
      <details className="reference-files">
        <summary>Reference files used in this document</summary>
        <div className="studio-section-title">
          <div>
            <span className="mini-label">01 / REVIEW</span>
            <h2>Files used to prepare your instructions</h2>
          </div>
          <span>
            <GripVertical size={15} /> Drag cards to arrange
          </span>
        </div>
        <div className="pack-grid studio-evidence-grid">
          {order.map((groupIndex, position) => {
            const group = pack.groups[groupIndex];
            return (
              <article
                key={group.name}
                className={`studio-evidence-card ${dragged === position ? "is-dragging" : ""}`}
                data-card-position={position}
              >
                <div className="evidence-card-top">
                  <span className="evidence-icon">
                    <FileCode2 size={20} />
                  </span>
                  <span
                    className={`evidence-status ${group.evidence.length ? "found" : ""}`}
                  >
                    {group.evidence.length
                      ? "Files available"
                      : "Check repository"}
                  </span>
                  <button
                    className="card-drag-handle"
                    aria-label={`Drag ${group.name}`}
                    onPointerDown={(event) => {
                      if (event.button !== 0) return;
                      event.currentTarget.setPointerCapture(event.pointerId);
                      setDragged(position);
                    }}
                    onPointerUp={(event) => {
                      const destination = document
                        .elementFromPoint(event.clientX, event.clientY)
                        ?.closest<HTMLElement>("[data-card-position]");
                      const target = Number(destination?.dataset.cardPosition);
                      if (
                        destination &&
                        Number.isInteger(target) &&
                        target !== position
                      )
                        move(position, target);
                      setDragged(null);
                      if (
                        event.currentTarget.hasPointerCapture(event.pointerId)
                      )
                        event.currentTarget.releasePointerCapture(
                          event.pointerId,
                        );
                    }}
                    onPointerCancel={() => setDragged(null)}
                  >
                    <GripVertical size={18} />
                  </button>
                </div>
                <h3>{group.name}</h3>
                <p>
                  {group.evidence.length
                    ? `${group.evidence.length} file excerpts available.`
                    : "No matching files were read. Check whether this documentation exists in the repository."}
                </p>
                <div className="evidence-card-bottom">
                  <button
                    className="card-open"
                    aria-expanded={expanded === group.name}
                    onClick={() =>
                      setExpanded(expanded === group.name ? null : group.name)
                    }
                  >
                    {expanded === group.name ? "Close details" : "View files"}
                    <ArrowUpRight size={15} />
                  </button>
                  <div className="card-move">
                    <button
                      disabled={position === 0}
                      aria-label={`Move ${group.name} earlier`}
                      onClick={() => move(position, position - 1)}
                    >
                      <ArrowLeft size={14} />
                    </button>
                    <button
                      disabled={position === 3}
                      aria-label={`Move ${group.name} later`}
                      onClick={() => move(position, position + 1)}
                    >
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
                {expanded === group.name && (
                  <div className="evidence-card-details">
                    {group.evidence.length ? (
                      group.evidence.slice(0, 6).map((source) => (
                        <a
                          key={source.id}
                          href={source.github_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {source.path}:{source.start_line}
                          <ArrowUpRight size={13} />
                        </a>
                      ))
                    ) : (
                      <p>
                        Open the repository to look for documentation outside
                        this snapshot. Do not invent missing commands.
                      </p>
                    )}
                    <Link href="/workspace/evidence">
                      Browse repository files →
                    </Link>
                  </div>
                )}
              </article>
            );
          })}
        </div>
        <p className="pack-limit">
          Only files read by RepoLens are listed. A missing reference does not
          mean the file is absent from GitHub.
        </p>
      </details>
      <details>
        <summary>Preview download</summary>
        <pre>{documentContent}</pre>
      </details>
      <p>
        For tools supporting skills, save the reviewed file under{" "}
        <code>.agents/skills/{pack.name}/SKILL.md</code>. Other tools can use it
        as attached context. Repository instructions remain authoritative.
      </p>
    </section>
  );
}
