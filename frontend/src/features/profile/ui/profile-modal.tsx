"use client";

import { useAtom } from "jotai";
import styled from "styled-components";
import { isProfileModalOpenAtom } from "@/features/profile/model/profile-modal.atom";
import { Button } from "@/shared/ui/button";
import { Modal } from "@/shared/ui/modal";

export function ProfileModal() {
  const [isOpen, setIsOpen] = useAtom(isProfileModalOpenAtom);

  return (
    <Modal isOpen={isOpen} title="나의 프로필" onClose={() => setIsOpen(false)}>
      <Content>
        <Field>
          <Label htmlFor="team">응원 팀</Label>
          <Input id="team" placeholder="예: 롯데 자이언츠" />
        </Field>
        <Field>
          <Label htmlFor="budget">1인 예산</Label>
          <Input id="budget" placeholder="예: 50,000원" />
        </Field>
        <Field>
          <Label htmlFor="seat">좌석 선호</Label>
          <Input id="seat" placeholder="예: 응원석, 시야 좋은 곳, 그늘" />
        </Field>
        <Button type="button" variant="primary">
          선호 저장
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

const Field = styled.div`
  display: grid;
  gap: 8px;
`;

const Label = styled.label`
  font-size: 13px;
  font-weight: 700;
`;

const Input = styled.input`
  min-height: 42px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 12px;
`;
