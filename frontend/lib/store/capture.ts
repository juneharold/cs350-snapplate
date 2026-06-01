"use client";

import { create } from "zustand";
import type { LatLng } from "@/lib/types";

/**
 * In-memory hand-off between the capture picker and the preview screen.
 *
 * We intentionally keep this OUT of localStorage — data URLs for raw
 * camera photos can blow the 5MB cap fast. If the user reloads
 * `/capture/preview` before saving, we send them back to `/capture`.
 */
export type PendingPhoto = {
  /** Stable per-file id used to identify the cover. */
  key: string;
  /** The raw File — sent as multipart to the real backend's /media/upload. */
  file: File;
  /** Data URL — preview only, never persisted. */
  dataUrl: string;
  /** Original filename, used by MSW to deterministically pick a tone. */
  name: string;
  bytes: number;
  width: number;
  height: number;
  captured_at: string | null;
  lat: number | null;
  lng: number | null;
};

type CaptureState = {
  pending: PendingPhoto[];
  coverKey: string | null;
  setPending: (photos: PendingPhoto[]) => void;
  clear: () => void;
  setCover: (key: string) => void;
};

export const useCapture = create<CaptureState>((set) => ({
  pending: [],
  coverKey: null,
  setPending: (photos) =>
    set({
      pending: photos,
      coverKey: photos[0]?.key ?? null,
    }),
  clear: () => set({ pending: [], coverKey: null }),
  setCover: (key) => set({ coverKey: key }),
}));

/**
 * Use the photo's captured_at / lat / lng if available, otherwise fall
 * back to the device's current values.
 */
export function deriveDraftMeta(
  photos: PendingPhoto[],
  fallback: { now: Date; location: LatLng | null },
): { captured_at: string; lat: number | null; lng: number | null } {
  const withTs = photos.find((p) => p.captured_at);
  const withLoc = photos.find((p) => p.lat != null && p.lng != null);
  return {
    captured_at: withTs?.captured_at ?? fallback.now.toISOString(),
    lat: withLoc?.lat ?? fallback.location?.lat ?? null,
    lng: withLoc?.lng ?? fallback.location?.lng ?? null,
  };
}
