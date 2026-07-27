"use client";

import { useAtom } from "jotai";
import styled from "styled-components";
import { isSourceDrawerOpenAtom } from "@/widgets/source-drawer/model/source-drawer.atom";
import { Button } from "@/shared/ui/button";

export function SourceDrawer() {
  const [isOpen, setIsOpen] = useAtom(isSourceDrawerOpenAtom);

  return (
    <Aside $isOpen={isOpen} aria-label="출처와 근거">
      <TopLine>
        <Title>출처</Title>
        <Button type="button" variant="ghost" onClick={() => setIsOpen(false)}>
          닫기
        </Button>
      </TopLine>
      <EmptyText>Agent가 사용한 문서, 기준 시점, 한계가 이 영역에 표시됩니다.</EmptyText>
    </Aside>
  );
}

const Aside = styled.aside<{ $isOpen: boolean }>`
  display: ${({ $isOpen }) => ($isOpen ? "grid" : "none")};
  position: fixed;
  top: 72px;
  right: 0;
  bottom: 0;
  z-index: 10;
  width: min(100vw, 360px);
  align-content: start;
  gap: 14px;
  border-left: 1px solid ${({ theme }) => theme.color.border};
  padding: 18px;
  background: ${({ theme }) => theme.color.panel};
  box-shadow: ${({ theme }) => theme.shadow.panel};
`;

const TopLine = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

const Title = styled.h2`
  margin: 0;
  font-size: 16px;
`;

const EmptyText = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  line-height: 1.6;
`;
