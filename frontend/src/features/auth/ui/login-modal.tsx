"use client";

import { Mail } from "lucide-react";
import styled from "styled-components";
import { startGoogleOAuth } from "@/features/auth/api/auth-api";
import { useGlobalModal } from "@/features/global-modal/model/use-global-modal";
import { Button } from "@/shared/ui/button";
import { Modal } from "@/shared/ui/modal";

export function LoginModal() {
  const { closeGlobalModal, isLoginModalOpen } = useGlobalModal();

  return (
    <Modal isOpen={isLoginModalOpen} title="로그인" onClose={closeGlobalModal}>
      <Content>
        <Description>
          대화 기록과 선호 팀, 예산, 좌석 성향을 저장하기 위한 로그인 영역입니다.
        </Description>
        <Button type="button" variant="primary" onClick={startGoogleOAuth}>
          <ButtonContent>
            <Mail aria-hidden="true" size={18} />
            Google로 계속하기
          </ButtonContent>
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

const ButtonContent = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
`;
