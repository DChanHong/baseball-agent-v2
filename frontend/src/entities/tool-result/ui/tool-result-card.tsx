"use client";

import styled from "styled-components";
import type { ToolResult } from "@/entities/tool-result/model/types";

type ToolResultCardProps = {
  result: ToolResult;
};

const statusLabel = {
  idle: "대기",
  running: "진행 중",
  success: "완료",
  error: "확인 필요",
};

export function ToolResultCard({ result }: ToolResultCardProps) {
  return (
    <Card>
      <TopLine>
        <Title>{result.title}</Title>
        <Status $status={result.status}>{statusLabel[result.status]}</Status>
      </TopLine>
      <Summary>{result.summary}</Summary>
      {result.asOf ? <Meta>기준 시점 {result.asOf}</Meta> : null}
    </Card>
  );
}

const Card = styled.article`
  display: grid;
  gap: 8px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 14px;
  background: ${({ theme }) => theme.color.panel};
`;

const TopLine = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
`;

const Title = styled.h3`
  margin: 0;
  font-size: 15px;
`;

const Status = styled.span<{ $status: ToolResult["status"] }>`
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 8px;
  background: ${({ $status, theme }) =>
    $status === "error" ? "#fde8e5" : $status === "running" ? "#e7f0f8" : theme.color.panelAlt};
  color: ${({ $status, theme }) =>
    $status === "error"
      ? theme.color.accent
      : $status === "running"
        ? theme.color.info
        : theme.color.primary};
  font-size: 12px;
  font-weight: 700;
`;

const Summary = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  line-height: 1.55;
`;

const Meta = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
`;
