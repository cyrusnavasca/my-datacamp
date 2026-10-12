import { z } from "zod";
import { jsonRoute, keySchema, stepSchema } from "@/lib/api/handler";
import { submit } from "@/lib/exercises";

export const POST = jsonRoute(
  z.object({
    key: keySchema,
    code: z.string().max(100_000).optional(),
    answer: z.union([z.number().int(), z.array(z.string()), z.record(z.string(), z.string())]).optional(),
    step: stepSchema,
  }),
  ({ key, ...input }) => submit(key, input),
);
