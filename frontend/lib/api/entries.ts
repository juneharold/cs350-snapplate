"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { EntryDetail, EntryListResponse } from "@/lib/types";

export const entryKeys = {
  all: ["entries"] as const,
  list: () => [...entryKeys.all, "list"] as const,
  detail: (id: string) => [...entryKeys.all, "detail", id] as const,
};

export function useEntries() {
  return useQuery({
    queryKey: entryKeys.list(),
    queryFn: () => apiFetch<EntryListResponse>("/entries"),
  });
}

export function useEntry(id: string | null) {
  return useQuery({
    queryKey: id ? entryKeys.detail(id) : ["entries", "detail", "noop"],
    enabled: !!id,
    queryFn: () => apiFetch<EntryDetail>(`/entries/${id}`),
  });
}
