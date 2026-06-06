"use client";

import { create } from "zustand";
import type { LatLng } from "@/lib/types";

/** Max photos per capture session (a single draft). */
export const MAX_PHOTOS = 5;

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
  /** Append more shots (capped at MAX_PHOTOS); the latest becomes the cover. */
  addPhotos: (photos: PendingPhoto[]) => void;
  /** Swap a single photo (by key) for a freshly retaken one, in place. */
  replacePhoto: (targetKey: string, photo: PendingPhoto) => void;
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
  addPhotos: (photos) =>
    set((s) => {
      const merged = [...s.pending, ...photos].slice(0, MAX_PHOTOS);
      // Show the most recent take straight away.
      return { pending: merged, coverKey: merged[merged.length - 1]?.key ?? s.coverKey };
    }),
  replacePhoto: (targetKey, photo) =>
    set((s) => {
      const idx = s.pending.findIndex((p) => p.key === targetKey);
      if (idx === -1) {
        // Target gone — fall back to appending under the cap.
        const merged = [...s.pending, photo].slice(0, MAX_PHOTOS);
        return { pending: merged, coverKey: photo.key };
      }
      const next = s.pending.slice();
      next[idx] = photo;
      return { pending: next, coverKey: photo.key };
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
