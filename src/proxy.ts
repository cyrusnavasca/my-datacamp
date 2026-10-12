import { NextResponse, type NextRequest } from "next/server";

// /api/run executes Python on this machine. Listening on 127.0.0.1 keeps the
// network out, but not other websites open in the same browser. Block them:
//  - Host must be a loopback name (stops DNS rebinding).
//  - Origin, when sent, must be this app (stops cross-site POSTs).
//  - Content-Type must be application/json (a cross-site JSON POST needs a
//    CORS preflight, which this app never answers).

const LOOPBACK = /^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/;

export function apiBlockReason(req: { method: string; headers: Headers }): string | null {
  const host = req.headers.get("host") ?? "";
  if (!LOOPBACK.test(host)) return "bad host";
  const origin = req.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).host !== host) return "cross-origin request";
    } catch {
      return "bad origin";
    }
  }
  if (req.method !== "GET" && !(req.headers.get("content-type") ?? "").startsWith("application/json")) return "JSON only";
  return null;
}

export function proxy(request: NextRequest) {
  const blocked = apiBlockReason(request);
  if (blocked) return NextResponse.json({ error: `forbidden: ${blocked}` }, { status: 403 });
  return NextResponse.next();
}

export const config = { matcher: "/api/:path*" };
