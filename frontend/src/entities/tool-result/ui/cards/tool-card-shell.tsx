"use client";

import type { ReactNode } from "react";
import styled from "styled-components";
import type { ToolResultStatus } from "@/entities/tool-result/model/types";

type ToolCardShellProps = {
  icon: ReactNode;
  title: string;
  status: ToolResultStatus;
  children: ReactNode;
  meta?: ReactNode;
};

const statusLabel: Record<ToolResultStatus, string> = {
  running: "조회 중",
  completed: "완료",
  failed: "확인 필요",
};

export function ToolCardShell({ icon, title, status, children, meta }: ToolCardShellProps) {
  return (
    <Card $status={status}>
      <TopLine>
        <TitleWrap>
          <IconWrap $status={status}>{icon}</IconWrap>
          <Title>{title}</Title>
        </TitleWrap>
        <Status $status={status}>{statusLabel[status]}</Status>
      </TopLine>
      <Body>{children}</Body>
      {meta ? <Meta>{meta}</Meta> : null}
    </Card>
  );
}

export const Summary = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 14px;
  line-height: 1.72;
  white-space: pre-wrap;
  word-break: keep-all;
`;

export const Highlight = styled.div`
  display: grid;
  gap: 5px;
  border-left: 3px solid #c8c8c8;
  padding: 7px 0 7px 12px;
  background: transparent;
`;

export const HighlightTitle = styled.strong`
  color: ${({ theme }) => theme.color.foreground};
  font-size: 15px;
  line-height: 1.35;
`;

export const HighlightMeta = styled.span`
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
  line-height: 1.45;
`;

export const LoadingDots = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 6px;

  span {
    width: 5px;
    height: 5px;
    border-radius: 999px;
    background: ${({ theme }) => theme.color.info};
    animation: tool-loading 900ms ease-in-out infinite;
  }

  span:nth-child(2) {
    animation-delay: 120ms;
  }

  span:nth-child(3) {
    animation-delay: 240ms;
  }

  @keyframes tool-loading {
    0%,
    80%,
    100% {
      opacity: 0.3;
      transform: translateY(0);
    }

    40% {
      opacity: 1;
      transform: translateY(-2px);
    }
  }
`;

export const DataGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(150px, 1fr));
  overflow: hidden;
  border: 1px solid #e7e7e7;
  border-radius: ${({ theme }) => theme.radius.md};
  background: #e7e7e7;
  gap: 1px;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`;

export const DataItem = styled.div`
  display: grid;
  grid-template-columns: minmax(64px, 0.4fr) minmax(0, 1fr);
  align-items: start;
  gap: 10px;
  min-width: 0;
  padding: 10px 12px;
  background: #ffffff;

  &:nth-child(-n + 2) {
    background: #f7f7f7;
  }
`;

export const Label = styled.span`
  color: #4f4f4f;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
`;

export const Value = styled.span`
  min-width: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  overflow-wrap: anywhere;
`;

export const EvidenceList = styled.div`
  display: grid;
  gap: 10px;
`;

export const EvidenceItem = styled.div`
  display: grid;
  gap: 6px;
  border-left: 3px solid #c8c8c8;
  padding: 4px 0 4px 12px;
  background: transparent;
`;

export const EvidenceTitle = styled.strong`
  color: ${({ theme }) => theme.color.foreground};
  font-size: 14px;
  line-height: 1.45;
`;

export const EvidenceText = styled.p`
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #6c6c6c;
  font-size: 13px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
`;

export const EvidenceMeta = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
`;

const Card = styled.article<{ $status: ToolResultStatus }>`
  display: grid;
  overflow: hidden;
  gap: 12px;
  border: 1px solid #e6e6e6;
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 0;
  background: #ffffff;
`;

const TopLine = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #e9e9e9;
  padding: 9px 12px;
  background: #f7f7f7;
`;

const TitleWrap = styled.div`
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
`;

const IconWrap = styled.span<{ $status: ToolResultStatus }>`
  display: inline-grid;
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  place-items: center;
  color: ${({ $status, theme }) =>
    $status === "failed" ? theme.color.accent : $status === "running" ? theme.color.info : "#555555"};
`;

const Title = styled.h3`
  min-width: 0;
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 13px;
  font-weight: 750;
  line-height: 1.35;
  overflow-wrap: anywhere;
`;

const Status = styled.span<{ $status: ToolResultStatus }>`
  flex: 0 0 auto;
  border-radius: 999px;
  border: 1px solid #e3e3e3;
  padding: 2px 7px;
  background: ${({ $status, theme }) =>
    $status === "failed" ? "#fff3f1" : $status === "running" ? "#f1f7fc" : theme.color.panel};
  color: ${({ $status, theme }) =>
    $status === "failed"
      ? theme.color.accent
      : $status === "running"
        ? theme.color.info
        : "#666666"};
  font-size: 11px;
  font-weight: 650;
`;

const Body = styled.div`
  display: grid;
  gap: 12px;
  padding: 12px;
`;

const Meta = styled.div`
  color: ${({ theme }) => theme.color.muted};
  font-size: 12px;
  line-height: 1.5;
  padding: 0 12px 12px;
`;
