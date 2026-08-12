"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { useSetAtom } from "jotai";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  LogIn,
  LogOut,
  Menu,
  MessageSquare,
  PenLine,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import styled from "styled-components";
import { isLoginModalOpenAtom } from "@/features/auth/model/auth-modal.atom";
import { useCurrentUser, useLogout } from "@/features/auth/model/auth-query";
import { useConversationList } from "@/features/conversation-list/model/conversation-list-query";
import { isProfileModalOpenAtom } from "@/features/profile/model/profile-modal.atom";

function subscribeToSidebarBreakpoint(callback: () => void) {
  const mediaQuery = window.matchMedia("(max-width: 720px)");
  mediaQuery.addEventListener("change", callback);

  return () => {
    mediaQuery.removeEventListener("change", callback);
  };
}

function getSidebarBreakpointSnapshot() {
  return window.matchMedia("(max-width: 720px)").matches;
}

function getSidebarBreakpointServerSnapshot() {
  return true;
}

export function ChatSidebar() {
  const openLoginModal = useSetAtom(isLoginModalOpenAtom);
  const openProfileModal = useSetAtom(isProfileModalOpenAtom);
  const { data: user, isLoading: isCheckingAuth } = useCurrentUser();
  const logoutMutation = useLogout();
  const {
    data: conversationSummaries = [],
    isError: isConversationListError,
    isLoading: isConversationListLoading,
  } = useConversationList({ enabled: Boolean(user) });
  const isNarrowSidebar = useSyncExternalStore(
    subscribeToSidebarBreakpoint,
    getSidebarBreakpointSnapshot,
    getSidebarBreakpointServerSnapshot,
  );
  const [userCollapsedState, setUserCollapsedState] = useState<boolean | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isAccountPanelOpen, setIsAccountPanelOpen] = useState(false);
  const sessionListRef = useRef<HTMLUListElement>(null);
  const accountRef = useRef<HTMLDivElement>(null);
  const isCollapsed = userCollapsedState ?? isNarrowSidebar;
  const userInitial = user?.nickname.slice(0, 1) ?? "K";
  // TanStack Virtual intentionally returns imperative helpers; React Compiler cannot memoize them.
  // eslint-disable-next-line react-hooks/incompatible-library
  const sessionVirtualizer = useVirtualizer({
    count: conversationSummaries.length,
    estimateSize: () => 44,
    getScrollElement: () => sessionListRef.current,
    overscan: 6,
  });

  useEffect(() => {
    if (!isAccountPanelOpen) {
      return;
    }

    function closeOnOutsidePointer(event: PointerEvent) {
      if (!accountRef.current?.contains(event.target as Node)) {
        setIsAccountPanelOpen(false);
      }
    }

    window.addEventListener("pointerdown", closeOnOutsidePointer);

    return () => {
      window.removeEventListener("pointerdown", closeOnOutsidePointer);
    };
  }, [isAccountPanelOpen]);

  useEffect(() => {
    if (!user) {
      setActiveSessionId(null);
      return;
    }

    if (
      activeSessionId &&
      !conversationSummaries.some((conversation) => conversation.id === activeSessionId)
    ) {
      setActiveSessionId(null);
    }
  }, [activeSessionId, conversationSummaries, user]);

  function startNewChat() {
    setActiveSessionId(null);
    closeOnCompactPhone();
  }

  function selectSession(sessionId: string) {
    setActiveSessionId(sessionId);
    closeOnCompactPhone();
  }

  function closeOnCompactPhone() {
    if (window.matchMedia("(max-width: 480px)").matches) {
      setUserCollapsedState(true);
    }
  }

  function openLogin() {
    setIsAccountPanelOpen(false);
    openLoginModal(true);
    closeOnCompactPhone();
  }

  function openProfile() {
    setIsAccountPanelOpen(false);
    openProfileModal(true);
    closeOnCompactPhone();
  }

  function logout() {
    setIsAccountPanelOpen(false);
    logoutMutation.mutate();
    closeOnCompactPhone();
  }

  function openAccountFromRail() {
    setUserCollapsedState(false);
    setIsAccountPanelOpen(true);
  }

  return (
    <>
      <FloatingMenuButton
        type="button"
        $isVisible={isCollapsed}
        aria-label="채팅 목록 열기"
        title="채팅 목록 열기"
        onClick={() => setUserCollapsedState(false)}
      >
        <Menu aria-hidden="true" size={19} />
      </FloatingMenuButton>

      <CompactScrim
        type="button"
        $isVisible={!isCollapsed}
        aria-label="채팅 목록 닫기"
        onClick={() => setUserCollapsedState(true)}
      />

      <Sidebar $isCollapsed={isCollapsed} aria-label="채팅 목록">
        {isCollapsed ? (
          <Rail>
            <LogoIconButton
              type="button"
              aria-label="KBO Mate"
              title="KBO Mate"
              onClick={() => setUserCollapsedState(false)}
            >
              <LogoImage src="/brand/flaming-baseball-logo.webp" alt="" />
            </LogoIconButton>
            <IconButton type="button" aria-label="새 채팅" title="새 채팅" onClick={startNewChat}>
              <PenLine aria-hidden="true" size={18} />
            </IconButton>
            <IconButton
              type="button"
              aria-label="사이드바 펼치기"
              title="사이드바 펼치기"
              onClick={() => setUserCollapsedState(false)}
            >
              <ChevronRight aria-hidden="true" size={18} />
            </IconButton>
            <RailSpacer />
            <IconButton
              type="button"
              aria-label={user ? "계정 메뉴" : "로그인"}
              title={user ? "계정 메뉴" : "로그인"}
              disabled={isCheckingAuth}
              onClick={user ? openAccountFromRail : openLogin}
            >
              {isCheckingAuth ? (
                <LoadingIcon aria-hidden="true" size={18} />
              ) : user ? (
                <RailAvatar>{userInitial}</RailAvatar>
              ) : (
                <LogIn aria-hidden="true" size={18} />
              )}
            </IconButton>
          </Rail>
        ) : (
          <ExpandedPanel>
            <TopGroup>
              <BrandRow>
                <BrandIdentity>
                  <LogoFrame aria-hidden="true">
                    <LogoImage src="/brand/flaming-baseball-logo.webp" alt="" />
                  </LogoFrame>
                  <BrandText>
                    <BrandName>KBO Mate</BrandName>
                    <BrandCaption>야구 관람 도우미</BrandCaption>
                  </BrandText>
                </BrandIdentity>
                <HeaderActions>
                  <IconButton
                    type="button"
                    aria-label="사이드바 접기"
                    title="사이드바 접기"
                    onClick={() => setUserCollapsedState(true)}
                  >
                    <ChevronLeft aria-hidden="true" size={18} />
                  </IconButton>
                </HeaderActions>
              </BrandRow>

              <NewChatButton type="button" onClick={startNewChat}>
                <PenLine aria-hidden="true" size={18} />
                새 채팅
              </NewChatButton>
            </TopGroup>

            <ListGroup>
              <SectionLabel>채팅 목록</SectionLabel>
              {!user ? (
                <ListStateText>로그인 후 대화 목록을 볼 수 있습니다.</ListStateText>
              ) : isConversationListLoading ? (
                <ListStateText>대화 목록을 불러오는 중입니다.</ListStateText>
              ) : isConversationListError ? (
                <ListStateText>대화 목록을 불러오지 못했습니다.</ListStateText>
              ) : conversationSummaries.length === 0 ? (
                <ListStateText>아직 저장된 대화가 없습니다.</ListStateText>
              ) : (
                <SessionList ref={sessionListRef} aria-label="채팅 세션">
                  <VirtualListSpace $height={sessionVirtualizer.getTotalSize()}>
                    {sessionVirtualizer.getVirtualItems().map((virtualSession) => {
                      const conversation = conversationSummaries[virtualSession.index];

                      return (
                        <SessionItem
                          key={conversation.id}
                          $height={virtualSession.size}
                          $start={virtualSession.start}
                          ref={sessionVirtualizer.measureElement}
                          data-index={virtualSession.index}
                        >
                          <SessionButton
                            type="button"
                            $isActive={conversation.id === activeSessionId}
                            onClick={() => selectSession(conversation.id)}
                          >
                            <MessageSquare aria-hidden="true" size={16} />
                            <SessionTitle>{conversation.title ?? "새 대화"}</SessionTitle>
                          </SessionButton>
                        </SessionItem>
                      );
                    })}
                  </VirtualListSpace>
                </SessionList>
              )}
            </ListGroup>

            <AccountArea ref={accountRef}>
              {user ? (
                <>
                  <AccountButton
                    type="button"
                    aria-expanded={isAccountPanelOpen}
                    aria-haspopup="menu"
                    onClick={() => setIsAccountPanelOpen((current) => !current)}
                  >
                    <AccountAvatar>{userInitial}</AccountAvatar>
                    <AccountText>
                      <AccountName>{user.nickname}</AccountName>
                      <AccountCaption>개인</AccountCaption>
                    </AccountText>
                    <ChevronDown aria-hidden="true" size={17} />
                  </AccountButton>

                  {isAccountPanelOpen ? (
                    <AccountPanel role="menu" aria-label="계정 메뉴">
                      <AccountPanelHeader>
                        <AccountAvatar $large>{userInitial}</AccountAvatar>
                        <AccountText>
                          <AccountName>{user.nickname}</AccountName>
                          <AccountCaption>개인</AccountCaption>
                        </AccountText>
                      </AccountPanelHeader>
                      <MenuItem type="button" role="menuitem" onClick={openProfile}>
                        <UserRound aria-hidden="true" size={19} />
                        마이페이지
                      </MenuItem>
                      <MenuDivider />
                      <DangerMenuItem
                        type="button"
                        role="menuitem"
                        disabled={logoutMutation.isPending}
                        onClick={logout}
                      >
                        <LogOut aria-hidden="true" size={19} />
                        로그아웃
                      </DangerMenuItem>
                    </AccountPanel>
                  ) : null}
                </>
              ) : (
                <LoginButton type="button" disabled={isCheckingAuth} onClick={openLogin}>
                  {isCheckingAuth ? (
                    <LoadingIcon aria-hidden="true" size={18} />
                  ) : (
                    <LogIn aria-hidden="true" size={18} />
                  )}
                  {isCheckingAuth ? "확인 중" : "로그인"}
                </LoginButton>
              )}
            </AccountArea>
          </ExpandedPanel>
        )}
      </Sidebar>
    </>
  );
}

const FloatingMenuButton = styled.button<{ $isVisible: boolean }>`
  position: fixed;
  top: 14px;
  left: 12px;
  z-index: 20;
  display: none;
  width: 42px;
  height: 42px;
  place-items: center;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: rgba(255, 255, 255, 0.96);
  color: ${({ theme }) => theme.color.foreground};
  box-shadow: 0 12px 28px rgba(18, 32, 25, 0.12);

  @media (max-width: 480px) {
    display: ${({ $isVisible }) => ($isVisible ? "grid" : "none")};
  }
`;

const CompactScrim = styled.button<{ $isVisible: boolean }>`
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 21;
  display: none;
  border: 0;
  padding: 0;
  background: rgba(18, 32, 25, 0.18);

  @media (max-width: 480px) {
    display: ${({ $isVisible }) => ($isVisible ? "block" : "none")};
  }
`;

const Sidebar = styled.aside<{ $isCollapsed: boolean }>`
  position: sticky;
  top: 0;
  z-index: 12;
  display: block;
  width: ${({ $isCollapsed }) => ($isCollapsed ? "58px" : "300px")};
  height: 100vh;
  border-right: 1px solid ${({ theme }) => theme.color.border};
  background: rgba(247, 247, 245, 0.96);
  backdrop-filter: blur(14px);
  transition:
    grid-template-columns 180ms ease,
    width 180ms ease;

  @media (max-width: 720px) {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    height: 100vh;
    box-shadow: ${({ $isCollapsed, theme }) => ($isCollapsed ? "none" : theme.shadow.panel)};
  }

  @media (max-width: 480px) {
    z-index: 22;
    width: ${({ $isCollapsed }) => ($isCollapsed ? "58px" : "min(300px, calc(100vw - 28px))")};
    border-right: ${({ $isCollapsed, theme }) =>
      $isCollapsed ? "0" : `1px solid ${theme.color.border}`};
    transform: translateX(${({ $isCollapsed }) => ($isCollapsed ? "-100%" : "0")});
    transition:
      box-shadow 180ms ease,
      transform 200ms ease;
    pointer-events: ${({ $isCollapsed }) => ($isCollapsed ? "none" : "auto")};
  }
`;

const Rail = styled.div`
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 8px 12px;
`;

const IconButton = styled.button`
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid transparent;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: transparent;
  color: ${({ theme }) => theme.color.muted};
  transition:
    background 160ms ease,
    border-color 160ms ease,
    color 160ms ease;

  &:disabled {
    cursor: wait;
    opacity: 0.58;
  }

  &:hover {
    border-color: rgba(19, 111, 74, 0.18);
    background: rgba(255, 255, 255, 0.86);
    color: ${({ theme }) => theme.color.foreground};
  }
`;

const LogoIconButton = styled(IconButton)`
  margin-bottom: 12px;
  padding: 4px;
  background: transparent;
`;

const LogoImage = styled.img`
  width: 100%;
  height: 100%;
  object-fit: contain;
`;

const RailSpacer = styled.div`
  flex: 1 1 auto;
`;

const RailAvatar = styled.span`
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: #f5c21b;
  color: #ffffff;
  font-size: 14px;
  font-weight: 900;
`;

const ExpandedPanel = styled.div`
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 16px;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 16px 16px 14px 14px;
`;

const TopGroup = styled.div`
  display: grid;
  gap: 20px;
`;

const BrandRow = styled.div`
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
`;

const BrandIdentity = styled.div`
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
`;

const LogoFrame = styled.div`
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  flex: 0 0 auto;
`;

const BrandText = styled.div`
  display: grid;
  min-width: 0;
  gap: 2px;
`;

const BrandName = styled.h1`
  margin: 0;
  overflow: hidden;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 22px;
  font-weight: 900;
  line-height: 1.05;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const BrandCaption = styled.p`
  margin: 0;
  overflow: hidden;
  color: ${({ theme }) => theme.color.muted};
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const HeaderActions = styled.div`
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
`;

const NewChatButton = styled.button`
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 9px;
  background: transparent;
  color: ${({ theme }) => theme.color.foreground};
  font-weight: 850;
  transition:
    background 160ms ease,
    color 160ms ease;

  svg {
    flex: 0 0 auto;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.82);
  }
`;

const ListGroup = styled.div`
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  gap: 8px;
`;

const SectionLabel = styled.h2`
  margin: 0;
  padding: 0 8px;
  color: #8a8f8b;
  font-size: 13px;
  font-weight: 850;
  line-height: 1.4;
`;

const SessionList = styled.ul`
  position: relative;
  min-height: 0;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  scrollbar-color: rgba(23, 32, 28, 0.22) transparent;
  scrollbar-width: thin;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(23, 32, 28, 0.2);
  }

  &::-webkit-scrollbar-thumb:hover {
    background: rgba(23, 32, 28, 0.32);
  }
`;

const ListStateText = styled.p`
  margin: 6px 8px 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
  font-weight: 700;
  line-height: 1.5;
`;

const VirtualListSpace = styled.div<{ $height: number }>`
  position: relative;
  height: ${({ $height }) => $height}px;
`;

const SessionItem = styled.li<{ $height: number; $start: number }>`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: ${({ $height }) => $height}px;
  min-width: 0;
  padding-bottom: 4px;
  transform: translateY(${({ $start }) => $start}px);
`;

const SessionButton = styled.button<{ $isActive: boolean }>`
  display: flex;
  width: 100%;
  min-height: 40px;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 10px;
  background: ${({ $isActive }) => ($isActive ? "rgba(255, 255, 255, 0.94)" : "transparent")};
  color: ${({ theme }) => theme.color.foreground};
  font-weight: ${({ $isActive }) => ($isActive ? 850 : 720)};
  text-align: left;
  transition:
    background 160ms ease,
    color 160ms ease;

  svg {
    flex: 0 0 auto;
    color: ${({ $isActive, theme }) => ($isActive ? theme.color.primary : theme.color.muted)};
  }

  &:hover {
    background: rgba(255, 255, 255, 0.88);
  }
`;

const SessionTitle = styled.span`
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const AccountArea = styled.div`
  position: relative;
  min-width: 0;
  padding-top: 12px;
  border-top: 1px solid rgba(217, 225, 220, 0.86);
`;

const LoginButton = styled.button`
  display: inline-flex;
  width: 100%;
  min-height: 46px;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 0 12px;
  background: ${({ theme }) => theme.color.panel};
  color: ${({ theme }) => theme.color.foreground};
  font-weight: 850;
  transition:
    background 160ms ease,
    border-color 160ms ease;

  &:hover {
    border-color: rgba(19, 111, 74, 0.24);
    background: rgba(255, 255, 255, 0.96);
  }

  &:disabled {
    cursor: wait;
    opacity: 0.7;
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

const AccountButton = styled.button`
  display: grid;
  width: 100%;
  min-height: 50px;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 6px 8px;
  background: transparent;
  color: ${({ theme }) => theme.color.foreground};
  text-align: left;
  transition:
    background 160ms ease,
    border-color 160ms ease;

  &:hover,
  &[aria-expanded="true"] {
    border-color: rgba(217, 225, 220, 0.88);
    background: rgba(255, 255, 255, 0.9);
  }
`;

const AccountAvatar = styled.span<{ $large?: boolean }>`
  display: grid;
  width: ${({ $large }) => ($large ? "56px" : "38px")};
  height: ${({ $large }) => ($large ? "56px" : "38px")};
  place-items: center;
  border-radius: 999px;
  background: #f5c21b;
  color: #ffffff;
  font-size: ${({ $large }) => ($large ? "20px" : "15px")};
  font-weight: 900;
`;

const AccountText = styled.span`
  display: grid;
  min-width: 0;
  gap: 2px;
`;

const AccountName = styled.span`
  overflow: hidden;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 15px;
  font-weight: 900;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const AccountCaption = styled.span`
  overflow: hidden;
  color: ${({ theme }) => theme.color.muted};
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const AccountPanel = styled.div`
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  z-index: 28;
  display: grid;
  width: min(272px, calc(100vw - 36px));
  gap: 8px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 10px;
  background: ${({ theme }) => theme.color.panel};
  box-shadow: 0 20px 58px rgba(18, 32, 25, 0.16);
`;

const AccountPanelHeader = styled.div`
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding: 8px 8px 12px;
`;

const MenuItem = styled.button`
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: 12px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 10px;
  background: transparent;
  color: ${({ theme }) => theme.color.foreground};
  font-weight: 800;
  text-align: left;

  &:hover {
    background: ${({ theme }) => theme.color.panelAlt};
  }

  &:disabled {
    cursor: wait;
    opacity: 0.58;
  }
`;

const DangerMenuItem = styled(MenuItem)`
  color: #ff4a4f;
`;

const MenuDivider = styled.div`
  height: 1px;
  margin: 2px 0;
  background: ${({ theme }) => theme.color.border};
`;
