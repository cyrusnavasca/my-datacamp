import { describe, expect, it } from "vitest";
import { apiBlockReason } from "@/proxy";

const req = (headers: Record<string, string>, method = "POST") => ({ method, headers: new Headers(headers) });
const json = { "content-type": "application/json" };

describe("api guard", () => {
  it("allows same-origin JSON from loopback", () => {
    expect(apiBlockReason(req({ host: "127.0.0.1:3000", origin: "http://127.0.0.1:3000", ...json }))).toBeNull();
    expect(apiBlockReason(req({ host: "localhost:3000", ...json }))).toBeNull();
  });
  it("blocks other sites, rebinding hosts and non-JSON posts", () => {
    expect(apiBlockReason(req({ host: "127.0.0.1:3000", origin: "https://evil.example", ...json }))).toBe("cross-origin request");
    expect(apiBlockReason(req({ host: "evil.example:3000", ...json }))).toBe("bad host");
    expect(apiBlockReason(req({ host: "127.0.0.1:3000", "content-type": "text/plain" }))).toBe("JSON only");
    expect(apiBlockReason(req({ host: "127.0.0.1:3000", origin: "null", ...json }))).toBe("bad origin");
  });
});
