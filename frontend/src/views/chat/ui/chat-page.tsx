"use client";

import styled from "styled-components";
import { LoginModal } from "@/features/auth/ui/login-modal";
import { ProfileModal } from "@/features/profile/ui/profile-modal";
import { AppHeader } from "@/widgets/app-header/ui/app-header";
import { ChatPanel } from "@/widgets/chat/ui/chat-panel";
import { ChatSidebar } from "@/widgets/chat-sidebar/ui/chat-sidebar";
import { SourceDrawer } from "@/widgets/source-drawer/ui/source-drawer";

export function ChatPage() {
  return (
    <Shell>
      <AppHeader />
      <Workspace>
        <ChatSidebar />
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
  padding-top: 72px;

  @media (max-width: 720px) {
    padding-top: 64px;
  }
`;

const Workspace = styled.div`
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  min-height: calc(100vh - 72px);

  @media (max-width: 720px) {
    grid-template-columns: minmax(0, 1fr);
    min-height: calc(100vh - 64px);
    padding-left: 56px;
  }

  @media (max-width: 480px) {
    padding-left: 0;
  }
`;
