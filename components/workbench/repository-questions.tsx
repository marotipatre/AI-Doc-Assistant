"use client";
import { useEffect, useRef, useState } from "react";
import { TechnologyDocumentation } from "./technology-documentation";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FilePlus2, Send, Square } from "lucide-react";
import { repositoryDocumentation } from "@/lib/documentation";
import { getApi } from "@/lib/api-client";
import type { Message, Overview } from "@/lib/dto";

export function RepositoryQuestions({
  overview,
  onAddToDocument,
}: {
  overview: Overview;
  onAddToDocument: (text: string) => void;
}) {
  const primaryTechnology = repositoryDocumentation(overview).find(
    (item) => item.kind === "Official documentation",
  )?.name;
  const api = getApi(overview.repository.is_demo ? "demo" : "live");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [completed, setCompleted] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const conversation = useRef<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);
  async function ask() {
    const content = question.trim();
    if (!content || busy) return;
    const controller = new AbortController();
    abort.current = controller;
    const id = crypto.randomUUID();
    setBusy(true);
    setError("");
    setNotice("");
    setQuestion("");
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content,
        citations: [],
        created_at: new Date().toISOString(),
      },
      {
        id,
        role: "assistant",
        content: "",
        citations: [],
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const thread =
        conversation.current ||
        (await api.createConversation(overview.repository.id)).id;
      if (controller.signal.aborted) return;
      conversation.current = thread;
      await api.streamMessage(
        thread,
        content,
        (event) => {
          if (controller.signal.aborted) return;
          if (event.type === "error") {
            setError(event.message);
            return;
          }
          if (event.type === "done")
            setCompleted((current) => [...current, event.message.id]);
          setMessages((current) =>
            current.map((message) =>
              message.id !== id
                ? message
                : event.type === "token"
                  ? { ...message, content: message.content + event.text }
                  : event.type === "citations"
                    ? { ...message, citations: event.sources }
                    : event.type === "done"
                      ? event.message
                      : message,
            ),
          );
        },
        controller.signal,
      );
    } catch (e) {
      if (!controller.signal.aborted)
        setError(
          e instanceof Error
            ? e.message
            : "The answer could not be completed. Please try again.",
        );
    } finally {
      if (abort.current === controller) {
        setBusy(false);
        if (controller.signal.aborted)
          setNotice(
            "Answer stopped. Any text already received may be incomplete.",
          );
      }
    }
  }
  return (
    <section className="repository-questions">
      <div className="studio-page-heading">
        <span className="mini-label">QUESTIONS ABOUT YOUR PROJECT</span>
        <h1>Ask repository</h1>
        <p>
          Ask about setup, project structure, or a specific feature. Answers
          include references to the files used. Name a technology when you want
          an explanation from its official documentation, such as “Explain
          FastAPI dependencies using the docs.” Check the cited version before
          making changes.
        </p>
        {overview.repository.is_demo && (
          <p>You are using example files and example answers.</p>
        )}
      </div>
      <div className="question-examples">
        {[
          "Where are the official documentation links for this project?",
          ...(primaryTechnology
            ? [`Explain ${primaryTechnology} setup using the official docs`]
            : []),
          "How do I run the tests?",
          "Where is authentication implemented?",
          "How is this repository structured?",
        ].map((text) => (
          <button
            className="button secondary"
            disabled={busy}
            key={text}
            onClick={() => setQuestion(text)}
          >
            {text}
          </button>
        ))}
      </div>
      <div
        className="repository-thread"
        aria-live="polite"
        aria-relevant="additions text"
      >
        {messages.length === 0 && (
          <div className="question-empty">
            <h2>What do you need to know?</h2>
            <p>
              Choose a question above or write your own below. Naming a file or
              feature helps find relevant references.
            </p>
          </div>
        )}
        {messages.map((message) => (
          <article
            className={`repository-message ${message.role}`}
            key={message.id}
          >
            <strong>{message.role === "user" ? "You" : "Answer"}</strong>
            <div className="answer-markdown">
              <Markdown remarkPlugins={[remarkGfm]}>
                {message.content ||
                  (busy
                    ? "Searching repository files…"
                    : "No answer was completed.")}
              </Markdown>
            </div>
            {message.citations.length > 0 && (
              <details>
                <summary>Referenced files ({message.citations.length})</summary>
                {message.citations.map((source, i) => (
                  <div className="answer-reference" key={source.id}>
                    <strong>
                      [{i + 1}] {source.path}:{source.start_line}–
                      {source.end_line}
                    </strong>
                    <pre>{source.excerpt}</pre>
                    {source.github_url && (
                      <a
                        href={source.github_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open reference
                      </a>
                    )}
                  </div>
                ))}
              </details>
            )}
            {message.role === "assistant" &&
              message.content &&
              message.citations.length > 0 &&
              completed.includes(message.id) &&
              !busy &&
              !error &&
              !notice.startsWith("Answer stopped") && (
                <button
                  className="button secondary"
                  onClick={() => {
                    onAddToDocument(
                      `\n\n## Repository question\n\n${messages[messages.indexOf(message) - 1]?.content || ""}\n\n${message.content}\n\n### References\n${message.citations.map((source, i) => `- [${i + 1}] ${source.path}:${source.start_line}-${source.end_line}${source.github_url ? ` (${source.github_url})` : ""}`).join("\n")}`,
                    );
                    setNotice(
                      "Answer added to SKILL.md. Open the editor to review it before downloading.",
                    );
                  }}
                >
                  <FilePlus2 size={15} />
                  Add answer to SKILL.md
                </button>
              )}
          </article>
        ))}
      </div>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      <form
        className="repository-question-form"
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <label htmlFor="repository-question">Your question</label>
        <textarea
          id="repository-question"
          value={question}
          maxLength={4000}
          disabled={busy}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="For example: which environment variables are required to run this project?"
        />
        <div className="pack-actions">
          {busy ? (
            <button
              type="button"
              className="button secondary"
              onClick={() => abort.current?.abort()}
            >
              <Square size={14} />
              Stop answer
            </button>
          ) : (
            <button
              className="button primary"
              disabled={
                !question.trim() || overview.repository.status !== "ready"
              }
            >
              <Send size={15} />
              Ask question
            </button>
          )}
          <button
            type="button"
            className="button secondary"
            disabled={busy || !messages.length}
            onClick={() => {
              conversation.current = null;
              setMessages([]);
              setError("");
              setNotice("");
            }}
          >
            New conversation
          </button>
        </div>
      </form>
      <details className="question-docs">
        <summary>Browse developer documentation</summary>
        <TechnologyDocumentation overview={overview} />
      </details>
    </section>
  );
}
