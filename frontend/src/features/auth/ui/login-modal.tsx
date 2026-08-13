"use client";

import styled from "styled-components";
import { startGoogleOAuth } from "@/features/auth/api/auth-api";
import { useGlobalModal } from "@/features/global-modal/model/use-global-modal";
import { Modal } from "@/shared/ui/modal";

export function LoginModal() {
  const { closeGlobalModal, isLoginModalOpen } = useGlobalModal();

  return (
    <Modal isOpen={isLoginModalOpen} title="로그인 또는 회원가입" onClose={closeGlobalModal} showHeader={false}>
      <Content>
        <LogoImage src="/brand/flaming-baseball-logo.webp" alt="" />
        <Title>로그인 또는 회원가입</Title>
        <Description>KBO Mate와 함께 관람 계획을 시작하세요</Description>
        <GoogleButton type="button" onClick={startGoogleOAuth}>
          <GoogleMark aria-hidden="true">G</GoogleMark>
          <ButtonLabel>Google로 계속하기</ButtonLabel>
        </GoogleButton>
      </Content>
    </Modal>
  );
}

const Content = styled.div`
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 42px 28px 32px;
`;

const LogoImage = styled.img`
  width: 68px;
  height: 68px;
  object-fit: contain;
  margin-bottom: 10px;
`;

const Title = styled.h2`
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 24px;
  font-weight: 800;
  line-height: 1.25;
`;

const Description = styled.p`
  margin: 0;
  padding-bottom: 24px;
  color: ${({ theme }) => theme.color.muted};
  font-size: 14px;
  line-height: 1.5;
  text-align: center;
`;

const GoogleButton = styled.button`
  position: relative;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 24px;
  align-items: center;
  width: min(100%, 360px);
  min-height: 42px;
  border: 1px solid #e4e8e5;
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 0 20px;
  background: ${({ theme }) => theme.color.panel};
  color: #2f3531;
  box-shadow: 0 2px 8px rgba(23, 32, 28, 0.06);
  font-size: 14px;
  font-weight: 700;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease,
    transform 150ms ease;

  &:hover {
    border-color: #ced8d1;
    box-shadow: 0 5px 14px rgba(23, 32, 28, 0.1);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
`;

const GoogleMark = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  color: #4285f4;
  font-size: 18px;
  font-weight: 800;
  font-family: Arial, sans-serif;
`;

const ButtonLabel = styled.span`
  min-width: 0;
  text-align: center;
`;
