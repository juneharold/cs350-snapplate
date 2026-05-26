"use client";

import { create } from "zustand";

type ToastState = {
  message: string | null;
  show: (message: string, durationMs?: number) => void;
  clear: () => void;
};

let lastTimer: ReturnType<typeof setTimeout> | null = null;

export const useToast = create<ToastState>((set) => ({
  message: null,
  show: (message, durationMs = 2400) => {
    if (lastTimer) clearTimeout(lastTimer);
    set({ message });
    if (typeof window !== "undefined") {
      lastTimer = setTimeout(() => set({ message: null }), durationMs);
    }
  },
  clear: () => {
    if (lastTimer) clearTimeout(lastTimer);
    set({ message: null });
  },
}));
