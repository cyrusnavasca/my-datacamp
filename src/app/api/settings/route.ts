import { z } from "zod";
import { jsonRoute } from "@/lib/api/handler";
import { resetProgress, setSetting } from "@/lib/progress";

export const POST = jsonRoute(
  z.object({
    dailyGoal: z.number().int().min(50).max(5000).optional(),
    theme: z.enum(["system", "light", "dark"]).optional(),
    reset: z.union([z.literal("all"), z.string().regex(/^[a-z0-9-]+$/)]).optional(),
  }),
  ({ dailyGoal, theme, reset }) => {
    if (dailyGoal) setSetting("daily_goal", String(dailyGoal));
    if (theme) setSetting("theme", theme);
    if (reset) resetProgress(reset === "all" ? undefined : reset);
    return { ok: true };
  },
);
