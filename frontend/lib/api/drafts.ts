"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type {
  CreateDraftRequest,
  DraftDetail,
  DraftListResponse,
  FinalizeDraftRequest,
  FinalizeDraftResponse,
} from "@/lib/types";

export const draftKeys = {
  all: ["drafts"] as const,
  list: () => [...draftKeys.all, "list"] as const,
  detail: (id: string) => [...draftKeys.all, "detail", id] as const,
};

export function useDrafts() {
  return useQuery({
    queryKey: draftKeys.list(),
    queryFn: () => apiFetch<DraftListResponse>("/drafts"),
  });
}

export function useDraft(id: string | null) {
  return useQuery({
    queryKey: id ? draftKeys.detail(id) : ["drafts", "detail", "noop"],
    enabled: !!id,
    queryFn: () => apiFetch<DraftDetail>(`/drafts/${id}`),
  });
}

export function useCreateDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateDraftRequest) =>
      apiFetch<DraftDetail>("/drafts", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: draftKeys.list() });
    },
  });
}

export function useUpdateDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<{ restaurant_id: string; cover_media_id: string; captured_at: string }>) =>
      apiFetch<DraftDetail>(`/drafts/${id}`, { method: "PATCH", body: patch }),
    onSuccess: (data) => {
      qc.setQueryData(draftKeys.detail(id), data);
      qc.invalidateQueries({ queryKey: draftKeys.list() });
    },
  });
}

export function useDeleteDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/drafts/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: draftKeys.list() });
    },
  });
}

export function useFinalizeDraft(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FinalizeDraftRequest) =>
      apiFetch<FinalizeDraftResponse>(`/drafts/${id}/finalize`, {
        method: "POST",
        body,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: draftKeys.list() });
      qc.invalidateQueries({ queryKey: ["entries"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
