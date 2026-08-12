import { z } from "zod";
import { API_BASE_URL, fetchWithAuthRefresh } from "@/features/auth/api/auth-api";

export type ConversationSummary = {
  id: string;
  title: string | null;
  status: string;
  lastMessageAt: string | null;
  createdAt: string;
  updatedAt: string;
};

const conversationSummarySchema = z
  .object({
    id: z.string().min(1),
    title: z.string().nullable(),
    status: z.string().min(1),
    last_message_at: z.string().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
  })
  .transform(
    (conversation): ConversationSummary => ({
      id: conversation.id,
      title: conversation.title,
      status: conversation.status,
      lastMessageAt: conversation.last_message_at,
      createdAt: conversation.created_at,
      updatedAt: conversation.updated_at,
    }),
  );

const conversationListSchema = z
  .object({
    conversations: z.array(conversationSummarySchema),
    limit: z.number(),
    offset: z.number(),
  })
  .transform((payload) => payload.conversations);

export async function listConversations(): Promise<ConversationSummary[]> {
  const response = await fetchWithAuthRefresh(`${API_BASE_URL}/api/v1/conversations?limit=50`, {
    credentials: "include",
  });

  if (response.status === 401) {
    return [];
  }

  if (!response.ok) {
    throw new Error(`대화 목록을 불러오지 못했습니다. (${response.status})`);
  }

  const payload = (await response.json()) as unknown;
  return conversationListSchema.parse(payload);
}
