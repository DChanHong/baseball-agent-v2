"use client";

import styled from "styled-components";
import type { ChatMessage } from "@/entities/message/model/types";
import { ToolResultCard } from "@/entities/tool-result/ui/tool-result-card";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <Bubble $isUser={isUser}>
      <Body>{message.content}</Body>
      {message.toolResults?.length ? (
        <ToolList>
          {message.toolResults.map((result) => (
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
`;
