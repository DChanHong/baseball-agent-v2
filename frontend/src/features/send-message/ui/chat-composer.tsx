"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useAtom } from "jotai";
import {
  ArrowUp,
  Armchair,
  BrainCircuit,
  CloudSun,
  FileText,
  MapPinned,
  Mic,
  Plus,
  Search,
  Sparkles,
  Ticket,
  X,
} from "lucide-react";
import { useRef, useState, type ReactNode } from "react";
import styled, { css } from "styled-components";
import { chatInputAtom } from "@/features/send-message/model/chat-input.atom";

type SuggestionCategory = "seat" | "ticket" | "weather";

type ChatComposerProps = {
  disabled?: boolean;
  onSendMessage?: (message: string) => void;
};

const commandSuggestions: Record<SuggestionCategory, string[]> = {
  seat: [
    "잠실에서 LG 응원하기 좋은 좌석 추천해줘",
    "사직구장 처음 가는데 시야 좋은 좌석 비교해줘",
    "비 오는 날 고척돔 말고 야외 구장은 어디 앉는 게 좋아?",
  ],
  ticket: [
    "이번 주말 롯데 홈경기 예매 방법 알려줘",
    "두산 원정석 예매할 때 공식 링크와 주의사항 알려줘",
    "KBO 경기 예매 오픈 전에 준비할 체크리스트 만들어줘",
  ],
  weather: [
    "내일 문학구장 날씨 기준으로 준비물 알려줘",
    "대구 원정 가는데 더위 피할 좌석과 이동 팁 알려줘",
    "비 예보가 있을 때 취소 가능성과 좌석 선택 기준 알려줘",
  ],
};

const categoryMeta: Record<
  SuggestionCategory,
  {
    icon: ReactNode;
    label: string;
    title: string;
  }
> = {
  seat: {
    icon: <Armchair size={20} />,
    label: "좌석 추천",
    title: "좌석 추천 질문",
  },
  ticket: {
    icon: <Ticket size={20} />,
    label: "예매 안내",
    title: "예매 안내 질문",
  },
  weather: {
    icon: <CloudSun size={20} />,
    label: "날씨 판단",
    title: "날씨 기반 질문",
  },
};

export function ChatComposer({ disabled = false, onSendMessage }: ChatComposerProps) {
  const [value, setValue] = useAtom(chatInputAtom);
  const [searchEnabled, setSearchEnabled] = useState(true);
  const [deepResearchEnabled, setDeepResearchEnabled] = useState(false);
  const [reasonEnabled, setReasonEnabled] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [showUploadAnimation, setShowUploadAnimation] = useState(false);
  const [activeCategory, setActiveCategory] = useState<SuggestionCategory | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUploadFile = () => {
    setShowUploadAnimation(true);

    window.setTimeout(() => {
      setUploadedFiles((prev) => [...prev, "직관 메모.pdf"]);
      setShowUploadAnimation(false);
    }, 900);
  };

  const handleCommandSelect = (command: string) => {
    setValue(command);
    setActiveCategory(null);
    inputRef.current?.focus();
  };

  const handleSendMessage = () => {
    const trimmedValue = value.trim();

    if (!trimmedValue || disabled) {
      return;
    }

    onSendMessage?.(trimmedValue);
    setValue("");
  };

  return (
    <ComposerShell>
      <PromptCard>
        <InputArea>
          <Input
            ref={inputRef}
            type="text"
            placeholder="경기 일정, 좌석, 예매, 날씨를 한 번에 물어보세요"
            value={value}
            disabled={disabled}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                handleSendMessage();
              }
            }}
          />
        </InputArea>

        {uploadedFiles.length > 0 ? (
          <UploadedFiles>
            {uploadedFiles.map((file, index) => (
              <UploadedFile key={`${file}-${index}`}>
                <FileText size={14} />
                <span>{file}</span>
                <RemoveFileButton
                  type="button"
                  aria-label={`${file} 제거`}
                  onClick={() => setUploadedFiles((prev) => prev.filter((_, i) => i !== index))}
                >
                  <X size={12} />
                </RemoveFileButton>
              </UploadedFile>
            ))}
          </UploadedFiles>
        ) : null}

        <FunctionRow>
          <ModeGroup>
            <ModeButton
              type="button"
              $active={searchEnabled}
              onClick={() => setSearchEnabled((prev) => !prev)}
            >
              <Search size={16} />
              일정 검색
            </ModeButton>
            <ModeButton
              type="button"
              $active={deepResearchEnabled}
              onClick={() => setDeepResearchEnabled((prev) => !prev)}
            >
              <MapPinned size={16} />
              원정 조사
            </ModeButton>
            <ModeButton
              type="button"
              $active={reasonEnabled}
              onClick={() => setReasonEnabled((prev) => !prev)}
            >
              <BrainCircuit size={16} />
              추천 근거
            </ModeButton>
          </ModeGroup>
          <ActionGroup>
            <IconButton type="button" aria-label="음성 입력">
              <Mic size={20} />
            </IconButton>
            <SendButton
              type="button"
              aria-label="메시지 전송"
              disabled={!value.trim() || disabled}
              $disabled={disabled}
              onClick={handleSendMessage}
            >
              <ArrowUp size={18} />
            </SendButton>
          </ActionGroup>
        </FunctionRow>

        <UploadRow>
          <UploadButton type="button" onClick={handleUploadFile}>
            {showUploadAnimation ? (
              <Dots aria-hidden="true">
                {[0, 1, 2].map((item) => (
                  <motion.span
                    key={item}
                    initial={{ opacity: 0.25, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.42,
                      repeat: Infinity,
                      repeatType: "mirror",
                      delay: item * 0.1,
                    }}
                  />
                ))}
              </Dots>
            ) : (
              <Plus size={16} />
            )}
            직관 자료 추가
          </UploadButton>
        </UploadRow>
      </PromptCard>

      <CommandGrid>
        {(Object.keys(categoryMeta) as SuggestionCategory[]).map((category) => (
          <CommandButton
            key={category}
            type="button"
            $active={activeCategory === category}
            onClick={() => setActiveCategory((prev) => (prev === category ? null : category))}
          >
            {categoryMeta[category].icon}
            <span>{categoryMeta[category].label}</span>
          </CommandButton>
        ))}
      </CommandGrid>

      <AnimatePresence>
        {activeCategory ? (
          <SuggestionWrap
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <SuggestionPanel>
              <SuggestionTitle>
                <Sparkles size={16} />
                {categoryMeta[activeCategory].title}
              </SuggestionTitle>
              <SuggestionList>
                {commandSuggestions[activeCategory].map((suggestion, index) => (
                  <SuggestionItem
                    key={suggestion}
                    type="button"
                    as={motion.button}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: index * 0.04 }}
                    onClick={() => handleCommandSelect(suggestion)}
                  >
                    {categoryMeta[activeCategory].icon}
                    <span>{suggestion}</span>
                  </SuggestionItem>
                ))}
              </SuggestionList>
            </SuggestionPanel>
          </SuggestionWrap>
        ) : null}
      </AnimatePresence>
    </ComposerShell>
  );
}

const ComposerShell = styled.div`
  display: grid;
  gap: 16px;
  width: min(100%, 760px);
`;

const PromptCard = styled.div`
  overflow: hidden;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.panel};
  box-shadow: ${({ theme }) => theme.shadow.panel};
`;

const InputArea = styled.div`
  padding: 18px 18px 12px;
`;

const Input = styled.input`
  width: 100%;
  border: 0;
  outline: 0;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 16px;

  &::placeholder {
    color: ${({ theme }) => theme.color.muted};
  }

  &:disabled {
    cursor: wait;
  }
`;

const UploadedFiles = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 18px 12px;
`;

const UploadedFile = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 5px 8px;
  background: ${({ theme }) => theme.color.panelAlt};
  color: ${({ theme }) => theme.color.foreground};
  font-size: 12px;
`;

const RemoveFileButton = styled.button`
  display: inline-grid;
  place-items: center;
  border: 0;
  padding: 0;
  background: transparent;
  color: ${({ theme }) => theme.color.muted};
`;

const FunctionRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px 14px;

  @media (max-width: 680px) {
    align-items: stretch;
    flex-direction: column;
  }
`;

const ModeGroup = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
`;

const ModeButton = styled.button<{ $active: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 34px;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 800;
  transition:
    background 160ms ease,
    color 160ms ease,
    border-color 160ms ease;

  ${({ $active }) =>
    $active
      ? css`
          border-color: rgba(19, 111, 74, 0.2);
          background: #e9f6ef;
          color: #136f4a;
        `
      : css`
          background: #f1f2ef;
          color: #7a837c;
        `}
`;

const ActionGroup = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 8px;
`;

const IconButton = styled.button`
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: ${({ theme }) => theme.color.muted};
`;

const SendButton = styled.button<{ $disabled: boolean }>`
  display: inline-grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.primary};
  color: #ffffff;
  transition:
    background 160ms ease,
    opacity 160ms ease;

  &:disabled {
    background: #e2e5e0;
    color: #99a29b;
    cursor: ${({ $disabled }) => ($disabled ? "wait" : "not-allowed")};
  }
`;

const UploadRow = styled.div`
  border-top: 1px solid ${({ theme }) => theme.color.border};
  padding: 10px 16px;
`;

const UploadButton = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  padding: 0;
  background: transparent;
  color: ${({ theme }) => theme.color.muted};
  font-size: 13px;
  font-weight: 700;
`;

const Dots = styled.span`
  display: inline-flex;
  gap: 3px;

  span {
    width: 5px;
    height: 5px;
    border-radius: 999px;
    background: ${({ theme }) => theme.color.primary};
  }
`;

const CommandGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`;

const CommandButton = styled.button<{ $active: boolean }>`
  display: grid;
  place-items: center;
  gap: 8px;
  min-height: 92px;
  border: 1px solid ${({ theme, $active }) => ($active ? theme.color.primary : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: 14px;
  background: ${({ $active }) => ($active ? "#e9f6ef" : "#ffffff")};
  color: ${({ theme, $active }) => ($active ? theme.color.primary : theme.color.foreground)};
  font-weight: 800;
  transition:
    border-color 160ms ease,
    background 160ms ease,
    transform 160ms ease;

  &:hover {
    transform: translateY(-1px);
  }
`;

const SuggestionWrap = styled(motion.div)`
  overflow: hidden;
`;

const SuggestionPanel = styled.div`
  overflow: hidden;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.panel};
  box-shadow: ${({ theme }) => theme.shadow.panel};
`;

const SuggestionTitle = styled.h3`
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  padding: 13px 14px;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 14px;
`;

const SuggestionList = styled.div`
  display: grid;
`;

const SuggestionItem = styled.button`
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  border: 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  padding: 0 14px;
  background: #ffffff;
  color: ${({ theme }) => theme.color.foreground};
  text-align: left;

  &:last-child {
    border-bottom: 0;
  }

  &:hover {
    background: ${({ theme }) => theme.color.panelAlt};
  }

  svg {
    flex: 0 0 auto;
    color: ${({ theme }) => theme.color.primary};
  }
`;
