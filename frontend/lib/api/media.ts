"use client";

import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { MediaUploadResponse } from "@/lib/types";

/**
 * Upload one or more photos.
 *
 * The real backend will accept `multipart/form-data`. For the MVP mock,
 * the client already reads each File to a data URL + extracts whatever
 * EXIF it can, then POSTs a JSON payload describing the files. When the
 * real backend lands we'll swap this to a `FormData` body without
 * changing the response shape.
 */
export type UploadFileInput = {
  name: string;
  bytes: number;
  width?: number;
  height?: number;
  captured_at?: string | null;
  lat?: number | null;
  lng?: number | null;
  label?: string;
};

export function useUploadMedia() {
  return useMutation({
    mutationFn: (files: UploadFileInput[]) =>
      apiFetch<MediaUploadResponse>("/media/upload", {
        method: "POST",
        body: { files },
      }),
  });
}
