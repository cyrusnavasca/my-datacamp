import { z } from "zod";
import { jsonRoute, keySchema, stepSchema } from "@/lib/api/handler";
import { run } from "@/lib/exercises";

export const POST = jsonRoute(
  z.object({ key: keySchema, code: z.string().max(100_000), step: stepSchema }),
  ({ key, code, step }) => run(key, code, step),
);
