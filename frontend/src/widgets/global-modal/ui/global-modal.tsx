"use client";

import { LoginModal } from "@/features/auth/ui/login-modal";
import { ProfileModal } from "@/features/profile/ui/profile-modal";

export function GlobalModal() {
  return (
    <>
      <LoginModal />
      <ProfileModal />
    </>
  );
}
