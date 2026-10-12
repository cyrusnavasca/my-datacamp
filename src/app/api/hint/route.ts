import { z } from "zod";
import { jsonRoute, keySchema, stepSchema } from "@/lib/api/handler";
import { hint } from "@/lib/exercises";

export const POST = jsonRoute(z.object({ key: keySchema, step: stepSchema }), ({ key, step }) => ({ hint: hint(key, step) }));
