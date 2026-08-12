"use client";

import { useState, type FormEvent } from "react";
import { useAtom } from "jotai";
import { Save } from "lucide-react";
import styled from "styled-components";
import { AuthApiError, type CurrentUser } from "@/features/auth/api/auth-api";
import { useCurrentUser, useUpdateCurrentUser } from "@/features/auth/model/auth-query";
import { isProfileModalOpenAtom } from "@/features/profile/model/profile-modal.atom";
import { Button } from "@/shared/ui/button";
import { Modal } from "@/shared/ui/modal";

const teamOptions = [
  { id: "LG", label: "LG 트윈스" },
  { id: "DOOSAN", label: "두산 베어스" },
  { id: "KIWOOM", label: "키움 히어로즈" },
  { id: "SSG", label: "SSG 랜더스" },
  { id: "KT", label: "KT 위즈" },
  { id: "KIA", label: "KIA 타이거즈" },
  { id: "SAMSUNG", label: "삼성 라이온즈" },
  { id: "LOTTE", label: "롯데 자이언츠" },
  { id: "HANWHA", label: "한화 이글스" },
  { id: "NC", label: "NC 다이노스" },
] as const;

export function ProfileModal() {
  const [isOpen, setIsOpen] = useAtom(isProfileModalOpenAtom);
  const { data: user } = useCurrentUser();

  return (
    <Modal isOpen={isOpen} title="나의 프로필" onClose={() => setIsOpen(false)}>
      <ProfileForm user={user ?? null} onClose={() => setIsOpen(false)} />
    </Modal>
  );
}

type ProfileFormProps = {
  user: CurrentUser | null;
  onClose: () => void;
};

function ProfileForm({ user, onClose }: ProfileFormProps) {
  const {
    error: updateError,
    isPending: isSaving,
    mutateAsync: updateCurrentUser,
  } = useUpdateCurrentUser();
  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [favoriteTeam, setFavoriteTeam] = useState(user?.favoriteTeam ?? "");
  const [formError, setFormError] = useState<string | null>(null);

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedNickname = nickname.trim();
    if (!trimmedNickname) {
      setFormError("닉네임을 입력해주세요.");
      return;
    }

    setFormError(null);

    try {
      await updateCurrentUser({
        nickname: trimmedNickname,
        favoriteTeam: favoriteTeam || null,
      });
      onClose();
    } catch {
      // The mutation error is rendered below.
    }
  }

  return (
    <Content as="form" onSubmit={submitProfile}>
      <Field>
        <Label htmlFor="nickname">닉네임</Label>
        <Input
          id="nickname"
          value={nickname}
          maxLength={32}
          disabled={!user || isSaving}
          onChange={(event) => setNickname(event.target.value)}
        />
      </Field>
      <Field>
        <Label htmlFor="team">응원 팀</Label>
        <Select
          id="team"
          value={favoriteTeam}
          disabled={!user || isSaving}
          onChange={(event) => setFavoriteTeam(event.target.value)}
        >
          <option value="">아직 설정되지 않았습니다</option>
          {teamOptions.map((team) => (
            <option key={team.id} value={team.id}>
              {team.label}
            </option>
          ))}
        </Select>
      </Field>
      {formError || updateError ? (
        <ErrorText>{formError ?? getProfileErrorMessage(updateError)}</ErrorText>
      ) : null}
      <Actions>
        <Button type="button" variant="secondary" onClick={onClose}>
          취소
        </Button>
        <Button type="submit" variant="primary" disabled={!user || isSaving}>
          <Save aria-hidden="true" size={16} />
          {isSaving ? "저장 중" : "저장"}
        </Button>
      </Actions>
    </Content>
  );
}

function getProfileErrorMessage(error: Error | null): string {
  if (error instanceof AuthApiError) {
    if (error.status === 409) {
      return "이미 사용 중인 닉네임입니다.";
    }
    if (error.status === 401) {
      return "로그인이 필요합니다.";
    }
    if (error.detail === "invalid_favorite_team") {
      return "응원 팀을 다시 선택해주세요.";
    }
    if (error.detail === "nickname_required") {
      return "닉네임을 입력해주세요.";
    }
  }

  return "프로필을 저장하지 못했습니다.";
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

const Select = styled.select`
  min-height: 42px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  padding: 0 12px;
  background: ${({ theme }) => theme.color.panel};
  color: ${({ theme }) => theme.color.foreground};
`;

const ErrorText = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.accent};
  font-size: 13px;
  line-height: 1.4;
`;

const Actions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 8px;

  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
`;
