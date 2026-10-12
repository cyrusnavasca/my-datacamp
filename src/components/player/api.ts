import type { Answer, Reveal, SubmitResult } from "@/lib/exercises";
import type { RunResult } from "@/lib/runner";

async function post<T>(url: string, body: object): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(typeof data.error === "string" ? data.error : JSON.stringify(data.error));
  return data as T;
}

export const api = {
  run: (key: string, code: string, step?: number) => post<RunResult>("/api/run", { key, code, step }),
  submit: (key: string, input: { code?: string; answer?: Answer; step?: number }) => post<SubmitResult>("/api/submit", { key, ...input }),
  hint: (key: string, step?: number) => post<{ hint: string }>("/api/hint", { key, step }),
  solution: (key: string, step?: number) => post<Reveal>("/api/solution", { key, step }),
};

export type { Answer, Reveal, RunResult, SubmitResult };
