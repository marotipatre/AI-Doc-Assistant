/** Opt-in real public GitHub ingestion through the Next.js proxy. Embeddings use the configured provider, if enabled. */
const base =
  process.env.REPOLENS_SMOKE_URL || "http://127.0.0.1:3000/api/backend";
let cookie = "";
async function request(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<Response> {
  const response = await fetch(base + path, {
    method,
    signal: AbortSignal.timeout(120_000),
    headers: { "Content-Type": "application/json", Cookie: cookie },
    body: body ? JSON.stringify(body) : undefined,
  });
  const session = response.headers
    .getSetCookie()
    .find((value) => value.startsWith("repolens_session="));
  if (session) cookie = session.split(";")[0];
  if (!response.ok)
    throw new Error(
      `${method} ${path}: ${response.status} ${await response.text()}`,
    );
  return response;
}
const repository = await (
  await request("/v1/repositories", "POST", {
    url: "https://github.com/octocat/Hello-World",
  })
).json();
try {
  const job = await (
    await request(`/v1/repositories/${repository.id}/index`, "POST")
  ).json();
  let status;
  for (let attempt = 0; attempt < 120; attempt++) {
    status = await (await request(`/v1/jobs/${job.id}`)).json();
    if (["completed", "failed", "cancelled"].includes(status.status)) break;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  if (status?.status !== "completed") throw new Error(JSON.stringify(status));
  const overview = await (
    await request(`/v1/repositories/${repository.id}/overview`)
  ).json();
  if (
    !overview.sources.length ||
    !overview.sources.every(
      (source: { github_url: string; commit_sha: string }) =>
        source.github_url.includes(`/blob/${source.commit_sha}/`),
    )
  )
    throw new Error("Missing commit-pinned citations");
  let chatVerified = false;
  if (process.argv.includes("--chat")) {
    for (let i = 0; i < 2; i++) {
      const conversation = await (
        await request(
          `/v1/repositories/${repository.id}/conversations`,
          "POST",
          {},
        )
      ).json();
      const response = await request(
        `/v1/conversations/${conversation.id}/messages`,
        "POST",
        {
          content:
            "What text does the README contain? Answer briefly with a citation.",
        },
      );
      const body = await response.text();
      const done = body
        .split("\n\n")
        .find((block) => block.startsWith("event: done\n"));
      if (!done)
        throw new Error("Chat failed to complete: " + body.slice(-1000));
      const message = JSON.parse(done.split("\ndata: ")[1]).message;
      if (!message.citations.length || !message.content.includes("Hello"))
        throw new Error("Chat did not return the expected README evidence");
      if (i === 1 && !message.cached)
        throw new Error("Repeated question did not reuse answer");
    }
    chatVerified = true;
  }
  console.log(
    JSON.stringify(
      {
        result: "passed",
        repository: repository.full_name,
        files: overview.repository.file_count,
        chunks: overview.repository.chunk_count,
        commit: overview.repository.commit_sha,
        mode: "real GitHub ingestion through Next.js proxy",
        chat_and_cache_verified: chatVerified,
      },
      null,
      2,
    ),
  );
} finally {
  await request(`/v1/repositories/${repository.id}`, "DELETE");
}
export {};
