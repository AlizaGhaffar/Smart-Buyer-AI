import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const backendUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";

  try {
    const response = await fetch(`${backendUrl.replace(/\/$/, "")}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    console.error("Could not reach the lead search backend.", error);
    return NextResponse.json(
      { detail: "The search service is unavailable. Please try again." },
      { status: 502 },
    );
  }
}
