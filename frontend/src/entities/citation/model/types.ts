import { z } from "zod";

export const citationSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  url: z.url().optional(),
  asOf: z.string().optional(),
  limitation: z.string().optional(),
});

export type Citation = z.infer<typeof citationSchema>;
