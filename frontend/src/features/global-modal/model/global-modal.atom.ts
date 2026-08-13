"use client";

import { atom } from "jotai";

export type GlobalModalType = "login" | "profile";

export type GlobalModalState = {
  type: GlobalModalType | null;
};

export const globalModalAtom = atom<GlobalModalState>({
  type: null,
});
