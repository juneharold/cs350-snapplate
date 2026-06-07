"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Live rear-camera stream for the capture screen.
 *
 * Owns the fiddly MediaStream lifecycle so the page stays readable:
 *  • starts `getUserMedia({ facingMode: "environment" })` on mount,
 *  • guards against React StrictMode's dev double-mount (two streams /
 *    a stuck camera light),
 *  • detects torch support and exposes a toggle,
 *  • and stops every track on unmount — callers also call `stop()`
 *    explicitly before navigating so the light dies instantly.
 */
export type CameraStatus = "idle" | "requesting" | "live" | "unavailable";

// `torch` isn't in the standard lib DOM types yet.
type TorchCapabilities = MediaTrackCapabilities & { torch?: boolean };
type TorchConstraintSet = MediaTrackConstraintSet & { torch?: boolean };

/** Human hint for why the camera couldn't open, by DOMException name. */
function reasonFor(err: unknown): string {
  const name = err instanceof Error ? err.name : "";
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Camera permission was blocked. Allow it in the address-bar icon, then reload.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No camera was found on this device.";
    case "NotReadableError":
      return "The camera is in use by another app or tab.";
    default:
      return "Couldn't start the camera.";
  }
}

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const startedRef = useRef(false);
  const [status, setStatus] = useState<CameraStatus>("idle");
  const [reason, setReason] = useState<string | null>(null);
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchOn, setTorchOn] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    startedRef.current = false;
    setTorchOn(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (startedRef.current) return; // dev StrictMode: skip the 2nd mount
    startedRef.current = true;

    const md = typeof navigator !== "undefined" ? navigator.mediaDevices : undefined;
    if (!md?.getUserMedia) {
      // getUserMedia only exists in a secure context (https:// or
      // localhost) — a LAN IP or VS Code's embedded browser won't have it.
      const insecure = typeof window !== "undefined" && !window.isSecureContext;
      setReason(
        insecure
          ? "Camera needs a secure context — open http://localhost:3000 in a real browser (not a LAN IP or an embedded preview)."
          : "This browser doesn't expose the camera API.",
      );
      console.warn("[useCamera] getUserMedia unavailable", {
        hasMediaDevices: Boolean(md),
        isSecureContext: typeof window !== "undefined" ? window.isSecureContext : "n/a",
        href: typeof window !== "undefined" ? window.location.href : "n/a",
      });
      setStatus("unavailable");
      return;
    }

    setStatus("requesting");
    // Ask for the rear camera at a main-sensor resolution. Phones expose
    // several back lenses (ultra-wide ≈ 0.5x, main = 1x); there's no web API
    // to pick the lens directly, but requesting 1080p reliably nudges the
    // browser to the main 1x sensor instead of defaulting to ultra-wide.
    md.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        const track = stream.getVideoTracks()[0];
        const caps = track?.getCapabilities?.() as TorchCapabilities | undefined;
        setTorchSupported(Boolean(caps?.torch));
        setStatus("live");
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn("[useCamera] getUserMedia failed:", err);
        setReason(reasonFor(err));
        setStatus("unavailable");
      });

    return () => {
      cancelled = true;
      stop();
    };
  }, [stop]);

  const toggleTorch = useCallback(async () => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track) return;
    const next = !torchOn;
    try {
      await track.applyConstraints({ advanced: [{ torch: next } as TorchConstraintSet] });
      setTorchOn(next);
    } catch {
      // Some devices advertise torch but throw on apply — leave state as-is.
    }
  }, [torchOn]);

  return { videoRef, status, reason, torchSupported, torchOn, toggleTorch, stop };
}
