"use client";

import type { ReactNode } from "react";
import styled, { css } from "styled-components";
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
    <Card>
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
  line-height: 1.6;
  white-space: pre-wrap;
`;

export const DataGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`;

export const DataItem = styled.div`
  display: grid;
  gap: 3px;
  min-width: 0;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 10px;
  background: ${({ theme }) => theme.color.panelAlt};
`;

export const Label = styled.span`
  color: ${({ theme }) => theme.color.muted};
  font-size: 12px;
  font-weight: 800;
`;

export const Value = styled.span`
  min-width: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 14px;
  font-weight: 800;
  line-height: 1.45;
  overflow-wrap: anywhere;
`;

export const EvidenceList = styled.div`
  display: grid;
  gap: 8px;
`;

export const EvidenceItem = styled.div`
  display: grid;
  gap: 4px;
  border-left: 3px solid ${({ theme }) => theme.color.primary};
  padding-left: 10px;
`;

export const EvidenceTitle = styled.strong`
  color: ${({ theme }) => theme.color.foreground};
  font-size: 14px;
`;

export const EvidenceText = styled.p`
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
`;

const Card = styled.article`
  display: grid;
  gap: 12px;
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

const TitleWrap = styled.div`
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
`;

const IconWrap = styled.span<{ $status: ToolResultStatus }>`
  display: inline-grid;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: ${({ theme }) => theme.radius.sm};

  ${({ $status, theme }) =>
    $status === "failed"
      ? css`
          background: #fde8e5;
          color: ${theme.color.accent};
        `
      : $status === "running"
        ? css`
            background: #e7f0f8;
            color: ${theme.color.info};
          `
        : css`
            background: #e9f6ef;
            color: ${theme.color.primary};
          `}
`;

const Title = styled.h3`
  min-width: 0;
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 15px;
  overflow-wrap: anywhere;
`;

const Status = styled.span<{ $status: ToolResultStatus }>`
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 8px;
  background: ${({ $status, theme }) =>
    $status === "failed" ? "#fde8e5" : $status === "running" ? "#e7f0f8" : theme.color.panelAlt};
  color: ${({ $status, theme }) =>
    $status === "failed"
      ? theme.color.accent
      : $status === "running"
        ? theme.color.info
        : theme.color.primary};
  font-size: 12px;
  font-weight: 800;
`;

const Body = styled.div`
  display: grid;
  gap: 10px;
`;

const Meta = styled.div`
  color: ${({ theme }) => theme.color.muted};
  font-size: 12px;
  line-height: 1.5;
`;
