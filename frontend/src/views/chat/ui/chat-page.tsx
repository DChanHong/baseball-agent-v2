"use client";

import styled from "styled-components";
import { LoginModal } from "@/features/auth/ui/login-modal";
import { ProfileModal } from "@/features/profile/ui/profile-modal";
import { AppHeader } from "@/widgets/app-header/ui/app-header";
import { ChatPanel } from "@/widgets/chat/ui/chat-panel";
import { SourceDrawer } from "@/widgets/source-drawer/ui/source-drawer";

export function ChatPage() {
  return (
    <Shell>
      <AppHeader />
      <Workspace>
        <ChatPanel />
        <SourceDrawer />
      </Workspace>
      <LoginModal />
      <ProfileModal />
    </Shell>
  );
}

const Shell = styled.div`
  min-height: 100vh;
`;

const Workspace = styled.div`
  min-height: calc(100vh - 72px);
`;
