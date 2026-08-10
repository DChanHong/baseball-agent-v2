"use client";

import { useSetAtom } from "jotai";
import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import styled from "styled-components";
import type { ChatMessage } from "@/entities/message/model/types";
import { MessageBubble } from "@/entities/message/ui/message-bubble";
import type { ToolResult } from "@/entities/tool-result/model/types";
import {
  streamChatMessage,
  type ChatStreamEvent,
  type ChatStreamMessage,
} from "@/features/chat-stream/api/stream-chat-message";
import {
  getOrCreateGuestId,
  getStoredConversationId,
  storeConversationId,
} from "@/features/chat-stream/model/guest-session";
import { ChatComposer } from "@/features/send-message/ui/chat-composer";
import { Button } from "@/shared/ui/button";
import { isSourceDrawerOpenAtom } from "@/widgets/source-drawer/model/source-drawer.atom";

export function ChatPanel() {
  const openSourceDrawer = useSetAtom(isSourceDrawerOpenAtom);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : getStoredConversationId(),
  );
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const guestIdRef = useRef<string | null>(null);
  const pendingUserMessageIdRef = useRef<string | null>(null);
  const activeAssistantMessageIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    guestIdRef.current = getOrCreateGuestId();

    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSendMessage = (message: string) => {
    if (isStreaming) {
      return;
    }

    const guestId = guestIdRef.current ?? getOrCreateGuestId();
    guestIdRef.current = guestId;

    const pendingUserMessageId = `local_user_${window.crypto.randomUUID()}`;
    pendingUserMessageIdRef.current = pendingUserMessageId;
    activeAssistantMessageIdRef.current = null;
    setErrorMessage(null);
    setIsStreaming(true);
    setMessages((prev) => [
      ...prev,
      {
        id: pendingUserMessageId,
        role: "user",
        content: message,
        createdAt: new Date().toISOString(),
      },
    ]);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    void consumeChatStream({
      guestId,
      conversationId,
      message,
      signal: abortController.signal,
    });
  };

  const consumeChatStream = async ({
    guestId,
    conversationId,
    message,
    signal,
  }: {
    guestId: string;
    conversationId: string | null;
    message: string;
    signal: AbortSignal;
  }) => {
    try {
      for await (const event of streamChatMessage({ guestId, conversationId, message }, signal)) {
        applyStreamEvent(event);
      }
    } catch (error) {
      if (signal.aborted) {
        return;
      }

      const message = error instanceof Error ? error.message : "채팅 응답을 불러오지 못했습니다.";
      setErrorMessage(message);
      ensureAssistantMessage("응답을 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
      pendingUserMessageIdRef.current = null;
    }
  };

  const applyStreamEvent = (event: ChatStreamEvent) => {
    switch (event.type) {
      case "conversation.created":
        setConversationId(event.conversationId);
        storeConversationId(event.conversationId);
        return;
      case "message.created":
        applyMessageCreated(event.message);
        return;
      case "tool.started":
        upsertToolResult({
          id: event.toolCallId,
          name: event.name,
          status: "running",
          input: event.input,
          result: null,
          error: null,
        });
        return;
      case "tool.completed":
        upsertToolResult({
          id: event.toolCallId,
          name: event.name,
          status: "completed",
          input: event.input,
          result: event.result,
          error: null,
        });
        return;
      case "tool.failed":
        upsertToolResult({
          id: event.toolCallId,
          name: event.name,
          status: "failed",
          input: event.input,
          result: null,
          error: event.error,
        });
        return;
      case "assistant.delta":
        activeAssistantMessageIdRef.current = event.messageId;
        appendAssistantDelta(event.messageId, event.delta);
        return;
      case "assistant.completed":
        activeAssistantMessageIdRef.current = event.messageId;
        setMessages((prev) =>
          prev.map((item) =>
            item.id === event.messageId ? { ...item, content: event.content } : item,
          ),
        );
        return;
      case "stream.failed":
        setErrorMessage(event.error.message);
        return;
      case "conversation.updated":
      case "done":
        return;
      default:
        return;
    }
  };

  const applyMessageCreated = (message: ChatStreamMessage) => {
    const chatMessage: ChatMessage = {
      id: message.id,
      role: message.role,
      content: message.content,
      createdAt: message.createdAt,
    };

    if (message.role === "assistant") {
      activeAssistantMessageIdRef.current = message.id;
    }

    setMessages((prev) => {
      if (prev.some((item) => item.id === message.id)) {
        return prev;
      }

      if (message.role === "user" && pendingUserMessageIdRef.current) {
        return prev.map((item) =>
          item.id === pendingUserMessageIdRef.current ? chatMessage : item,
        );
      }

      return [...prev, chatMessage];
    });
  };

  const ensureAssistantMessage = (fallbackContent = "") => {
    const messageId =
      activeAssistantMessageIdRef.current ?? `local_assistant_${window.crypto.randomUUID()}`;
    activeAssistantMessageIdRef.current = messageId;

    setMessages((prev) => {
      if (prev.some((item) => item.id === messageId)) {
        return prev;
      }

      return [
        ...prev,
        {
          id: messageId,
          role: "assistant",
          content: fallbackContent,
          createdAt: new Date().toISOString(),
          toolResults: [],
        },
      ];
    });

    return messageId;
  };

  const appendAssistantDelta = (messageId: string, delta: string) => {
    setMessages((prev) => {
      if (!prev.some((item) => item.id === messageId)) {
        return [
          ...prev,
          {
            id: messageId,
            role: "assistant",
            content: delta,
            createdAt: new Date().toISOString(),
            toolResults: [],
          },
        ];
      }

      return prev.map((item) =>
        item.id === messageId ? { ...item, content: `${item.content}${delta}` } : item,
      );
    });
  };

  const upsertToolResult = (toolResult: ToolResult) => {
    const assistantMessageId = ensureAssistantMessage();

    setMessages((prev) =>
      prev.map((message) => {
        if (message.id !== assistantMessageId) {
          return message;
        }

        const toolResults = message.toolResults ?? [];
        const existingIndex = toolResults.findIndex((item) => item.id === toolResult.id);

        if (existingIndex === -1) {
          return {
            ...message,
            toolResults: [...toolResults, toolResult],
          };
        }

        return {
          ...message,
          toolResults: toolResults.map((item, index) =>
            index === existingIndex ? toolResult : item,
          ),
        };
      }),
    );
  };

  const hasMessages = messages.length > 0;

  return (
    <Panel $hasMessages={hasMessages}>
      {hasMessages ? (
        <ChatWorkspace>
          <MessageList aria-live="polite">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {errorMessage ? <ErrorText>{errorMessage}</ErrorText> : null}
          </MessageList>
          <Dock>
            <ChatComposer disabled={isStreaming} onSendMessage={handleSendMessage} />
            <FooterActions>
              <Button type="button" variant="ghost" onClick={() => openSourceDrawer(true)}>
                출처 패널 열기
              </Button>
            </FooterActions>
          </Dock>
        </ChatWorkspace>
      ) : (
        <Hero>
          <LogoWrap aria-hidden="true">
            <LogoRing />
            <LogoCore>B</LogoCore>
          </LogoWrap>
          <Copy>
            <Eyebrow>
              <Sparkles size={15} />
              KBO Agent
            </Eyebrow>
            <Heading>오늘의 직관 판단을 한 번에 끝내세요</Heading>
            <Description>
              경기 일정, 구장 정보, 날씨, 좌석 추천, 예매 가이드를 출처와 기준 시점까지 함께
              확인합니다.
            </Description>
          </Copy>
          <ChatComposer disabled={isStreaming} onSendMessage={handleSendMessage} />
          {errorMessage ? <ErrorText>{errorMessage}</ErrorText> : null}
          <FooterActions>
            <Button type="button" variant="ghost" onClick={() => openSourceDrawer(true)}>
              출처 패널 열기
            </Button>
          </FooterActions>
        </Hero>
      )}
    </Panel>
  );
}

const Panel = styled.main<{ $hasMessages: boolean }>`
  display: flex;
  align-items: ${({ $hasMessages }) => ($hasMessages ? "stretch" : "center")};
  justify-content: center;
  min-width: 0;
  min-height: calc(100vh - 72px);
  padding: ${({ $hasMessages }) => ($hasMessages ? "0 20px" : "48px 20px")};
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(247, 248, 243, 0.96)),
    radial-gradient(circle at 50% 18%, rgba(217, 70, 53, 0.1), transparent 34%),
    ${({ theme }) => theme.color.background};

  @media (max-width: 720px) {
    min-height: calc(100vh - 64px);
    padding: ${({ $hasMessages }) => ($hasMessages ? "0 14px" : "36px 14px")};
  }
`;

const ChatWorkspace = styled.section`
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  width: min(100%, 920px);
  min-height: calc(100vh - 72px);

  @media (max-width: 720px) {
    min-height: calc(100vh - 64px);
  }
`;

const MessageList = styled.div`
  display: flex;
  overflow-y: auto;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  padding: 28px 0 18px;
`;

const Dock = styled.div`
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 14px 0 24px;
  background: linear-gradient(180deg, rgba(247, 248, 243, 0), ${({ theme }) => theme.color.background} 22%);
`;

const Hero = styled.section`
  display: grid;
  justify-items: center;
  gap: 24px;
  width: min(100%, 820px);
`;

const LogoWrap = styled.div`
  position: relative;
  display: grid;
  width: 82px;
  height: 82px;
  place-items: center;
`;

const LogoRing = styled.div`
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(from 120deg, #136f4a, #f7c948, #d94635, #136f4a), #ffffff;
  animation: logo-spin 9s linear infinite;

  &::after {
    position: absolute;
    inset: 15px;
    border-radius: 50%;
    background: ${({ theme }) => theme.color.background};
    content: "";
  }

  @keyframes logo-spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const LogoCore = styled.div`
  position: relative;
  z-index: 1;
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  background: #ffffff;
  color: ${({ theme }) => theme.color.primary};
  font-size: 24px;
  font-weight: 950;
  box-shadow: 0 10px 30px rgba(19, 111, 74, 0.12);
`;

const Copy = styled.div`
  display: grid;
  justify-items: center;
  gap: 10px;
  text-align: center;
`;

const Eyebrow = styled.p`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: ${({ theme }) => theme.color.primary};
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
`;

const Heading = styled.h1`
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: clamp(30px, 4vw, 44px);
  line-height: 1.14;
  word-break: keep-all;
`;

const Description = styled.p`
  max-width: 680px;
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 16px;
  line-height: 1.65;
  word-break: keep-all;
`;

const FooterActions = styled.div`
  display: flex;
  justify-content: center;
`;

const ErrorText = styled.p`
  width: min(100%, 760px);
  margin: 0;
  border: 1px solid rgba(217, 70, 53, 0.22);
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 10px 12px;
  background: rgba(217, 70, 53, 0.08);
  color: ${({ theme }) => theme.color.accent};
  font-size: 13px;
  font-weight: 700;
`;
