"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { ChevronLeft, ChevronRight, Menu, MessageSquare, PenLine } from "lucide-react";
import { useRef, useState, useSyncExternalStore } from "react";
import styled from "styled-components";

type MockChatSession = {
  id: string;
  title: string;
};

const mockChatSessions: MockChatSession[] = [
  {
    id: "session-1",
    title: "잠실 주말 경기 예매와 좌석 추천",
  },
  {
    id: "session-2",
    title: "사직 원정 동선과 비 예보 확인",
  },
  {
    id: "session-3",
    title: "고척돔 첫 직관 준비물 정리",
  },
  {
    id: "session-4",
    title: "대전 한화생명볼파크 먹거리와 주차",
  },
  {
    id: "session-5",
    title: "문학 야간 경기 날씨와 외야석 비교",
  },
  {
    id: "session-6",
    title: "창원NC파크 가족석과 테이블석 비교",
  },
  {
    id: "session-7",
    title: "수원 케이티위즈파크 퇴근길 직관",
  },
  {
    id: "session-8",
    title: "광주 챔피언스필드 응원석 분위기",
  },
  {
    id: "session-9",
    title: "대구 삼성라이온즈파크 원정 응원",
  },
  {
    id: "session-10",
    title: "잠실 더블헤더 일정과 좌석 선택",
  },
  {
    id: "session-11",
    title: "고척돔 키움전 예매 오픈 시간",
  },
  {
    id: "session-12",
    title: "사직구장 비 예보와 우천 취소 가능성",
  },
  {
    id: "session-13",
    title: "문학 홈런커플존 시야 확인",
  },
  {
    id: "session-14",
    title: "대전 신구장 첫 방문 체크리스트",
  },
  {
    id: "session-15",
    title: "잠실 3루 네이비석과 레드석 비교",
  },
  {
    id: "session-16",
    title: "수원 외야 자유석 준비물",
  },
  {
    id: "session-17",
    title: "창원 야간 경기 숙소 동선",
  },
  {
    id: "session-18",
    title: "대구 원정 버스와 주차장 비교",
  },
  {
    id: "session-19",
    title: "광주 주말 낮 경기 더위 대비",
  },
  {
    id: "session-20",
    title: "잠실 어린이 동반 좌석 추천",
  },
  {
    id: "session-21",
    title: "고척돔 응원단상 가까운 구역",
  },
  {
    id: "session-22",
    title: "사직 내야필드석 시야와 가격",
  },
  {
    id: "session-23",
    title: "문학 푸드코트와 입장 시간",
  },
  {
    id: "session-24",
    title: "대전 불꽃놀이 이벤트 경기",
  },
  {
    id: "session-25",
    title: "수원 1루 응원석 예매 전략",
  },
  {
    id: "session-26",
    title: "창원 테이블석 예매 난이도",
  },
  {
    id: "session-27",
    title: "대구 3루 원정석과 응원 동선",
  },
  {
    id: "session-28",
    title: "광주 챔필 주차와 셔틀 정보",
  },
  {
    id: "session-29",
    title: "잠실 평일 경기 퇴근 후 입장",
  },
  {
    id: "session-30",
    title: "고척돔 비 오는 날 관람 준비",
  },
  {
    id: "session-31",
    title: "사직 롯데 응원석 처음 가는 날",
  },
  {
    id: "session-32",
    title: "문학 스카이탁자석 시야",
  },
  {
    id: "session-33",
    title: "대전 중앙탁자석과 내야지정석",
  },
  {
    id: "session-34",
    title: "수원 먹거리 추천과 반입 규정",
  },
  {
    id: "session-35",
    title: "창원 원정팬 좌석 위치",
  },
  {
    id: "session-36",
    title: "대구 여름 야구장 복장",
  },
  {
    id: "session-37",
    title: "광주 KIA 홈경기 예매 팁",
  },
  {
    id: "session-38",
    title: "잠실 외야석 햇빛 방향 확인",
  },
  {
    id: "session-39",
    title: "고척돔 4층 지정석 시야",
  },
  {
    id: "session-40",
    title: "사직 주말 매진 경기 대안 좌석",
  },
  {
    id: "session-41",
    title: "문학 원정팬 입장 게이트",
  },
  {
    id: "session-42",
    title: "대전 낮 경기 그늘 좌석",
  },
  {
    id: "session-43",
    title: "수원 응원석 소음과 아이 동반",
  },
  {
    id: "session-44",
    title: "창원NC파크 주변 맛집 동선",
  },
  {
    id: "session-45",
    title: "대구 지하철 이동과 막차 시간",
  },
  {
    id: "session-46",
    title: "광주 원정 숙소 위치 추천",
  },
  {
    id: "session-47",
    title: "잠실 포스트시즌 예매 준비",
  },
  {
    id: "session-48",
    title: "고척돔 키움 홈경기 좌석별 분위기",
  },
  {
    id: "session-49",
    title: "사직 우천 취소 환불 기준",
  },
  {
    id: "session-50",
    title: "문학 야구장 첫 방문 전체 플랜",
  },
];

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
  const isNarrowSidebar = useSyncExternalStore(
    subscribeToSidebarBreakpoint,
    getSidebarBreakpointSnapshot,
    getSidebarBreakpointServerSnapshot,
  );
  const [userCollapsedState, setUserCollapsedState] = useState<boolean | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    mockChatSessions[0]?.id ?? null,
  );
  const sessionListRef = useRef<HTMLUListElement>(null);
  const isCollapsed = userCollapsedState ?? isNarrowSidebar;
  // TanStack Virtual intentionally returns imperative helpers; React Compiler cannot memoize them.
  // eslint-disable-next-line react-hooks/incompatible-library
  const sessionVirtualizer = useVirtualizer({
    count: mockChatSessions.length,
    estimateSize: () => 44,
    getScrollElement: () => sessionListRef.current,
    overscan: 6,
  });

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
        <Rail $isCollapsed={isCollapsed}>
          <IconButton type="button" aria-label="새 채팅" title="새 채팅" onClick={startNewChat}>
            <PenLine aria-hidden="true" size={18} />
          </IconButton>
          <IconButton
            type="button"
            aria-label={isCollapsed ? "사이드바 펼치기" : "사이드바 접기"}
            title={isCollapsed ? "사이드바 펼치기" : "사이드바 접기"}
            onClick={() => setUserCollapsedState(!isCollapsed)}
          >
            {isCollapsed ? (
              <ChevronRight aria-hidden="true" size={18} />
            ) : (
              <ChevronLeft aria-hidden="true" size={18} />
            )}
          </IconButton>
        </Rail>

        {!isCollapsed ? (
          <ExpandedPanel>
            <NewChatButton type="button" onClick={startNewChat}>
              <PenLine aria-hidden="true" size={18} />
              새 채팅
            </NewChatButton>

            <SessionList ref={sessionListRef} aria-label="채팅 세션">
              <VirtualListSpace $height={sessionVirtualizer.getTotalSize()}>
                {sessionVirtualizer.getVirtualItems().map((virtualSession) => {
                  const session = mockChatSessions[virtualSession.index];

                  return (
                    <SessionItem
                      key={session.id}
                      $height={virtualSession.size}
                      $start={virtualSession.start}
                      ref={sessionVirtualizer.measureElement}
                      data-index={virtualSession.index}
                    >
                      <SessionButton
                        type="button"
                        $isActive={session.id === activeSessionId}
                        onClick={() => selectSession(session.id)}
                      >
                        <MessageSquare aria-hidden="true" size={16} />
                        <SessionTitle>{session.title}</SessionTitle>
                      </SessionButton>
                    </SessionItem>
                  );
                })}
              </VirtualListSpace>
            </SessionList>
          </ExpandedPanel>
        ) : null}
      </Sidebar>
    </>
  );
}

const FloatingMenuButton = styled.button<{ $isVisible: boolean }>`
  position: fixed;
  top: 76px;
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
  top: 64px;
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
  top: 72px;
  z-index: 12;
  display: grid;
  grid-template-columns: ${({ $isCollapsed }) => ($isCollapsed ? "56px" : "56px 224px")};
  width: ${({ $isCollapsed }) => ($isCollapsed ? "56px" : "280px")};
  height: calc(100vh - 72px);
  border-right: 1px solid ${({ theme }) => theme.color.border};
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  transition:
    grid-template-columns 180ms ease,
    width 180ms ease;

  @media (max-width: 720px) {
    position: fixed;
    top: 64px;
    bottom: 0;
    left: 0;
    height: calc(100vh - 64px);
    box-shadow: ${({ $isCollapsed, theme }) => ($isCollapsed ? "none" : theme.shadow.panel)};
  }

  @media (max-width: 480px) {
    z-index: 22;
    grid-template-columns: 56px minmax(0, 224px);
    width: min(280px, calc(100vw - 28px));
    border-right: ${({ $isCollapsed, theme }) =>
      $isCollapsed ? "0" : `1px solid ${theme.color.border}`};
    transform: translateX(${({ $isCollapsed }) => ($isCollapsed ? "-100%" : "0")});
    transition:
      box-shadow 180ms ease,
      transform 200ms ease;
    pointer-events: ${({ $isCollapsed }) => ($isCollapsed ? "none" : "auto")};
  }
`;

const Rail = styled.div<{ $isCollapsed: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border-right: ${({ $isCollapsed, theme }) =>
    $isCollapsed ? "0" : `1px solid ${theme.color.border}`};
  padding: 14px 8px;
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

  &:hover {
    border-color: rgba(19, 111, 74, 0.18);
    background: ${({ theme }) => theme.color.panelAlt};
    color: ${({ theme }) => theme.color.primary};
  }
`;

const ExpandedPanel = styled.div`
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  height: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: 14px 12px;
`;

const NewChatButton = styled.button`
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid ${({ theme }) => theme.color.primary};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 12px;
  background: ${({ theme }) => theme.color.primary};
  color: #ffffff;
  font-weight: 850;
  transition:
    background 160ms ease,
    border-color 160ms ease;

  &:hover {
    border-color: ${({ theme }) => theme.color.primaryHover};
    background: ${({ theme }) => theme.color.primaryHover};
  }
`;

const SessionList = styled.ul`
  position: relative;
  min-height: 0;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
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
  gap: 8px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 10px;
  background: ${({ $isActive }) => ($isActive ? "rgba(19, 111, 74, 0.1)" : "transparent")};
  color: ${({ theme }) => theme.color.foreground};
  font-weight: ${({ $isActive }) => ($isActive ? 850 : 650)};
  text-align: left;
  transition:
    background 160ms ease,
    color 160ms ease;

  svg {
    flex: 0 0 auto;
    color: ${({ $isActive, theme }) => ($isActive ? theme.color.primary : theme.color.muted)};
  }

  &:hover {
    background: ${({ $isActive, theme }) =>
      $isActive ? "rgba(19, 111, 74, 0.13)" : theme.color.panelAlt};
  }
`;

const SessionTitle = styled.span`
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;
