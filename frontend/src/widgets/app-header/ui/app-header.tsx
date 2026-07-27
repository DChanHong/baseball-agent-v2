"use client";

import { useSetAtom } from "jotai";
import styled from "styled-components";
import { isLoginModalOpenAtom } from "@/features/auth/model/auth-modal.atom";
import { isProfileModalOpenAtom } from "@/features/profile/model/profile-modal.atom";
import { Button } from "@/shared/ui/button";

export function AppHeader() {
  const openLoginModal = useSetAtom(isLoginModalOpenAtom);
  const openProfileModal = useSetAtom(isProfileModalOpenAtom);

  return (
    <Header>
      <Brand>
        <Mark aria-hidden="true">B</Mark>
        <BrandText>
          <Title>Baseball Agent</Title>
          <Subtitle>KBO 직관 의사결정 도우미</Subtitle>
        </BrandText>
      </Brand>
      <Actions>
        <Button type="button" variant="secondary" onClick={() => openProfileModal(true)}>
          프로필
        </Button>
        <Button type="button" variant="primary" onClick={() => openLoginModal(true)}>
          로그인
        </Button>
      </Actions>
    </Header>
  );
}

const Header = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  padding: 14px 20px;
  background: ${({ theme }) => theme.color.panel};

  @media (max-width: 560px) {
    align-items: flex-start;
    flex-direction: column;
  }
`;

const Brand = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

const Mark = styled.span`
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.primary};
  color: #ffffff;
  font-weight: 900;
`;

const BrandText = styled.div`
  display: grid;
  gap: 2px;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 18px;
`;

const Subtitle = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
`;

const Actions = styled.div`
  display: flex;
  gap: 8px;
`;
