"use client";

import { useAtom } from "jotai";
import styled from "styled-components";
import { useCurrentUser } from "@/features/auth/model/auth-query";
import { isProfileModalOpenAtom } from "@/features/profile/model/profile-modal.atom";
import { Button } from "@/shared/ui/button";
import { Modal } from "@/shared/ui/modal";

export function ProfileModal() {
  const [isOpen, setIsOpen] = useAtom(isProfileModalOpenAtom);
  const { data: user } = useCurrentUser();

  return (
    <Modal isOpen={isOpen} title="나의 프로필" onClose={() => setIsOpen(false)}>
      <Content>
        <Field>
          <Label htmlFor="nickname">닉네임</Label>
          <Input id="nickname" value={user?.nickname ?? ""} readOnly />
        </Field>
        <Field>
          <Label htmlFor="team">응원 팀</Label>
          <Input id="team" value={user?.favoriteTeam ?? ""} readOnly placeholder="아직 설정되지 않았습니다" />
        </Field>
        <Button type="button" variant="secondary" disabled>
          프로필 수정 준비 중
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
