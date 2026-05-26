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

  setSession: (token: string, user: AuthUser) => void;
  setUser: (user: AuthUser) => void;
  setHasSeenOnboarding: (v: boolean) => void;
  setLocationGranted: (granted: boolean) => void;
  setCurrentLocation: (loc: LatLng | null) => void;
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
      setSession: (accessToken, user) => set({ accessToken, user }),
      setUser: (user) => set({ user }),
      setHasSeenOnboarding: (hasSeenOnboarding) => set({ hasSeenOnboarding }),
      setLocationGranted: (locationGranted) => set({ locationGranted }),
      setCurrentLocation: (currentLocation) => set({ currentLocation }),
      logout: () => set({ ...initialState }),
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
    },
  ),
);

/**
 * Default fallback location (Daejeon — Eoeun-dong area, near KAIST)
 * used when geolocation is denied or unavailable.
 */
export const FALLBACK_LOCATION: LatLng = { lat: 36.371, lng: 127.361 };
