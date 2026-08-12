import { useQuery } from "@tanstack/react-query";
import { listConversations } from "@/features/conversation-list/api/list-conversations";

export const conversationListQueryKey = ["conversations", "list"] as const;

export function useConversationList(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: conversationListQueryKey,
    queryFn: listConversations,
    enabled: options.enabled ?? true,
  });
}
