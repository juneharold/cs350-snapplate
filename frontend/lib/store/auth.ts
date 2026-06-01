"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { AuthUser, LatLng } from "@/lib/types";

type AuthState = {
  accessToken: string | null;
  user: AuthUser | null;

  /** Onboarding marketing carousel (3 slides) seen at least once. */
  hasSeenOnboarding: boolean;

  /** Tri-state: null = never asked, true/false = browser response. */
  locationGranted: boolean | null;
  currentLocation: LatLng | null;

  /** True once the persisted store has rehydrated from localStorage. Guards
   *  route gates from acting on the (empty) pre-hydration state on first paint. */
  hasHydrated: boolean;

  setSession: (token: string, user: AuthUser) => void;
  setUser: (user: AuthUser) => void;
  setHasSeenOnboarding: (v: boolean) => void;
  setLocationGranted: (granted: boolean) => void;
  setCurrentLocation: (loc: LatLng | null) => void;
  setHasHydrated: (v: boolean) => void;
  logout: () => void;
};

const initialState = {
  accessToken: null,
  user: null,
  hasSeenOnboarding: false,
  locationGranted: null,
  currentLocation: null,
} as const;

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      ...initialState,
      hasHydrated: false,
      setSession: (accessToken, user) => set({ accessToken, user }),
      setUser: (user) => set({ user }),
      setHasSeenOnboarding: (hasSeenOnboarding) => set({ hasSeenOnboarding }),
      setLocationGranted: (locationGranted) => set({ locationGranted }),
      setCurrentLocation: (currentLocation) => set({ currentLocation }),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      // Clear the account session only. Location grant + last known
      // location are device-level (tied to the browser, not the account),
      // so we keep them — otherwise re-login loses an already-granted
      // permission and the home screen falsely asks for location again.
      // Keep hasHydrated true so route gates don't bounce after logout.
      logout: () =>
        set((s) => ({
          ...initialState,
          locationGranted: s.locationGranted,
          currentLocation: s.currentLocation,
          hasHydrated: true,
        })),
    }),
    {
      name: "snapplate.auth",
      storage: createJSONStorage(() => localStorage),
      // Persist last known location for smoother home experience.
      partialize: (s) => ({
        accessToken: s.accessToken,
        user: s.user,
        hasSeenOnboarding: s.hasSeenOnboarding,
        locationGranted: s.locationGranted,
        currentLocation: s.currentLocation,
      }),
      // Flip hasHydrated once localStorage has been read back, so route gates
      // don't bounce a logged-in user on a hard navigation / refresh.
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    },
  ),
);

/**
 * Default fallback location (Daejeon — Eoeun-dong area, near KAIST)
 * used when geolocation is denied or unavailable.
 */
export const FALLBACK_LOCATION: LatLng = { lat: 36.371, lng: 127.361 };
