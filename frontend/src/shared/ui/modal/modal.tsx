"use client";

import type { ReactNode } from "react";
import styled from "styled-components";
import { Button } from "@/shared/ui/button";

type ModalProps = {
  children: ReactNode;
  isOpen: boolean;
  title: string;
  onClose: () => void;
};

export function Modal({ children, isOpen, title, onClose }: ModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <Overlay role="presentation" onMouseDown={onClose}>
      <Dialog
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <Header>
          <Title id="modal-title">{title}</Title>
          <Button type="button" variant="ghost" onClick={onClose} aria-label="모달 닫기">
            닫기
          </Button>
        </Header>
        {children}
      </Dialog>
    </Overlay>
  );
}

const Overlay = styled.div`
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(17, 26, 22, 0.38);
`;

const Dialog = styled.div`
  width: min(100%, 440px);
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.panel};
  box-shadow: ${({ theme }) => theme.shadow.panel};
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

const Title = styled.h2`
  margin: 0;
  font-size: 18px;
`;
