import { NextResponse } from "next/server";
import { z } from "zod";
import { ContentError } from "@/lib/content/loader";
import { ExerciseNotFound } from "@/lib/exercises";
import { MonsterError } from "@/lib/monsters";

/** Wraps a JSON route: validates the body, maps known errors to status codes. */
export function jsonRoute<T extends z.ZodType>(schema: T, fn: (body: z.infer<T>) => Promise<unknown> | unknown) {
  return async (req: Request) => {
    let body: unknown;
    try {
      body = await req.json();
    } catch {
      return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
    }
    const parsed = schema.safeParse(body);
    if (!parsed.success) return NextResponse.json({ error: parsed.error.issues }, { status: 400 });
    try {
      return NextResponse.json(await fn(parsed.data));
    } catch (e) {
      if (e instanceof ExerciseNotFound) return NextResponse.json({ error: `exercise not found: ${e.message}` }, { status: 404 });
      if (e instanceof MonsterError) return NextResponse.json({ error: e.message }, { status: 400 });
      if (e instanceof ContentError) return NextResponse.json({ error: e.message }, { status: 500 });
      console.error(e);
      return NextResponse.json({ error: (e as Error).message }, { status: 500 });
    }
  };
}

export const keySchema = z.string().regex(/^[a-z0-9-]+\/[a-z0-9-]+\/[a-z0-9-]+\/[a-z0-9-]+$/);
export const stepSchema = z.number().int().min(0).max(10).optional();
