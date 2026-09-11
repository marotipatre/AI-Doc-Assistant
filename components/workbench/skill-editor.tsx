"use client";
import { useRef, useState } from "react";
import { Check, MessageSquare, Send, Undo2, X } from "lucide-react";
import type { Overview } from "@/lib/dto";

type Proposal = { base: string; start: number; end: number; content: string };
export function SkillEditor({
  overview,
  value,
  onChange,
}: {
  overview: Overview;
  value: string;
  onChange: (value: string) => void;
}) {
  const editor = useRef<HTMLTextAreaElement>(null);
  const [instruction, setInstruction] = useState("");
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [history, setHistory] = useState<{ role: string; text: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [undo, setUndo] = useState<{ before: string; after: string } | null>(
    null,
  );
  async function suggest() {
    if (!instruction.trim() || busy) return;
    const base = value,
      start = selection.start,
      end = selection.end;
    const selected = base.slice(start, end);
    if (selected.length > 6000) {
      setError("Select a shorter passage (up to 6,000 characters).");
      return;
    }
    setBusy(true);
    setError("");
    setProposal(null);
    const request = instruction.trim();
    setHistory((items) => [...items.slice(-7), { role: "You", text: request }]);
    try {
      let content: string;
      if (overview.repository.is_demo) {
        content = `### Review checklist\n\n- Confirm the setup steps against README.md.\n- Run the checks documented in the repository.\n- Record any missing instructions before making changes.`;
        setHistory((items) => [
          ...items,
          {
            role: "Assistant",
            text: "This example adds a review checklist. Connect a repository to request changes tailored to your document.",
          },
        ]);
      } else {
        const response = await fetch(
          `/api/backend/v1/repositories/${encodeURIComponent(overview.repository.id)}/skill-edits`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              instruction: request,
              selection: selected,
              context: base.slice(0, 4000),
            }),
          },
        );
        const result = await response.json();
        if (!response.ok)
          throw new Error(
            typeof result.detail === "string"
              ? result.detail
              : "The suggestion could not be completed. Try again.",
          );
        if (typeof result.content !== "string" || !result.content.trim())
          throw new Error("No suggestion was returned.");
        content = result.content;
        setHistory((items) => [
          ...items,
          {
            role: "Assistant",
            text: selected
              ? "Review the replacement below, then apply it to the selected passage."
              : "Review the new section below, then add it to the end of your document.",
          },
        ]);
      }
      setProposal({
        base,
        start: selected ? start : base.length,
        end: selected ? end : base.length,
        content,
      });
      setInstruction("");
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "The suggestion could not be completed.",
      );
    } finally {
      setBusy(false);
    }
  }
  function apply() {
    if (!proposal) return;
    if (value !== proposal.base) {
      setError(
        "The document changed after this suggestion was requested. Request a new suggestion to avoid overwriting your edits.",
      );
      return;
    }
    const insertion =
      proposal.start === proposal.end
        ? `\n\n${proposal.content}`
        : proposal.content;
    const next =
      value.slice(0, proposal.start) + insertion + value.slice(proposal.end);
    setUndo({ before: value, after: next });
    onChange(next);
    setProposal(null);
    setSelection({ start: 0, end: 0 });
    setHistory((items) => [
      ...items,
      {
        role: "Assistant",
        text: "Change applied to the document. Download SKILL.md when you finish reviewing.",
      },
    ]);
  }
  return (
    <section
      className="document-workspace"
      aria-label="Document editor and writing assistant"
    >
      <div className="document-editor">
        <div className="document-heading">
          <div>
            <h2>Edit SKILL.md</h2>
            <p>Edit directly, or select a passage and request a change.</p>
          </div>
          <button
            className="button secondary"
            disabled={!undo || value !== undo.after}
            onClick={() => {
              if (undo) onChange(undo.before);
              setUndo(null);
            }}
          >
            <Undo2 size={15} />
            Undo suggestion
          </button>
        </div>
        <label className="sr-only" htmlFor="skill-document">
          SKILL.md document
        </label>
        <textarea
          id="skill-document"
          ref={editor}
          value={value}
          spellCheck={false}
          onChange={(e) => {
            onChange(e.target.value);
            setSelection({
              start: e.target.selectionStart,
              end: e.target.selectionEnd,
            });
          }}
          onSelect={(e) =>
            setSelection({
              start: e.currentTarget.selectionStart,
              end: e.currentTarget.selectionEnd,
            })
          }
        />
      </div>
      <aside className="document-chat" id="writing-assistant">
        <h2>
          <MessageSquare size={18} />
          Writing assistant
        </h2>
        <p>
          {selection.end > selection.start
            ? `${selection.end - selection.start} characters selected. The suggestion will replace this passage.`
            : "Ask to add a section, or select text in the editor to rewrite it."}
        </p>
        <div className="document-chat-history" aria-live="polite">
          {history.map((item, i) => (
            <div key={i} className={item.role === "You" ? "user" : ""}>
              <strong>{item.role}</strong>
              <p>{item.text}</p>
            </div>
          ))}
        </div>
        {error && <p role="alert">{error}</p>}
        {proposal && (
          <div className="document-proposal">
            <label htmlFor="suggested-edit">
              Suggested text — review before applying
            </label>
            <textarea
              id="suggested-edit"
              value={proposal.content}
              onChange={(e) =>
                setProposal({ ...proposal, content: e.target.value })
              }
            />
            <div className="pack-actions">
              <button className="button primary" onClick={apply}>
                <Check size={14} />
                Apply change
              </button>
              <button
                className="button secondary"
                onClick={() => setProposal(null)}
              >
                <X size={14} />
                Discard
              </button>
            </div>
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void suggest();
          }}
        >
          <label htmlFor="edit-request">What should change?</label>
          <textarea
            id="edit-request"
            value={instruction}
            maxLength={2000}
            disabled={busy}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="For example: add a checklist for reviewing a pull request"
          />
          <button
            className="button primary"
            disabled={busy || !instruction.trim()}
          >
            <Send size={14} />
            {busy ? "Preparing suggestion…" : "Suggest edit"}
          </button>
        </form>
      </aside>
    </section>
  );
}
