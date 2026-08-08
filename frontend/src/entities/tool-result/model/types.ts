import { z } from "zod";

const jsonObjectSchema = z.record(z.string(), z.unknown());

export const toolResultNameSchema = z.enum([
  "find_kbo_game",
  "get_stadium_info",
  "get_weather_context",
  "search_stadium_guide",
  "search_ticketing_guide",
  "search_baseball_knowledge",
]);

export const toolResultStatusSchema = z.enum(["running", "completed", "failed"]);

export const toolResultErrorSchema = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
});

export const toolResultSchema = z.object({
  id: z.string().min(1),
  name: toolResultNameSchema,
  status: toolResultStatusSchema,
  input: jsonObjectSchema.default({}),
  result: jsonObjectSchema.nullable(),
  error: toolResultErrorSchema.nullable(),
});

export type ToolResultName = z.infer<typeof toolResultNameSchema>;
export type ToolResultStatus = z.infer<typeof toolResultStatusSchema>;
export type ToolResultError = z.infer<typeof toolResultErrorSchema>;
export type ToolResult = z.infer<typeof toolResultSchema>;
