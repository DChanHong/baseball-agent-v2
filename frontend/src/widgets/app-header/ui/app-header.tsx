"use client";

import { useEffect, useRef, useState } from "react";
import { useSetAtom } from "jotai";
import { ChevronDown, LoaderCircle, LogIn, LogOut, UserRound } from "lucide-react";
import styled from "styled-components";
import { isLoginModalOpenAtom } from "@/features/auth/model/auth-modal.atom";
import { useCurrentUser, useLogout } from "@/features/auth/model/auth-query";
import { isProfileModalOpenAtom } from "@/features/profile/model/profile-modal.atom";

export function AppHeader() {
  const openLoginModal = useSetAtom(isLoginModalOpenAtom);
  const openProfileModal = useSetAtom(isProfileModalOpenAtom);
  const { data: user, isLoading } = useCurrentUser();
  const logoutMutation = useLogout();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isMenuOpen) {
      return;
    }

    function closeOnOutsidePointer(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }

    window.addEventListener("pointerdown", closeOnOutsidePointer);

    return () => {
      window.removeEventListener("pointerdown", closeOnOutsidePointer);
    };
  }, [isMenuOpen]);

  function openProfile() {
    setIsMenuOpen(false);
    openProfileModal(true);
  }

  function logout() {
    setIsMenuOpen(false);
    logoutMutation.mutate();
  }

  return (
    <Header>
      <Brand>
        <LogoFrame aria-hidden="true">
          <LogoImage src="/brand/flaming-baseball-logo.webp" alt="" />
        </LogoFrame>
        <BrandText>
          <Title>KBO Mate</Title>
          <Subtitle>일정부터 예매까지, KBO 관람 도우미</Subtitle>
        </BrandText>
      </Brand>

      {user ? (
        <AccountMenu ref={menuRef}>
          <AccountButton
            type="button"
            aria-expanded={isMenuOpen}
            aria-haspopup="menu"
            onClick={() => setIsMenuOpen((current) => !current)}
          >
            <UserName>{user.nickname}</UserName>
            <Avatar>{user.nickname.slice(0, 1)}</Avatar>
            <ChevronDown aria-hidden="true" size={16} strokeWidth={2.4} />
          </AccountButton>

          {isMenuOpen ? (
            <Dropdown role="menu" aria-label="프로필 메뉴">
              <MenuItem type="button" role="menuitem" onClick={openProfile}>
                <UserRound aria-hidden="true" size={17} />
                마이페이지
              </MenuItem>
              <MenuItem
                type="button"
                role="menuitem"
                onClick={logout}
                disabled={logoutMutation.isPending}
              >
                <LogOut aria-hidden="true" size={17} />
                로그아웃
              </MenuItem>
            </Dropdown>
          ) : null}
        </AccountMenu>
      ) : (
        <LoginButton
          type="button"
          aria-label={isLoading ? "로그인 상태 확인 중" : "로그인"}
          disabled={isLoading}
          onClick={() => openLoginModal(true)}
        >
          {isLoading ? (
            <LoadingIcon aria-hidden="true" size={17} />
          ) : (
            <LogIn aria-hidden="true" size={17} />
          )}
          <LoginLabel>{isLoading ? "확인 중" : "로그인"}</LoginLabel>
        </LoginButton>
      )}
    </Header>
  );
}

const Header = styled.header`
  position: fixed;
  top: 0;
  right: 0;
  left: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 72px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(14px);

  @media (max-width: 720px) {
    gap: 12px;
    min-height: 64px;
    padding: 0 14px;
  }
`;

const Brand = styled.div`
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
`;

const LogoFrame = styled.div`
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: ${({ theme }) => theme.radius.sm};
  background:
    radial-gradient(circle at 58% 36%, rgba(255, 226, 168, 0.7), transparent 54%),
    rgba(255, 248, 239, 0.92);
  flex: 0 0 auto;

  @media (max-width: 720px) {
    width: 40px;
    height: 40px;
  }
`;

const LogoImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: contain;
`;

const BrandText = styled.div`
  min-width: 0;
  display: grid;
  gap: 2px;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 18px;
  line-height: 1.15;
  white-space: nowrap;

  @media (max-width: 420px) {
    font-size: 16px;
  }
`;

const Subtitle = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  @media (max-width: 560px) {
    display: none;
  }
`;

const LoginButton = styled.button`
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid ${({ theme }) => theme.color.primary};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 15px;
  background: ${({ theme }) => theme.color.primary};
  color: #ffffff;
  font-weight: 800;
  white-space: nowrap;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;

  &:hover {
    border-color: ${({ theme }) => theme.color.primaryHover};
    background: ${({ theme }) => theme.color.primaryHover};
  }

  &:active {
    transform: translateY(1px);
  }

  &:disabled {
    cursor: wait;
    opacity: 0.7;
  }

  @media (max-width: 420px) {
    width: 40px;
    padding: 0;
  }
`;

const LoadingIcon = styled(LoaderCircle)`
  animation: spin 900ms linear infinite;

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const LoginLabel = styled.span`
  @media (max-width: 420px) {
    display: none;
  }
`;

const AccountMenu = styled.div`
  position: relative;
  flex: 0 0 auto;
`;

const AccountButton = styled.button`
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 8px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 999px;
  padding: 4px 8px 4px 14px;
  background: ${({ theme }) => theme.color.panel};
  color: ${({ theme }) => theme.color.foreground};
  font-weight: 800;
  transition:
    background 160ms ease,
    border-color 160ms ease;

  &:hover,
  &[aria-expanded="true"] {
    border-color: rgba(19, 111, 74, 0.34);
    background: ${({ theme }) => theme.color.panelAlt};
  }
`;

const UserName = styled.span`
  max-width: 132px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  @media (max-width: 560px) {
    display: none;
  }
`;

const Avatar = styled.span`
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.primary};
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
`;

const Dropdown = styled.div`
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  display: grid;
  min-width: 164px;
  gap: 4px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 6px;
  background: ${({ theme }) => theme.color.panel};
  box-shadow: ${({ theme }) => theme.shadow.panel};
`;

const MenuItem = styled.button`
  display: flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 10px;
  background: transparent;
  color: ${({ theme }) => theme.color.foreground};
  font-weight: 700;
  text-align: left;

  &:hover {
    background: ${({ theme }) => theme.color.panelAlt};
  }

  &:disabled {
    cursor: wait;
    opacity: 0.58;
  }
`;
