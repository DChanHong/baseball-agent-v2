import { z } from "zod";

export const toolEnvelopeMetaSchema = z.object({
  source: z.string().optional(),
  asOf: z.string().optional(),
  limitations: z.array(z.string()).default([]),
});

export const toolEnvelopeErrorSchema = z.object({
  code: z.string().min(1),
  message: z.string().min(1),
});

export function createToolEnvelopeSchema<TDataSchema extends z.ZodType>(dataSchema: TDataSchema) {
  return z.object({
    ok: z.boolean(),
    status: z.string().min(1),
    data: dataSchema.nullable(),
    error: toolEnvelopeErrorSchema.nullable(),
    meta: toolEnvelopeMetaSchema,
  });
}

export type ToolEnvelope<TData> = {
  ok: boolean;
  status: string;
  data: TData | null;
  error: z.infer<typeof toolEnvelopeErrorSchema> | null;
  meta: z.infer<typeof toolEnvelopeMetaSchema>;
};
