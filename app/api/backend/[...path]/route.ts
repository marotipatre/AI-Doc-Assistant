/** A thin transport boundary. Ingestion, authentication and generation live in FastAPI. */
export const runtime = "nodejs";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context): Promise<Response> {
  const { path } = await context.params;
  if (
    path.some(
      (segment) =>
        !segment ||
        segment === "." ||
        segment === ".." ||
        /[\\/]/.test(segment),
    )
  ) {
    return Response.json({ detail: "Invalid API path." }, { status: 400 });
  }
  const incomingUrl = new URL(request.url);
  // This origin is server configuration, never user input.
  const base = process.env.FASTAPI_URL || "http://127.0.0.1:8000";
  const target = new URL(
    `${base.replace(/\/$/, "")}/${path.map(encodeURIComponent).join("/")}`,
  );
  target.search = incomingUrl.search;
  const headers = new Headers();
  for (const name of [
    "accept",
    "content-type",
    "authorization",
    "x-request-id",
  ]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const sessionCookies = request.headers
    .get("cookie")
    ?.split(";")
    .map((cookie) => cookie.trim())
    .filter((cookie) =>
      /^(repolens_session|repolens_oauth_state)=/.test(cookie),
    )
    .join("; ");
  if (sessionCookies) headers.set("cookie", sessionCookies);
  if (!["GET", "HEAD"].includes(request.method)) {
    const origin = request.headers.get("origin");
    if (origin && origin !== incomingUrl.origin) {
      return Response.json(
        { detail: "Cross-origin writes are not allowed." },
        { status: 403 },
      );
    }
  }
  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
      signal: request.signal,
    });
    const outgoingHeaders = new Headers({
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    });
    for (const name of ["content-type", "retry-after", "x-request-id"]) {
      const value = response.headers.get(name);
      if (value) outgoingHeaders.set(name, value);
    }
    for (const cookie of response.headers.getSetCookie())
      outgoingHeaders.append("set-cookie", cookie);
    const location = response.headers.get("location");
    if (location) outgoingHeaders.set("location", location);
    return new Response(response.body, {
      status: response.status,
      headers: outgoingHeaders,
    });
  } catch {
    return Response.json(
      {
        detail:
          "RepoLens API is unavailable. Start the FastAPI service, or switch to the sample workspace.",
      },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const DELETE = proxy;
