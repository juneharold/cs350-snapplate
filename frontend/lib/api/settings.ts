"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { SettingsResponse } from "@/lib/types";

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: () => apiFetch<SettingsResponse>("/settings"),
  });
}

type Patch = Partial<{
  notifications: Partial<SettingsResponse["notifications"]>;
  appearance: SettingsResponse["appearance"];
}>;

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Patch) =>
      apiFetch<SettingsResponse>("/settings", { method: "PATCH", body: patch }),
    onMutate: async (patch) => {
      await qc.cancelQueries({ queryKey: ["settings"] });
      const prev = qc.getQueryData<SettingsResponse>(["settings"]);
      if (prev) {
        qc.setQueryData<SettingsResponse>(["settings"], {
          ...prev,
          notifications: {
            ...prev.notifications,
            ...(patch.notifications ?? {}),
          },
          appearance: patch.appearance ?? prev.appearance,
        });
      }
      return { prev };
    },
    onError: (_e, _patch, ctx) => {
      if (ctx?.prev) qc.setQueryData(["settings"], ctx.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
  });
}
