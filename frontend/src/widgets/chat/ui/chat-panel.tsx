"use client";

import { useSetAtom } from "jotai";
import { Sparkles } from "lucide-react";
import styled from "styled-components";
import { ChatComposer } from "@/features/send-message/ui/chat-composer";
import { Button } from "@/shared/ui/button";
import { isSourceDrawerOpenAtom } from "@/widgets/source-drawer/model/source-drawer.atom";

export function ChatPanel() {
  const openSourceDrawer = useSetAtom(isSourceDrawerOpenAtom);

  return (
    <Panel>
      <Hero>
        <LogoWrap aria-hidden="true">
          <LogoRing />
          <LogoCore>B</LogoCore>
        </LogoWrap>
        <Copy>
          <Eyebrow>
            <Sparkles size={15} />
            KBO Agent
          </Eyebrow>
          <Heading>오늘의 직관 판단을 한 번에 끝내세요</Heading>
          <Description>
            경기 일정, 구장 정보, 날씨, 좌석 추천, 예매 가이드를 출처와 기준 시점까지 함께
            확인합니다.
          </Description>
        </Copy>
        <ChatComposer />
        <FooterActions>
          <Button type="button" variant="ghost" onClick={() => openSourceDrawer(true)}>
            출처 패널 열기
          </Button>
        </FooterActions>
      </Hero>
    </Panel>
  );
}

const Panel = styled.main`
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: calc(100vh - 72px);
  padding: 48px 20px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(247, 248, 243, 0.96)),
    radial-gradient(circle at 50% 18%, rgba(217, 70, 53, 0.1), transparent 34%),
    ${({ theme }) => theme.color.background};
`;

const Hero = styled.section`
  display: grid;
  justify-items: center;
  gap: 24px;
  width: min(100%, 820px);
`;

const LogoWrap = styled.div`
  position: relative;
  display: grid;
  width: 82px;
  height: 82px;
  place-items: center;
`;

const LogoRing = styled.div`
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(from 120deg, #136f4a, #f7c948, #d94635, #136f4a), #ffffff;
  animation: logo-spin 9s linear infinite;

  &::after {
    position: absolute;
    inset: 15px;
    border-radius: 50%;
    background: ${({ theme }) => theme.color.background};
    content: "";
  }

  @keyframes logo-spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const LogoCore = styled.div`
  position: relative;
  z-index: 1;
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  background: #ffffff;
  color: ${({ theme }) => theme.color.primary};
  font-size: 24px;
  font-weight: 950;
  box-shadow: 0 10px 30px rgba(19, 111, 74, 0.12);
`;

const Copy = styled.div`
  display: grid;
  justify-items: center;
  gap: 10px;
  text-align: center;
`;

const Eyebrow = styled.p`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  color: ${({ theme }) => theme.color.primary};
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
`;

const Heading = styled.h1`
  margin: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: clamp(30px, 4vw, 44px);
  line-height: 1.14;
  word-break: keep-all;
`;

const Description = styled.p`
  max-width: 680px;
  margin: 0;
  color: ${({ theme }) => theme.color.muted};
  font-size: 16px;
  line-height: 1.65;
  word-break: keep-all;
`;

const FooterActions = styled.div`
  display: flex;
  justify-content: center;
`;
