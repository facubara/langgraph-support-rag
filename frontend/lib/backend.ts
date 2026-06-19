import { auth } from "@/auth";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export class UnauthorizedError extends Error {}

/**
 * Authenticated server-to-server fetch to the FastAPI backend (the BFF boundary).
 * The browser never calls FastAPI directly — it calls our route handlers, which read
 * the Auth.js session and forward the request with a shared secret + identity headers.
 */
export async function backendFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const session = await auth();
  if (!session?.user) throw new UnauthorizedError("not signed in");

  const headers = new Headers(init.headers);
  headers.set("x-internal-secret", process.env.SERVICE_SHARED_SECRET ?? "");
  headers.set("x-user-id", session.user.id ?? session.user.email ?? "anonymous");
  headers.set("x-user-email", session.user.email ?? "");

  return fetch(`${BACKEND_URL}${path}`, { ...init, headers, cache: "no-store" });
}

/** Proxy a JSON request to the backend and relay its status + body verbatim. */
export async function proxyJson(path: string, init: RequestInit = {}): Promise<Response> {
  try {
    const res = await backendFetch(path, init);
    const body = await res.text();
    const headers = new Headers();
    headers.set("content-type", res.headers.get("content-type") ?? "application/json");
    for (const h of ["retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"]) {
      const v = res.headers.get(h);
      if (v) headers.set(h, v);
    }
    return new Response(body, { status: res.status, headers });
  } catch (err) {
    if (err instanceof UnauthorizedError) return Response.json({ detail: "unauthorized" }, { status: 401 });
    return Response.json({ detail: "backend unreachable" }, { status: 502 });
  }
}

/** Forward the incoming request body as a JSON POST to the backend. */
export async function forwardPost(request: Request, path: string): Promise<Response> {
  const body = await request.text();
  return proxyJson(path, { method: "POST", body, headers: { "content-type": "application/json" } });
}
