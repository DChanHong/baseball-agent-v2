import { z } from "zod";

export const gameSummarySchema = z.object({
  id: z.string().min(1),
  date: z.string().min(1),
  homeTeam: z.string().min(1),
  awayTeam: z.string().min(1),
  stadiumName: z.string().min(1),
});

export type GameSummary = z.infer<typeof gameSummarySchema>;
