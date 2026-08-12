"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSetAtom } from "jotai";
import { ListChecks, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import styled from "styled-components";
import type { ChatMessage } from "@/entities/message/model/types";
import { MessageBubble } from "@/entities/message/ui/message-bubble";
import type { ToolResult, ToolResultName } from "@/entities/tool-result/model/types";
import {
  streamChatMessage,
  type ChatStreamEvent,
  type ChatStreamMessage,
} from "@/features/chat-stream/api/stream-chat-message";
import { isLoginModalOpenAtom } from "@/features/auth/model/auth-modal.atom";
import { useCurrentUser } from "@/features/auth/model/auth-query";
import { conversationListQueryKey } from "@/features/conversation-list/model/conversation-list-query";
import { ChatComposer } from "@/features/send-message/ui/chat-composer";
import { Button } from "@/shared/ui/button";
import { isSourceDrawerOpenAtom } from "@/widgets/source-drawer/model/source-drawer.atom";

type ResponseStatus = "idle" | "streaming" | "failed" | ToolResultName;

const responseStatusLabels: Record<ResponseStatus, string> = {
  idle: "준비됨",
  streaming: "답변 작성 중",
  failed: "응답 실패",
  find_kbo_game: "경기 일정 확인 중",
  get_stadium_info: "구장 정보 확인 중",
  get_weather_context: "날씨 확인 중",
  search_stadium_guide: "구장 가이드 검색 중",
  search_ticketing_guide: "예매 정보 검색 중",
  search_baseball_knowledge: "야구 지식 검색 중",
};

const toolDisplayLabels: Record<ToolResultName, string> = {
  find_kbo_game: "경기 일정",
  get_stadium_info: "구장 정보",
  get_weather_context: "구장 날씨",
  search_stadium_guide: "구장 가이드",
  search_ticketing_guide: "예매 안내",
  search_baseball_knowledge: "야구 지식",
};

export function ChatPanel() {
  const queryClient = useQueryClient();
  const openSourceDrawer = useSetAtom(isSourceDrawerOpenAtom);
  const openLoginModal = useSetAtom(isLoginModalOpenAtom);
  const { data: user, isLoading: isCheckingAuth } = useCurrentUser();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [responseStatus, setResponseStatus] = useState<ResponseStatus>("idle");
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failedRequestMessage, setFailedRequestMessage] = useState<string | null>(null);
  const [isActivityOpen, setIsActivityOpen] = useState(false);
  const [activeAssistantMessageId, setActiveAssistantMessageId] = useState<string | null>(null);
  const pendingUserMessageIdRef = useRef<string | null>(null);
  const activeAssistantMessageIdRef = useRef<string | null>(null);
  const lastSubmittedMessageRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const handleSendMessage = (message: string) => {
    if (isStreaming) {
      return;
    }

    if (!user) {
      openLoginModal(true);
      setErrorMessage("로그인 후 채팅을 시작할 수 있습니다.");
      return;
    }

    const pendingUserMessageId = `local_user_${window.crypto.randomUUID()}`;
    const pendingAssistantMessageId = `local_assistant_${window.crypto.randomUUID()}`;
    lastSubmittedMessageRef.current = message;
    pendingUserMessageIdRef.current = pendingUserMessageId;
    activeAssistantMessageIdRef.current = pendingAssistantMessageId;
    setActiveAssistantMessageId(pendingAssistantMessageId);
    setErrorMessage(null);
    setFailedRequestMessage(null);
    setResponseStatus("streaming");
    setIsStreaming(true);
    setMessages((prev) => [
      ...prev,
      {
        id: pendingUserMessageId,
        role: "user",
        content: message,
        createdAt: new Date().toISOString(),
      },
      {
        id: pendingAssistantMessageId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        toolResults: [],
      },
    ]);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    void consumeChatStream({
      conversationId,
      message,
      signal: abortController.signal,
    });
  };

  const consumeChatStream = async ({
    conversationId,
    message,
    signal,
  }: {
    conversationId: string | null;
    message: string;
    signal: AbortSignal;
  }) => {
    try {
      for await (const event of streamChatMessage({ conversationId, message }, signal)) {
        applyStreamEvent(event);
      }
    } catch (error) {
      if (signal.aborted) {
        return;
      }

      const message = error instanceof Error ? error.message : "채팅 응답을 불러오지 못했습니다.";
      setErrorMessage(message);
      setFailedRequestMessage(lastSubmittedMessageRef.current);
      setResponseStatus("failed");
      ensureAssistantMessage("응답을 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsStreaming(false);
      setResponseStatus((current) => (current === "failed" ? current : "idle"));
      abortControllerRef.current = null;
      pendingUserMessageIdRef.current = null;
    }
  };

  const applyStreamEvent = (event: ChatStreamEvent) => {
    switch (event.type) {
      case "conversation.created":
        setConversationId(event.conversationId);
        return;
      case "message.created":
        applyMessageCreated(event.message);
        return;
      case "tool.started":
        setResponseStatus(event.name);
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
        setResponseStatus("streaming");
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
        setResponseStatus("failed");
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
        setResponseStatus("streaming");
        {
          const previousAssistantMessageId = activeAssistantMessageIdRef.current;
          activeAssistantMessageIdRef.current = event.messageId;
          setActiveAssistantMessageId(event.messageId);
          appendAssistantDelta(event.messageId, event.delta, previousAssistantMessageId);
        }
        return;
      case "assistant.completed":
        setResponseStatus("streaming");
        {
          const previousAssistantMessageId = activeAssistantMessageIdRef.current;
          activeAssistantMessageIdRef.current = event.messageId;
          setActiveAssistantMessageId(event.messageId);
          setMessages((prev) => {
            if (prev.some((item) => item.id === event.messageId)) {
              return prev.map((item) =>
                item.id === event.messageId ? { ...item, content: event.content } : item,
              );
            }

            if (previousAssistantMessageId?.startsWith("local_assistant_")) {
              return prev.map((item) =>
                item.id === previousAssistantMessageId
                  ? { ...item, id: event.messageId, content: event.content }
                  : item,
              );
            }

            return prev;
          });
        }
        return;
      case "stream.failed":
        setErrorMessage(event.error.message);
        setFailedRequestMessage(lastSubmittedMessageRef.current);
        setResponseStatus("failed");
        ensureAssistantMessage("응답을 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.");
        return;
      case "conversation.updated":
        void queryClient.invalidateQueries({ queryKey: conversationListQueryKey });
        return;
      case "done":
        void queryClient.invalidateQueries({ queryKey: conversationListQueryKey });
        setResponseStatus((current) => (current === "failed" ? current : "idle"));
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
      const previousAssistantMessageId = activeAssistantMessageIdRef.current;
      activeAssistantMessageIdRef.current = message.id;
      setActiveAssistantMessageId(message.id);

      setMessages((prev) => {
        if (prev.some((item) => item.id === message.id)) {
          return prev;
        }

        if (previousAssistantMessageId?.startsWith("local_assistant_")) {
          const hasLocalAssistantMessage = prev.some((item) => item.id === previousAssistantMessageId);

          if (!hasLocalAssistantMessage) {
            return [...prev, chatMessage];
          }

          return prev.map((item) =>
            item.id === previousAssistantMessageId
              ? {
                  ...chatMessage,
                  content: chatMessage.content || item.content,
                  toolResults: item.toolResults ?? [],
                }
              : item,
          );
        }

        return [...prev, chatMessage];
      });
      return;
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
    setActiveAssistantMessageId(messageId);

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

  const appendAssistantDelta = (
    messageId: string,
    delta: string,
    previousAssistantMessageId: string | null,
  ) => {
    setMessages((prev) => {
      if (!prev.some((item) => item.id === messageId)) {
        if (previousAssistantMessageId?.startsWith("local_assistant_")) {
          const hasLocalAssistantMessage = prev.some((item) => item.id === previousAssistantMessageId);

          if (hasLocalAssistantMessage) {
            return prev.map((item) =>
              item.id === previousAssistantMessageId
                ? { ...item, id: messageId, content: `${item.content}${delta}` }
                : item,
            );
          }
        }

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
  const currentStatusLabel = responseStatusLabels[responseStatus];
  const activityItems = messages.flatMap((message) => message.toolResults ?? []);
  const hasActivity = activityItems.length > 0 || isStreaming || errorMessage;
  const handleRetry = () => {
    if (!failedRequestMessage || isStreaming) {
      return;
    }

    handleSendMessage(failedRequestMessage);
  };

  return (
    <Panel $hasMessages={hasMessages}>
      {hasMessages ? (
        <ChatWorkspace>
          <MessageList aria-live="polite">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                isStreaming={isStreaming && message.id === activeAssistantMessageId}
              />
            ))}
            {errorMessage ? (
              <ErrorBlock role="alert">
                <ErrorText>{errorMessage}</ErrorText>
                <RetryButton type="button" disabled={isStreaming} onClick={handleRetry}>
                  다시 시도
                </RetryButton>
              </ErrorBlock>
            ) : null}
          </MessageList>
          <Dock>
            <ChatComposer
              disabled={isStreaming || isCheckingAuth}
              showSuggestions={false}
              onSendMessage={handleSendMessage}
            />
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
          <ChatComposer
            disabled={isStreaming || isCheckingAuth}
            onSendMessage={handleSendMessage}
          />
          {errorMessage ? <ErrorText>{errorMessage}</ErrorText> : null}
          <FooterActions>
            <Button type="button" variant="ghost" onClick={() => openSourceDrawer(true)}>
              출처 패널 열기
            </Button>
          </FooterActions>
        </Hero>
      )}
      <ActivityButton
        type="button"
        aria-expanded={isActivityOpen}
        aria-controls="chat-activity-panel"
        onClick={() => setIsActivityOpen((prev) => !prev)}
      >
        <ListChecks size={18} />
        작업 내역
        {hasActivity ? <ActivityDot aria-hidden="true" /> : null}
      </ActivityButton>
      {isActivityOpen ? (
        <ActivityPanel id="chat-activity-panel">
          <ActivityHeader>
            <ActivityTitle>작업 내역</ActivityTitle>
            <ActivityCloseButton
              type="button"
              aria-label="작업 내역 닫기"
              onClick={() => setIsActivityOpen(false)}
            >
              <X size={16} />
            </ActivityCloseButton>
          </ActivityHeader>
          <ActivityList>
            {activityItems.length ? (
              activityItems.map((item) => (
                <ActivityItem key={item.id}>
                  <ActivityName>{toolLabel(item.name)}</ActivityName>
                  <StatusBadge $status={item.status === "failed" ? "failed" : item.status === "running" ? item.name : "idle"}>
                    {item.status === "running"
                      ? "진행 중"
                      : item.status === "failed"
                        ? "실패"
                        : "완료"}
                  </StatusBadge>
                </ActivityItem>
              ))
            ) : (
              <ActivityEmpty>{currentStatusLabel}</ActivityEmpty>
            )}
          </ActivityList>
        </ActivityPanel>
      ) : null}
    </Panel>
  );
}

const toolLabel = (name: ToolResultName) => toolDisplayLabels[name];

const Panel = styled.main<{ $hasMessages: boolean }>`
  display: flex;
  align-items: ${({ $hasMessages }) => ($hasMessages ? "stretch" : "center")};
  justify-content: center;
  min-width: 0;
  min-height: 100vh;
  padding: ${({ $hasMessages }) => ($hasMessages ? "0 20px" : "48px 20px")};
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(247, 248, 243, 0.96)),
    radial-gradient(circle at 50% 18%, rgba(217, 70, 53, 0.1), transparent 34%),
    ${({ theme }) => theme.color.background};

  @media (max-width: 720px) {
    padding: ${({ $hasMessages }) => ($hasMessages ? "0 14px" : "36px 14px")};
  }
`;

const ChatWorkspace = styled.section`
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  width: min(100%, 920px);
  min-height: 100vh;
`;

const StatusBadge = styled.span<{ $status: ResponseStatus }>`
  display: inline-flex;
  flex: 0 0 auto;
  min-height: 28px;
  align-items: center;
  border: 1px solid
    ${({ $status, theme }) =>
      $status === "failed" ? "rgba(217, 70, 53, 0.26)" : theme.color.border};
  border-radius: 999px;
  padding: 0 10px;
  background: ${({ $status, theme }) =>
    $status === "failed"
      ? "rgba(217, 70, 53, 0.08)"
      : $status === "idle"
        ? theme.color.panel
        : "rgba(19, 111, 74, 0.1)"};
  color: ${({ $status, theme }) =>
    $status === "failed"
      ? theme.color.accent
      : $status === "idle"
        ? theme.color.muted
        : theme.color.primary};
  font-size: 12px;
  font-weight: 850;
  white-space: nowrap;
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

const ErrorBlock = styled.div`
  display: flex;
  width: min(100%, 760px);
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid rgba(217, 70, 53, 0.22);
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 10px 12px;
  background: rgba(217, 70, 53, 0.08);

  ${ErrorText} {
    width: auto;
    border: 0;
    padding: 0;
    background: transparent;
  }
`;

const RetryButton = styled.button`
  flex: 0 0 auto;
  border: 1px solid rgba(217, 70, 53, 0.24);
  border-radius: 999px;
  padding: 7px 10px;
  background: ${({ theme }) => theme.color.panel};
  color: ${({ theme }) => theme.color.accent};
  font-size: 12px;
  font-weight: 850;

  &:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
`;

const ActivityButton = styled.button`
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 25;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  border: 1px solid rgba(19, 111, 74, 0.2);
  border-radius: 999px;
  padding: 0 14px;
  background: ${({ theme }) => theme.color.panel};
  color: ${({ theme }) => theme.color.primary};
  font-size: 13px;
  font-weight: 900;
  box-shadow: ${({ theme }) => theme.shadow.panel};

  @media (max-width: 560px) {
    right: 14px;
    bottom: 14px;
  }
`;

const ActivityDot = styled.span`
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.accent};
`;

const ActivityPanel = styled.aside`
  position: fixed;
  right: 22px;
  bottom: 74px;
  z-index: 24;
  display: grid;
  gap: 12px;
  width: min(340px, calc(100vw - 28px));
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 14px;
  background: ${({ theme }) => theme.color.panel};
  box-shadow: ${({ theme }) => theme.shadow.panel};

  @media (max-width: 560px) {
    right: 14px;
    bottom: 66px;
  }
`;

const ActivityHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
`;

const ActivityTitle = styled.h2`
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 15px;
`;

const ActivityCloseButton = styled.button`
  display: inline-grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.panelAlt};
  color: ${({ theme }) => theme.color.muted};
`;

const ActivityList = styled.div`
  display: grid;
  gap: 8px;
`;

const ActivityItem = styled.div`
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 10px;
  background: ${({ theme }) => theme.color.panelAlt};
`;

const ActivityName = styled.span`
  min-width: 0;
  overflow: hidden;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 13px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const ActivityEmpty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
  font-weight: 750;
`;
