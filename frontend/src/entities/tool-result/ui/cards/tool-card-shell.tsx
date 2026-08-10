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
  font-size: 15px;
  line-height: 1.72;
  white-space: pre-wrap;
  word-break: keep-all;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.border};
  gap: 1px;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`;

export const DataItem = styled.div`
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 12px 14px;
  background: #f6faf7;
`;

export const Label = styled.span`
  color: ${({ theme }) => theme.color.muted};
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0;
`;

export const Value = styled.span`
  min-width: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 15px;
  font-weight: 900;
  line-height: 1.35;
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

const Card = styled.article<{ $status: ToolResultStatus }>`
  position: relative;
  display: grid;
  overflow: hidden;
  gap: 14px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 16px;
  background:
    linear-gradient(
      90deg,
      ${({ $status }) =>
          $status === "failed"
            ? "rgba(217, 70, 53, 0.08)"
            : $status === "running"
              ? "rgba(29, 95, 145, 0.08)"
              : "rgba(19, 111, 74, 0.08)"}
        0,
      rgba(255, 255, 255, 0) 110px
    ),
    ${({ theme }) => theme.color.panel};

  &::before {
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: ${({ $status, theme }) =>
      $status === "failed"
        ? theme.color.accent
        : $status === "running"
          ? theme.color.info
          : theme.color.primary};
    content: "";
  }
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
  width: 36px;
  height: 36px;
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
  font-size: 16px;
  line-height: 1.35;
  overflow-wrap: anywhere;
`;

const Status = styled.span<{ $status: ToolResultStatus }>`
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 5px 9px;
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
  gap: 12px;
`;

const Meta = styled.div`
  color: ${({ theme }) => theme.color.muted};
  font-size: 12px;
  line-height: 1.5;
`;
