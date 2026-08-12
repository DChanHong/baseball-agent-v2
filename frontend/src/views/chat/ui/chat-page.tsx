"use client";

import styled from "styled-components";
import { LoginModal } from "@/features/auth/ui/login-modal";
import { ProfileModal } from "@/features/profile/ui/profile-modal";
import { ChatPanel } from "@/widgets/chat/ui/chat-panel";
import { ChatSidebar } from "@/widgets/chat-sidebar/ui/chat-sidebar";
import { SourceDrawer } from "@/widgets/source-drawer/ui/source-drawer";

export function ChatPage() {
  return (
    <Shell>
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
`;

const Workspace = styled.div`
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  min-height: 100vh;

  @media (max-width: 720px) {
    grid-template-columns: minmax(0, 1fr);
    padding-left: 58px;
  }

  @media (max-width: 480px) {
    padding-left: 0;
  }
`;
