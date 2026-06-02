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
          file,
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
          file,
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
