import { z } from "zod";
import type { ToolResult } from "@/entities/tool-result/model/types";
import { toolResultSchema } from "@/entities/tool-result/model/types";

export const chatMessageRoleSchema = z.enum(["user", "assistant", "system"]);

export const chatMessageSchema = z.object({
  id: z.string().min(1),
  role: chatMessageRoleSchema,
  content: z.string(),
  createdAt: z.string(),
  toolResults: z.array(toolResultSchema).optional(),
});

export type ChatMessageRole = z.infer<typeof chatMessageRoleSchema>;
export type ChatMessage = Omit<z.infer<typeof chatMessageSchema>, "toolResults"> & {
  toolResults?: ToolResult[];
};
