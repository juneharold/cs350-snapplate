"use client";

import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { MediaUploadResponse } from "@/lib/types";

/**
 * Upload one or more photos as multipart/form-data to the real backend.
 *
 * The backend's POST /media/upload expects `files[]` (the raw bytes) plus an
 * optional `extract_exif` flag, and returns { uploads: MediaRecord[] }. We send
 * the original File objects directly; the server does EXIF read/strip + variants.
 */
export function useUploadMedia() {
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      for (const f of files) form.append("files", f, f.name || "photo.jpg");
      form.append("extract_exif", "true");
      return apiFetch<MediaUploadResponse>("/media/upload", {
        method: "POST",
        body: form,
      });
    },
  });
}
