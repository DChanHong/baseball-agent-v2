import type { z } from "zod";

export function parseWithSchema<TSchema extends z.ZodType>(
  schema: TSchema,
  data: unknown,
): z.infer<TSchema> {
  return schema.parse(data);
}

export function safeParseWithSchema<TSchema extends z.ZodType>(schema: TSchema, data: unknown) {
  return schema.safeParse(data);
}
