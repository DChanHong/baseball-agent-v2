"use client";

import { useAtom } from "jotai";
import styled from "styled-components";
import { isLoginModalOpenAtom } from "@/features/auth/model/auth-modal.atom";
import { Button } from "@/shared/ui/button";
import { Modal } from "@/shared/ui/modal";

export function LoginModal() {
  const [isOpen, setIsOpen] = useAtom(isLoginModalOpenAtom);

  return (
    <Modal isOpen={isOpen} title="로그인" onClose={() => setIsOpen(false)}>
      <Content>
        <Description>
          대화 기록과 선호 팀, 예산, 좌석 성향을 저장하기 위한 로그인 영역입니다.
        </Description>
        <Field>
          <Label htmlFor="email">이메일</Label>
          <Input id="email" type="email" placeholder="you@example.com" />
        </Field>
        <Button type="button" variant="primary">
          이메일로 계속하기
        </Button>
      </Content>
    </Modal>
  );
}

const Content = styled.div`
  display: grid;
  gap: 16px;
  padding: 20px;
`;

const Description = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  line-height: 1.6;
`;

const Field = styled.div`
  display: grid;
  gap: 8px;
`;

const Label = styled.label`
  font-size: 13px;
  font-weight: 700;
`;

const Input = styled.input`
  min-height: 42px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 12px;
`;
