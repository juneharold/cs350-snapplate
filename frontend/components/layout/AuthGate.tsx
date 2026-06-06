"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/store/auth";

/**
 * Client-side route guard for the (app) group.
 *
 * - No token → bounce to /login
 * - Authed but `is_new` and no nickname → bounce to /onboarding
 *   so first-timers can't skip onboarding by deep-linking to /diary.
 *
 * IMPORTANT: we wait for the persisted auth store to rehydrate (`hasHydrated`)
 * before deciding. On a hard navigation / refresh, the store starts empty and
 * only fills from localStorage a tick later — acting before then would bounce a
 * logged-in user to /login. While not hydrated we render nothing (no flash).
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const hasHydrated = useAuth((s) => s.hasHydrated);
  const accessToken = useAuth((s) => s.accessToken);
  const user = useAuth((s) => s.user);
  const hasSeenOnboarding = useAuth((s) => s.hasSeenOnboarding);

  useEffect(() => {
    if (!hasHydrated) return; // wait for localStorage rehydration
    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (!hasSeenOnboarding || !user?.nickname) {
      router.replace("/onboarding");
    }
  }, [hasHydrated, accessToken, hasSeenOnboarding, user?.nickname, router]);

  if (!hasHydrated) return null;
  if (!accessToken) return null;
  if (!hasSeenOnboarding || !user?.nickname) return null;
  return <>{children}</>;
}
