"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { TasteProfileResponse } from "@/lib/types";

export function useTasteProfile() {
  return useQuery({
    queryKey: ["taste", "profile"],
    queryFn: () => apiFetch<TasteProfileResponse>("/taste/profile"),
  });
}

export function useTasteRefresh() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ job_id: string; estimated_seconds: number }>("/taste/refresh", {
        method: "POST",
      }),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["taste", "profile"] });
    },
  });
}
