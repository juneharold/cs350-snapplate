"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/store/auth";
import type { AuthUser, MagicLinkResponse, MeResponse, VerifyResponse } from "@/lib/types";

/**
 * Mock-only field that the MSW handler surfaces so the EmailLinkSent
 * screen can simulate "tap the link in your inbox" with one button.
 * The real backend will not return this.
 */
type MockMagicLinkResponse = MagicLinkResponse & { _mock_link_token?: string };

export function useMagicLink() {
  return useMutation({
    mutationFn: (email: string) =>
      apiFetch<MockMagicLinkResponse>("/auth/magic-link", {
        method: "POST",
        body: { email },
        skipAuth: true,
      }),
  });
}

export function useVerifyToken() {
  const setSession = useAuth((s) => s.setSession);
  return useMutation({
    mutationFn: (token: string) =>
      apiFetch<VerifyResponse>("/auth/verify", {
        method: "POST",
        body: { token },
        skipAuth: true,
      }),
    onSuccess: (data) => {
      setSession(data.access_token, data.user);
    },
  });
}

export function useMe() {
  const accessToken = useAuth((s) => s.accessToken);
  return useQuery({
    queryKey: ["me"],
    enabled: !!accessToken,
    queryFn: () => apiFetch<MeResponse>("/me"),
  });
}

export function useUpdateMe() {
  const qc = useQueryClient();
  const setUser = useAuth((s) => s.setUser);
  return useMutation({
    mutationFn: (patch: { nickname?: string }) =>
      apiFetch<MeResponse>("/me", { method: "PATCH", body: patch }),
    onSuccess: (data) => {
      qc.setQueryData(["me"], data);
      const next: AuthUser = {
        id: data.id,
        email: data.email,
        nickname: data.nickname,
        profile_image_url: data.profile_image_url,
      };
      setUser(next);
    },
  });
}

export function useLogout() {
  const logout = useAuth((s) => s.logout);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<void>("/auth/logout", { method: "POST" }),
    onSettled: () => {
      logout();
      qc.clear();
    },
  });
}
