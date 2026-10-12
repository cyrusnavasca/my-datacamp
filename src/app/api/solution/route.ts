import { z } from "zod";
import { jsonRoute, keySchema, stepSchema } from "@/lib/api/handler";
import { solution } from "@/lib/exercises";

export const POST = jsonRoute(z.object({ key: keySchema, step: stepSchema }), ({ key, step }) => solution(key, step));
