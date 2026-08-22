"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import styled from "styled-components";

type SourceDisclosureProps = {
  sources: string[];
};

export function SourceDisclosure({ sources }: SourceDisclosureProps) {
  const [isOpen, setIsOpen] = useState(false);
  const panelId = useId();

  if (sources.length === 0) {
    return null;
  }

  return (
    <Wrap>
      <Toggle
        type="button"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => setIsOpen((current) => !current)}
      >
        출처 {sources.length}개
        <Chevron $isOpen={isOpen} size={13} aria-hidden="true" />
      </Toggle>
      <Panel id={panelId} $isOpen={isOpen} aria-hidden={!isOpen}>
        <SourceList>
          {sources.map((source, index) => (
            <SourceItem key={`${source}-${index}`}>
              <SourceLink href={source} target="_blank" rel="noreferrer" title={source}>
                {sourceLabel(source)}
              </SourceLink>
            </SourceItem>
          ))}
        </SourceList>
      </Panel>
    </Wrap>
  );
}

function sourceLabel(source: string): string {
  try {
    const url = new URL(source);
    return koreanSourceLabel(url);
  } catch {
    return source;
  }
}

function koreanSourceLabel(url: URL): string {
  const host = url.hostname.replace(/^www\./, "");
  const path = url.pathname.toLowerCase();
  const full = `${host}${path}`;

  if (host.includes("koreabaseball.com")) {
    if (path.includes("/ebook/")) {
      return "KBO 공식 야구 규칙 자료";
    }

    if (path.includes("/league/map")) {
      return "KBO 리그 구장·티켓 안내";
    }

    return "KBO 공식 안내";
  }

  if (host.includes("lgtwins.com")) {
    if (path.includes("/ticket")) {
      return "LG 트윈스 공식 티켓 안내";
    }

    return "LG 트윈스 공식 안내";
  }

  if (host.includes("nol.yanolja.com")) {
    if (full.includes("bears")) {
      return "NOL 스포츠 두산 베어스 예매";
    }

    return "NOL 스포츠 예매 안내";
  }

  if (host.includes("ticketlink.co.kr")) {
    return "티켓링크 예매 안내";
  }

  if (host.includes("lottegiants.co.kr")) {
    if (path.includes("/ticket")) {
      return "롯데 자이언츠 공식 티켓 안내";
    }

    if (path.includes("/sajik")) {
      return "롯데 자이언츠 사직야구장 안내";
    }

    return "롯데 자이언츠 공식 안내";
  }

  if (host.includes("heroesbaseball.co.kr")) {
    return "키움 히어로즈 공식 안내";
  }

  if (host.includes("ssglanders.com")) {
    return "SSG 랜더스 공식 안내";
  }

  if (host.includes("tigers.co.kr")) {
    return "KIA 타이거즈 공식 안내";
  }

  if (host.includes("samsunglions.com")) {
    return "삼성 라이온즈 공식 안내";
  }

  if (host.includes("ktwiz.co.kr")) {
    if (path.includes("/ticket")) {
      return "kt wiz 공식 티켓 안내";
    }

    if (path.includes("/wizpark")) {
      return "kt wiz park 공식 안내";
    }

    return "kt wiz 공식 안내";
  }

  if (host.includes("hanwhaeagles.co.kr")) {
    return "한화 이글스 공식 안내";
  }

  if (host.includes("ncdinos.com")) {
    return "NC 다이노스 공식 안내";
  }

  if (host.includes("seoul.go.kr")) {
    if (full.includes("stadium") || full.includes("sports")) {
      return "서울시 체육시설 안내";
    }

    return "서울시 공식 안내";
  }

  if (host.includes("sisul.or.kr")) {
    return "서울시설공단 공식 안내";
  }

  if (host.includes("gocheokstadium")) {
    return "고척스카이돔 공식 안내";
  }

  if (host.includes("kto.visitkorea.or.kr") || host.includes("visitkorea.or.kr")) {
    return "한국관광공사 관광 정보";
  }

  return host;
}

const Wrap = styled.div`
  display: grid;
  gap: 0;
  max-width: 100%;
`;

const Toggle = styled.button`
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: 1px solid #e6e6e6;
  border-radius: 999px;
  padding: 3px 8px;
  background: #fafafa;
  color: #666666;
  font: inherit;
  font-size: 11px;
  font-weight: 650;
  line-height: 1.3;

  &:hover {
    border-color: #d4d4d4;
    background: #f5f5f5;
    color: ${({ theme }) => theme.color.foreground};
  }
`;

const Chevron = styled(ChevronDown)<{ $isOpen: boolean }>`
  flex: 0 0 auto;
  transition: transform 160ms ease;
  transform: rotate(${({ $isOpen }) => ($isOpen ? "180deg" : "0deg")});
`;

const Panel = styled.div<{ $isOpen: boolean }>`
  display: grid;
  grid-template-rows: ${({ $isOpen }) => ($isOpen ? "1fr" : "0fr")};
  opacity: ${({ $isOpen }) => ($isOpen ? 1 : 0)};
  overflow: hidden;
  pointer-events: ${({ $isOpen }) => ($isOpen ? "auto" : "none")};
  transition:
    grid-template-rows 180ms ease,
    opacity 140ms ease;
`;

const SourceList = styled.ul`
  display: grid;
  gap: 5px;
  min-height: 0;
  margin: 7px 0 0;
  padding: 0;
  list-style: none;
`;

const SourceItem = styled.li`
  min-width: 0;
`;

const SourceLink = styled.a`
  display: block;
  max-width: 100%;
  overflow: hidden;
  border: 1px solid #e6e6e6;
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 6px 8px;
  background: #ffffff;
  color: #666666;
  font-size: 12px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;

  &:hover {
    border-color: #d0d0d0;
    color: ${({ theme }) => theme.color.foreground};
    text-decoration: underline;
  }
`;
