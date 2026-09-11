/** Parse SSE incrementally, including UTF-8 and CRLF boundaries between chunks. */
export async function readEventStream(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: { event: string; data: unknown }) => void,
  signal?: AbortSignal,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";
  let data: string[] = [];
  const dispatch = () => {
    if (!data.length) return;
    const raw = data.join("\n");
    if (raw !== "[DONE]") {
      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch {
        throw new Error(
          "The server returned an invalid streaming event. Please retry.",
        );
      }
      onEvent({ event: eventName, data: parsed });
    }
    data = [];
    eventName = "message";
  };
  const line = (value: string) => {
    if (!value) {
      dispatch();
      eventName = "message";
      return;
    }
    if (value.startsWith(":")) return;
    const separator = value.indexOf(":");
    const key = separator < 0 ? value : value.slice(0, separator);
    const content =
      separator < 0 ? "" : value.slice(separator + 1).replace(/^ /, "");
    if (key === "event") eventName = content;
    if (key === "data") data.push(content);
  };
  const cancel = () => {
    void reader.cancel().catch(() => {});
  };
  signal?.addEventListener("abort", cancel, { once: true });
  try {
    while (true) {
      signal?.throwIfAborted();
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value, { stream: !chunk.done });
      // Keep a trailing CR until the next chunk so split CRLF is a single newline.
      let match: RegExpExecArray | null;
      const separator = /\r\n|\n|\r(?!$)/;
      while ((match = separator.exec(buffer))) {
        line(buffer.slice(0, match.index));
        buffer = buffer.slice(match.index + match[0].length);
      }
      if (chunk.done) break;
    }
    signal?.throwIfAborted();
    if (buffer) line(buffer.replace(/\r$/, ""));
    dispatch();
  } finally {
    signal?.removeEventListener("abort", cancel);
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
