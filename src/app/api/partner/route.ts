import { z } from "zod";
import { jsonRoute } from "@/lib/api/handler";
import { choosePartner, view } from "@/lib/monsters";

export const POST = jsonRoute(z.object({ id: z.string().regex(/^[a-z0-9-]+$/) }), ({ id }) => view(choosePartner(id)));
