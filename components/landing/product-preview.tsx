"use client";
import { useState } from "react";
import {
  ArrowUpRight,
  Check,
  FileCode2,
  FolderGit2,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
const scenes = [
  {
    title: "Review the project’s setup files.",
    label: "Review files",
    file: "README.md",
    text: "Setup instructions",
    status: "View source",
    lines: [
      "# Local development",
      "1. Read the setup documentation",
      "2. Confirm runtime and services",
      "3. Verify the documented checks",
    ],
  },
  {
    title: "Describe what you want to change.",
    label: "Edit instructions",
    file: "TASK BRIEF",
    text: "Add authentication tests",
    status: "References selected",
    lines: [
      "Task: add authentication tests",
      "→ Inspect candidate auth sources",
      "→ Review existing test patterns",
      "→ Confirm behavior and affected callers",
    ],
  },
  {
    title: "Review and download SKILL.md.",
    label: "Download file",
    file: "SKILL.md",
    text: "Repository instructions",
    status: "Ready to review",
    lines: [
      "name: repo-your-project",
      "## Setup instructions",
      "## Task-specific references",
      "## Verification checklist",
    ],
  },
];
export function ProductPreview() {
  const [active, setActive] = useState(0);
  const scene = scenes[active];
  return (
    <div className="product-stage">
      <div className="floating-note note-top">
        <ShieldCheck size={17} />
        <span>Review source files</span>
        <Check size={14} />
      </div>
      <div className="product-window">
        <div className="product-window-bar">
          <span className="window-controls">
            <i />
            <i />
            <i />
          </span>
          <span>repolens / SKILL.md editor</span>
          <span className="preview-badge">ILLUSTRATIVE</span>
        </div>
        <div className="product-window-body">
          <div className="preview-repository">
            <FolderGit2 size={19} />
            <span>your-team / your-project</span>
            <span>main</span>
          </div>
          <h2 key={active}>{scene.title}</h2>
          <div className="preview-evidence">
            <div>
              <FileCode2 size={20} />
              <strong>{scene.text}</strong>
            </div>
            <span>
              <Check size={13} />
              {scene.status}
            </span>
          </div>
          <div className="preview-editor">
            <div>
              <span>{scene.file}</span>
              <span>MARKDOWN</span>
            </div>
            <pre key={scene.file}>
              {scene.lines.map((line, i) => (
                <span key={line}>
                  <i>{i + 1}</i>
                  {line}
                  {"\n"}
                </span>
              ))}
            </pre>
          </div>
          <Link href="/workspace?demo=1">
            Open this example <ArrowUpRight size={15} />
          </Link>
        </div>
      </div>
      <div className="preview-scene-tabs" aria-label="Product preview steps">
        {scenes.map((item, i) => (
          <button
            key={item.label}
            aria-pressed={active === i}
            onClick={() => setActive(i)}
          >
            <span>0{i + 1}</span>
            {item.label}
          </button>
        ))}
      </div>
      <div className="floating-note note-bottom">
        <span className="status-dot" /> Edit the file before downloading.
      </div>
    </div>
  );
}
