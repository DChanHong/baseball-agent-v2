"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useAtom } from "jotai";
import { ArrowUp, Armchair, CloudSun, Sparkles, Ticket } from "lucide-react";
import { useRef, useState, type ReactNode } from "react";
import styled from "styled-components";
import { chatInputAtom } from "@/features/send-message/model/chat-input.atom";

type SuggestionCategory = "seat" | "ticket" | "weather";

type ChatComposerProps = {
  disabled?: boolean;
  onSendMessage?: (message: string) => void;
  showSuggestions?: boolean;
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

export function ChatComposer({
  disabled = false,
  onSendMessage,
  showSuggestions = true,
}: ChatComposerProps) {
  const [value, setValue] = useAtom(chatInputAtom);
  const [activeCategory, setActiveCategory] = useState<SuggestionCategory | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleCommandSelect = (command: string) => {
    setValue(command);
    setActiveCategory(null);
    inputRef.current?.focus();
    window.requestAnimationFrame(resizeTextarea);
  };

  const resizeTextarea = () => {
    const input = inputRef.current;

    if (!input) {
      return;
    }

    input.style.height = "0px";
    input.style.height = `${input.scrollHeight}px`;
  };

  const handleSendMessage = () => {
    const trimmedValue = value.trim();

    if (!trimmedValue || disabled) {
      return;
    }

    onSendMessage?.(trimmedValue);
    setValue("");

    window.requestAnimationFrame(resizeTextarea);
  };

  return (
    <ComposerShell>
      {showSuggestions ? (
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
      ) : null}

      <AnimatePresence>
        {showSuggestions && activeCategory ? (
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

      <PromptCard aria-label="채팅 입력">
        <InputArea>
          <Input
            ref={inputRef}
            rows={1}
            placeholder="ChatGPT에게 물어보세요"
            value={value}
            disabled={disabled}
            onChange={(event) => {
              setValue(event.target.value);
              resizeTextarea();
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSendMessage();
              }
            }}
          />
        </InputArea>
        <FunctionRow>
          <SendButton
            type="button"
            aria-label="메시지 전송"
            disabled={!value.trim() || disabled}
            $disabled={disabled}
            onClick={handleSendMessage}
          >
            <ArrowUp size={18} />
          </SendButton>
        </FunctionRow>
      </PromptCard>
    </ComposerShell>
  );
}

const ComposerShell = styled.div`
  position: fixed;
  right: max(20px, env(safe-area-inset-right));
  bottom: max(24px, env(safe-area-inset-bottom));
  left: calc(300px + 20px);
  z-index: 20;
  display: grid;
  justify-items: center;
  gap: 12px;
  pointer-events: none;

  @media (max-width: 720px) {
    left: calc(58px + 14px);
    right: 14px;
    bottom: max(16px, env(safe-area-inset-bottom));
  }

  @media (max-width: 480px) {
    left: 12px;
    right: 12px;
  }
`;

const PromptCard = styled.div`
  display: flex;
  width: min(100%, 980px);
  min-height: 66px;
  align-items: center;
  gap: 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 999px;
  padding: 8px 12px 8px 24px;
  background: ${({ theme }) => theme.color.panel};
  box-shadow:
    0 18px 48px rgba(32, 35, 34, 0.16),
    0 2px 12px rgba(32, 35, 34, 0.08);
  pointer-events: auto;

  @media (max-width: 560px) {
    gap: 8px;
    min-height: 58px;
    padding: 7px 8px 7px 18px;
  }
`;

const InputArea = styled.div`
  display: grid;
  flex: 1 1 auto;
  min-width: 0;
`;

const Input = styled.textarea`
  width: 100%;
  max-height: 128px;
  border: 0;
  outline: 0;
  padding: 7px 0;
  resize: none;
  background: transparent;
  color: ${({ theme }) => theme.color.foreground};
  font-size: 16px;
  line-height: 1.45;
  overflow-y: auto;

  &::placeholder {
    color: ${({ theme }) => theme.color.muted};
  }

  &:disabled {
    cursor: wait;
  }
`;

const FunctionRow = styled.div`
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;

  @media (max-width: 560px) {
    gap: 5px;
  }
`;

const SendButton = styled.button<{ $disabled: boolean }>`
  display: inline-grid;
  flex: 0 0 auto;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: #f1772f;
  color: #ffffff;
  transition:
    background 160ms ease,
    opacity 160ms ease;

  &:disabled {
    background: #e2e5e0;
    color: #99a29b;
    cursor: ${({ $disabled }) => ($disabled ? "wait" : "not-allowed")};
  }

  @media (max-width: 560px) {
    width: 42px;
    height: 42px;
  }
`;

const CommandGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: min(100%, 760px);
  pointer-events: auto;

  @media (max-width: 560px) {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
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

  @media (max-width: 560px) {
    min-height: 58px;
    padding: 8px 6px;
    font-size: 12px;

    svg {
      width: 16px;
      height: 16px;
    }
  }
`;

const SuggestionWrap = styled(motion.div)`
  width: min(100%, 760px);
  overflow: hidden;
  pointer-events: auto;
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
