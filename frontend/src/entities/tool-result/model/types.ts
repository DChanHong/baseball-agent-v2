import { z } from "zod";

export const toolResultKindSchema = z.enum([
  "find_kbo_game",
  "get_stadium_info",
  "get_weather_context",
  "search_baseball_knowledge",
  "score_seat_candidates",
  "get_ticketing_guide",
  "get_logistics_guide",
]);

export const toolResultStatusSchema = z.enum(["idle", "running", "success", "error"]);

export const toolResultSchema = z.object({
  id: z.string().min(1),
  kind: toolResultKindSchema,
  title: z.string().min(1),
  status: toolResultStatusSchema,
  summary: z.string().min(1),
  asOf: z.string().optional(),
});

export type ToolResultKind = z.infer<typeof toolResultKindSchema>;
export type ToolResultStatus = z.infer<typeof toolResultStatusSchema>;
export type ToolResult = z.infer<typeof toolResultSchema>;
