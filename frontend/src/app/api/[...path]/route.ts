// Backend-for-frontend proxy: the browser only ever calls same-origin /api/*,
// and this handler forwards the request to the Express API.
// Why: no CORS, and API_URL is read at *runtime*, so the same Docker image works
// in docker-compose (http://api:4000) and Kubernetes (http://api.mockai.svc:4000).

const API_URL = () => process.env.API_URL ?? "http://localhost:4000";

async function proxy(request: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const incoming = new URL(request.url);
  const target = `${API_URL()}/${path.join("/")}${incoming.search}`;

  const headers = new Headers();
  for (const name of ["authorization", "content-type", "accept"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const hasBody = !["GET", "HEAD"].includes(request.method);
  const res = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    // Required by Node's fetch when streaming a request body (e.g. audio uploads).
    // @ts-expect-error - `duplex` is not in the DOM RequestInit type yet
    duplex: hasBody ? "half" : undefined,
    cache: "no-store",
  });

  return new Response(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
