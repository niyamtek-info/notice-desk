import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");

  if (!url) {
    return NextResponse.json({ error: "Missing url parameter" }, { status: 400 });
  }

  // Strip trailing /api/v1 if present — NEXT_PUBLIC_API_URL may include it for
  // direct API calls (e.g. ${NEXT_PUBLIC_API_URL}/extract/process) but the proxy
  // needs the bare origin so it can append /api/v1/files/serve itself.
  const backendBase = (process.env.NEXT_PUBLIC_API_URL ?? "")
    .replace(/\/$/, "")
    .replace(/\/api\/v1$/, "");

  // gs:// URI — V4 signing failed on the backend; route through /api/v1/files/serve.
  // This is a server-side fetch so localhost resolves correctly on the VM.
  if (url.startsWith("gs://")) {
    const key = url.replace(/^gs:\/\/[^/]+\//, "");
    if (!backendBase) {
      return NextResponse.json({ error: "Backend URL not configured" }, { status: 500 });
    }
    const serveUrl = `${backendBase}/api/v1/files/serve?key=${encodeURIComponent(key)}`;
    const upstream = await fetch(serveUrl);
    const contentType = upstream.headers.get("content-type") ?? "application/octet-stream";
    const body = await upstream.arrayBuffer();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { "content-type": contentType },
    });
  }

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return NextResponse.json({ error: "Invalid url" }, { status: 400 });
  }

  // Backend file-serve URL — always rewrite to NEXT_PUBLIC_API_URL so that
  // BACKEND_BASE_URL (the VM's external IP set in the Python .env) never leaks
  // into a host-mismatch rejection.  This is a server-side fetch, so localhost
  // resolves correctly on the VM regardless of what IP was stored.
  if (parsed.pathname.startsWith("/api/v1/files/serve")) {
    const key = parsed.searchParams.get("key");
    if (key && backendBase) {
      const serveUrl = `${backendBase}/api/v1/files/serve?key=${encodeURIComponent(key)}`;
      const upstream = await fetch(serveUrl);
      const contentType = upstream.headers.get("content-type") ?? "application/octet-stream";
      const body = await upstream.arrayBuffer();
      return new NextResponse(body, {
        status: upstream.status,
        headers: { "content-type": contentType },
      });
    }
  }

  let backendHost = "";
  try {
    backendHost = new URL(backendBase).hostname;
  } catch {}

  const isGCS = parsed.hostname.endsWith("googleapis.com");
  const isBackend = backendHost !== "" && parsed.hostname === backendHost;

  if (!isGCS && !isBackend) {
    return NextResponse.json({ error: "URL not allowed" }, { status: 403 });
  }

  const upstream = await fetch(url);

  const contentType = upstream.headers.get("content-type") ?? "application/octet-stream";
  const body = await upstream.arrayBuffer();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "content-type": contentType,
    },
  });
}
