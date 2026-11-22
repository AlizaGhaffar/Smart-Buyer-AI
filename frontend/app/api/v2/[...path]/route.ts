import { NextResponse } from "next/server";

// A free-tier backend can take up to a minute to wake up on the first request.
export const maxDuration = 60;

// Proxy for the FastAPI /api/v2 endpoints. Only known paths are forwarded.
const ALLOWED = [
  /^search$/,
  /^search\/[a-f0-9]{32}$/,
  /^products$/,
  /^snapshots$/,
  /^knowledge\/(raw_sheep_wool|duck_down|cashmere)$/,
];

async function forward(request: Request, segments: string[]) {
  const path = segments.join("/");
  if (!ALLOWED.some((pattern) => pattern.test(path))) {
    return NextResponse.json({ detail: "Not found." }, { status: 404 });
  }
  const backendUrl = (process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  try {
    const response = await fetch(`${backendUrl}/api/v2/${path}`, {
      method: request.method,
      headers: { "Content-Type": "application/json" },
      body: request.method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    console.error("Could not reach the Smart Buyer AI backend.", error);
    return NextResponse.json(
      { detail: "The analysis server is not reachable. If it is hosted on a free plan it may be starting up; please try again in a minute." },
      { status: 502 },
    );
  }
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, context: Context) {
  return forward(request, (await context.params).path);
}

export async function POST(request: Request, context: Context) {
  return forward(request, (await context.params).path);
}
