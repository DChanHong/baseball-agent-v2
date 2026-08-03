const GUEST_ID_STORAGE_KEY = "baseball-agent:guest-id";
const CONVERSATION_ID_STORAGE_KEY = "baseball-agent:current-conversation-id";

export function getOrCreateGuestId() {
  const storedGuestId = window.localStorage.getItem(GUEST_ID_STORAGE_KEY);

  if (storedGuestId) {
    return storedGuestId;
  }

  const guestId = window.crypto.randomUUID();
  window.localStorage.setItem(GUEST_ID_STORAGE_KEY, guestId);

  return guestId;
}

export function getStoredConversationId() {
  return window.localStorage.getItem(CONVERSATION_ID_STORAGE_KEY);
}

export function storeConversationId(conversationId: string) {
  window.localStorage.setItem(CONVERSATION_ID_STORAGE_KEY, conversationId);
}
