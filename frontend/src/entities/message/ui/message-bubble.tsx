"use client";

import styled from "styled-components";
import type { ChatMessage } from "@/entities/message/model/types";
import { ToolResultCard } from "@/entities/tool-result/ui/tool-result-card";

type MessageBubbleProps = {
  message: ChatMessage;
  isStreaming?: boolean;
};

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const toolResults = message.toolResults ?? [];
  const shouldShowTyping = !isUser && isStreaming && !message.content.trim();
  const hasContent = Boolean(message.content.trim());
  const hasToolResults = toolResults.length > 0;

  if (!hasContent && !hasToolResults && !shouldShowTyping) {
    return null;
  }

  if (!isUser) {
    return (
      <AssistantFrame>
        <AssistantProfile>
          <AssistantLogo src="/brand/flaming-baseball-logo.webp" alt="" />
          <AssistantName>KBO Mate</AssistantName>
        </AssistantProfile>
        <AssistantCard>
          {hasContent ? <Body>{message.content}</Body> : null}
          {shouldShowTyping ? (
            <TypingIndicator $hasFollowingContent={hasToolResults} aria-label="답변 작성 중">
              <TypingDot />
              <TypingDot />
              <TypingDot />
            </TypingIndicator>
          ) : null}
          {hasToolResults ? (
            <ToolList>
              {toolResults.map((result) => (
                <ToolResultCard key={result.id} result={result} />
              ))}
            </ToolList>
          ) : null}
        </AssistantCard>
      </AssistantFrame>
    );
  }

  return (
    <Bubble>
      {hasContent ? <Body>{message.content}</Body> : null}
    </Bubble>
  );
}

const Bubble = styled.article`
  width: min(100%, 720px);
  margin-left: auto;
  border: 1px solid #d8dadd;
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 13px 15px;
  background: #f4f5f6;
  color: #111111;
`;

const AssistantFrame = styled.article`
  display: grid;
  gap: 8px;
  width: min(100%, 820px);
`;

const AssistantProfile = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  color: ${({ theme }) => theme.color.foreground};
`;

const AssistantLogo = styled.img`
  width: 26px;
  height: 26px;
  object-fit: contain;
`;

const AssistantName = styled.span`
  color: ${({ theme }) => theme.color.foreground};
  font-size: 15px;
  font-weight: 900;
`;

const AssistantCard = styled.div`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 15px 16px;
  background: ${({ theme }) => theme.color.panel};
  box-shadow: 0 8px 26px rgba(18, 32, 25, 0.05);
`;

const Body = styled.p`
  margin: 0;
  color: inherit;
  font-size: 15px;
  line-height: 1.78;
  white-space: pre-wrap;
  word-break: keep-all;
`;

const ToolList = styled.div`
  display: grid;
  gap: 12px;
  margin-top: 12px;

  &:first-child {
    margin-top: 0;
  }
`;

const TypingIndicator = styled.div<{ $hasFollowingContent: boolean }>`
  display: inline-flex;
  width: fit-content;
  align-items: center;
  gap: 5px;
  margin-bottom: ${({ $hasFollowingContent }) => ($hasFollowingContent ? "12px" : 0)};
  border-radius: 999px;
  padding: 8px 10px;
  background: ${({ theme }) => theme.color.panelAlt};
`;

const TypingDot = styled.span`
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.primary};
  animation: typing-bounce 880ms ease-in-out infinite;

  &:nth-child(2) {
    animation-delay: 120ms;
  }

  &:nth-child(3) {
    animation-delay: 240ms;
  }

  @keyframes typing-bounce {
    0%,
    80%,
    100% {
      opacity: 0.35;
      transform: translateY(0);
    }

    40% {
      opacity: 1;
      transform: translateY(-3px);
    }
  }
`;
