"use client";

import { useAtomValue, useSetAtom } from "jotai";
import {
  globalModalAtom,
  type GlobalModalType,
} from "@/features/global-modal/model/global-modal.atom";

export function useGlobalModal() {
  const modal = useAtomValue(globalModalAtom);
  const setModal = useSetAtom(globalModalAtom);

  return {
    currentModal: modal.type,
    isLoginModalOpen: modal.type === "login",
    isProfileModalOpen: modal.type === "profile",
    openGlobalModal: (type: GlobalModalType) => setModal({ type }),
    openLoginModal: () => setModal({ type: "login" }),
    openProfileModal: () => setModal({ type: "profile" }),
    closeGlobalModal: () => setModal({ type: null }),
  };
}
