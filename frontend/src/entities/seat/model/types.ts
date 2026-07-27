import { z } from "zod";

export const seatScoreSummarySchema = z.object({
  id: z.string().min(1),
  sectionName: z.string().min(1),
  totalScore: z.number(),
  priceScore: z.number(),
  viewScore: z.number(),
  cheeringScore: z.number(),
  weatherScore: z.number(),
});

export type SeatScoreSummary = z.infer<typeof seatScoreSummarySchema>;
