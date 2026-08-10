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

  return (
    <Bubble $isUser={isUser}>
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
    </Bubble>
  );
}

const Bubble = styled.article<{ $isUser: boolean }>`
  width: min(100%, ${({ $isUser }) => ($isUser ? "720px" : "820px")});
  margin-left: ${({ $isUser }) => ($isUser ? "auto" : 0)};
  border: 1px solid ${({ theme, $isUser }) => ($isUser ? theme.color.primary : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 16px;
  background: ${({ theme, $isUser }) => ($isUser ? "#edf7f0" : theme.color.panel)};
`;

const Body = styled.p`
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
`;

const ToolList = styled.div`
  display: grid;
  gap: 10px;
  margin-top: 14px;

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
