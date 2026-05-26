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
 * We intentionally render `null` while redirecting instead of a spinner;
 * the redirect happens on first paint and a spinner would just flash.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const accessToken = useAuth((s) => s.accessToken);
  const user = useAuth((s) => s.user);
  const hasSeenOnboarding = useAuth((s) => s.hasSeenOnboarding);

  useEffect(() => {
    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (!hasSeenOnboarding || !user?.nickname) {
      router.replace("/onboarding");
    }
  }, [accessToken, hasSeenOnboarding, user?.nickname, router]);

  if (!accessToken) return null;
  if (!hasSeenOnboarding || !user?.nickname) return null;
  return <>{children}</>;
}
