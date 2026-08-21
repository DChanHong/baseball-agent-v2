import { z } from "zod";
import { toolResultSchema } from "@/entities/tool-result/model/types";
import type { ToolResult } from "@/entities/tool-result/model/types";
import { API_BASE_URL, fetchWithAuthRefresh } from "@/features/auth/api/auth-api";
import type { ChatMessage } from "@/entities/message/model/types";

const toolPayloadSchema = z
  .object({
    tool_call_id: z.string(),
    name: toolResultSchema.shape.name,
    status: z.enum(["completed", "failed"]),
    input: z.record(z.string(), z.unknown()).default({}),
    result: z.record(z.string(), z.unknown()).nullable(),
    error: z
      .object({ code: z.string(), message: z.string() })
      .nullable(),
  })
  .transform(
    (p): ToolResult => ({
      id: p.tool_call_id,
      name: p.name,
      status: p.status,
      input: p.input,
      result: p.result,
      error: p.error,
    }),
  );

const messageMetadataSchema = z.object({
  tool_results: z.array(toolPayloadSchema).optional().default([]),
});

const messageSchema = z
  .object({
    id: z.string().min(1),
    role: z.enum(["user", "assistant"]),
    content: z.string(),
    sequence_no: z.number(),
    metadata: z.record(z.string(), z.unknown()).default({}),
    created_at: z.string(),
  })
  .transform((msg): ChatMessage => {
    const parsedMeta = messageMetadataSchema.safeParse(msg.metadata);
    const toolResults =
      msg.role === "assistant" && parsedMeta.success && parsedMeta.data.tool_results.length > 0
        ? parsedMeta.data.tool_results
        : undefined;

    return {
      id: msg.id,
      role: msg.role,
      content: msg.content,
      createdAt: msg.created_at,
      toolResults,
    };
  });

const messageListSchema = z
  .object({
    messages: z.array(messageSchema),
    limit: z.number(),
    offset: z.number(),
  })
  .transform((payload) => payload.messages);

export async function getConversationMessages(conversationId: string): Promise<ChatMessage[]> {
  const response = await fetchWithAuthRefresh(
    `${API_BASE_URL}/api/v1/conversations/${conversationId}/messages?limit=100`,
    { credentials: "include" },
  );

  if (response.status === 401 || response.status === 403 || response.status === 404) {
    return [];
  }

  if (!response.ok) {
    throw new Error(`메시지를 불러오지 못했습니다. (${response.status})`);
  }

  const payload = (await response.json()) as unknown;
  return messageListSchema.parse(payload);
}
