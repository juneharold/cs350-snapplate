"use client";

import type { PendingPhoto } from "@/lib/store/capture";

/**
 * Read a File into the shape `useCapture` expects.
 *
 * We grab dimensions by decoding the data URL into an Image. Real EXIF
 * extraction (captured_at, GPS) lands once we add a parser library —
 * for now the device's current location / wall-clock fill in.
 */
export function readFileAsPendingPhoto(file: File): Promise<PendingPhoto> {
  return new Promise<PendingPhoto>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.onload = () => {
      const dataUrl = String(reader.result);
      const img = new Image();
      img.onload = () => {
        resolve({
          key: `${file.name}-${file.size}-${file.lastModified}`,
          dataUrl,
          name: file.name || "photo.jpg",
          bytes: file.size,
          width: img.naturalWidth,
          height: img.naturalHeight,
          captured_at: file.lastModified
            ? new Date(file.lastModified).toISOString()
            : null,
          lat: null,
          lng: null,
        });
      };
      img.onerror = () =>
        resolve({
          key: `${file.name}-${file.size}-${file.lastModified}`,
          dataUrl,
          name: file.name || "photo.jpg",
          bytes: file.size,
          width: 0,
          height: 0,
          captured_at: file.lastModified
            ? new Date(file.lastModified).toISOString()
            : null,
          lat: null,
          lng: null,
        });
      img.src = dataUrl;
    };
    reader.readAsDataURL(file);
  });
}

export async function readManyFiles(files: FileList | File[]): Promise<PendingPhoto[]> {
  const arr = Array.from(files);
  return Promise.all(arr.map(readFileAsPendingPhoto));
}

/**
 * Build a `PendingPhoto` from a freshly captured camera frame.
 *
 * Mirrors `readFileAsPendingPhoto`'s shape so the preview/upload path is
 * identical — there's just no `File`, so we estimate `bytes` from the
 * base64 payload and synthesize a unique key. JPEG at 0.85 keeps a 1080p
 * frame well under 1 MB, consistent with the existing data-URL contract.
 */
export function pendingPhotoFromCanvas(
  canvas: HTMLCanvasElement,
  meta?: { lat?: number | null; lng?: number | null },
): PendingPhoto {
  const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
  const base64 = dataUrl.split(",")[1] ?? "";
  const bytes = Math.round((base64.length * 3) / 4);
  const stamp = Date.now();
  return {
    // No File to derive the usual `name-size-lastModified` key from; this
    // only needs to be unique within `pending[]` (and identify the cover).
    key: `cam-${stamp}-${Math.random().toString(36).slice(2, 8)}`,
    dataUrl,
    name: `snap-${stamp}.jpg`,
    bytes,
    width: canvas.width,
    height: canvas.height,
    captured_at: new Date(stamp).toISOString(),
    lat: meta?.lat ?? null,
    lng: meta?.lng ?? null,
  };
}
