"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Camera, ImagePlus, X, Zap, ZapOff } from "lucide-react";
import { Screen } from "@/components/layout/Screen";
import { useCapture, MAX_PHOTOS, type PendingPhoto } from "@/lib/store/capture";
import { readManyFiles, pendingPhotoFromCanvas } from "@/lib/files";
import { useCamera } from "@/lib/useCamera";

/**
 * Capture entry — a live rear-camera viewfinder.
 *
 * The shutter grabs the current `<video>` frame into a `<canvas>`, attaches
 * fresh GPS, and forwards a single `PendingPhoto` to `/capture/preview` via
 * the in-memory `useCapture` store. When `getUserMedia` is unavailable or
 * denied (insecure context, no camera, permission blocked) we fall back to
 * the native file inputs — `capture="environment"` opens the rear camera on
 * mobile, the plain input opens the gallery.
 */

/** Fresh device location, hard-capped so a slow provider never stalls the
 *  shutter. Null degrades cleanly — preview falls back to the auth-store
 *  location via `deriveDraftMeta`. */
function getFreshLocation(): Promise<{ lat: number; lng: number } | null> {
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      resolve(null);
      return;
    }
    let settled = false;
    const done = (v: { lat: number; lng: number } | null) => {
      if (settled) return;
      settled = true;
      resolve(v);
    };
    const timer = setTimeout(() => done(null), 3000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timer);
        done({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      () => {
        clearTimeout(timer);
        done(null);
      },
      { enableHighAccuracy: false, timeout: 3000, maximumAge: 60_000 },
    );
  });
}

export default function CapturePage() {
  const router = useRouter();
  const setPending = useCapture((s) => s.setPending);
  const addPhotos = useCapture((s) => s.addPhotos);
  const replacePhoto = useCapture((s) => s.replacePhoto);
  const pendingCount = useCapture((s) => s.pending.length);
  const { videoRef, status, reason, torchSupported, torchOn, toggleTorch, stop } = useCamera();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [reading, setReading] = useState(false);
  const [titleSize, setTitleSize] = useState(30);

  // Session mode, read from the URL after mount (window.location.search is
  // only reliable once the soft navigation has committed — reading it during
  // the first render returns the *previous* URL):
  //  • ?retake=<key> — replace that one photo
  //  • ?add=1        — append another photo
  //  • neither       — fresh session
  const [retakeKey, setRetakeKey] = useState<string | null>(null);
  const [addMode, setAddMode] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const rk = params.get("retake");
    const am = params.get("add") === "1";
    setRetakeKey(rk);
    setAddMode(am);
    // Only a plain fresh visit wipes the prior set; add/retake keep it.
    if (!am && !rk) useCapture.getState().clear();
  }, []);

  // Keep the title on a single line — measure the text and scale the font
  // down to whatever fits the available width (font width scales linearly,
  // so one canvas measurement gives the right size; no reflow loop).
  useEffect(() => {
    const el = titleRef.current;
    const container = el?.parentElement;
    if (!el || !container) return;
    const ctx = document.createElement("canvas").getContext("2d");
    if (!ctx) return;
    const fit = () => {
      const avail = el.clientWidth;
      if (!avail) return;
      const cs = getComputedStyle(el);
      ctx.font = `${cs.fontStyle} ${cs.fontWeight} 30px ${cs.fontFamily}`;
      const textW = ctx.measureText(el.textContent ?? "").width;
      if (!textW) return;
      setTitleSize(Math.max(15, Math.min(30, Math.floor((avail * 0.98) / textW * 30))));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  /** Store the new shots — replace one (retake), append (add), or replace all. */
  function commit(photos: PendingPhoto[]) {
    if (retakeKey) {
      if (photos[0]) replacePhoto(retakeKey, photos[0]);
    } else if (addMode) addPhotos(photos);
    else setPending(photos);
  }

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    if (!retakeKey && pendingCount >= MAX_PHOTOS) return;
    setReading(true);
    try {
      const photos = await readManyFiles(files);
      // Retake swaps a single photo; otherwise take only what fits under the cap.
      const limit = retakeKey ? 1 : MAX_PHOTOS - pendingCount;
      commit(photos.slice(0, limit));
      stop();
      router.push("/capture/preview");
    } finally {
      setReading(false);
    }
  }

  async function handleShutter() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0) return;
    if (!retakeKey && pendingCount >= MAX_PHOTOS) return;
    setReading(true);
    try {
      // Centered square crop — matches what the 1:1 viewfinder shows
      // (object-fit: cover centers the same region), so it's WYSIWYG.
      const side = Math.min(video.videoWidth, video.videoHeight);
      const sx = (video.videoWidth - side) / 2;
      const sy = (video.videoHeight - side) / 2;
      canvas.width = side;
      canvas.height = side;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, sx, sy, side, side, 0, 0, side, side);

      const loc = await getFreshLocation();
      const photo = pendingPhotoFromCanvas(canvas, loc ?? {});
      commit([photo]);
      stop();
      router.push("/capture/preview");
    } finally {
      setReading(false);
    }
  }

  const atMax = !retakeKey && pendingCount >= MAX_PHOTOS;

  return (
    <Screen bg="#0A0A08">
      <div className="absolute inset-0 flex flex-col" style={{ color: "var(--color-cream)" }}>
        {/* Header — X hugging the left edge + a one-line title beside it */}
        <div
          className="shrink-0 px-5 flex items-center gap-2.5"
          style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 16px)" }}
        >
          <Link
            href="/"
            aria-label="Close"
            onClick={() => stop()}
            className="flex items-center justify-center rounded-full shrink-0"
            style={{ width: 40, height: 40, background: "rgba(0,0,0,0.5)" }}
          >
            <X size={22} />
          </Link>
          <h1
            ref={titleRef}
            className="leading-tight font-normal"
            style={{
              flex: "1 1 0%",
              minWidth: 0,
              whiteSpace: "nowrap",
              overflow: "hidden",
              fontSize: titleSize,
            }}
          >
            What are you{" "}
            <em style={{ color: "#F4E37A", fontStyle: "italic" }}>eating?</em>
          </h1>
        </div>

        {/* Description — full width, left-aligned from the same margin */}
        <p
          className="shrink-0 px-5"
          style={{ marginTop: 8, fontSize: 14, lineHeight: 1.55, opacity: 0.78 }}
        >
          Snap it now — we&apos;ll remember the place and time. Add the rating
          later when you&apos;re done eating.
        </p>

        {/* Scrollable content — viewfinder centered in the remaining space */}
        <div className="flex-1 overflow-y-auto px-5 flex flex-col" style={{ minHeight: 0 }}>
          {/* Square viewfinder — fixed 1:1, centered */}
          <div
            className="relative"
            style={{
              marginTop: "auto",
              marginBottom: "auto",
              width: "100%",
              aspectRatio: "1 / 1",
              borderRadius: 24,
              border: "1px solid rgba(244,240,222,0.18)",
              overflow: "hidden",
              background: "#000",
            }}
          >
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: status === "live" ? "block" : "none",
              }}
            />

            {status !== "live" && (
              <div
                className="absolute inset-0 flex flex-col items-center justify-center text-center px-6"
                style={{ color: "rgba(244,240,222,0.55)" }}
              >
                <Camera size={36} strokeWidth={1.4} />
                <div
                  className="mt-2"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.08em" }}
                >
                  {status === "requesting" ? "REQUESTING CAMERA…" : "CAMERA UNAVAILABLE"}
                </div>
                {status === "unavailable" && reason && (
                  <div
                    className="mt-2"
                    style={{ fontSize: 12, lineHeight: 1.4, maxWidth: 260, opacity: 0.85 }}
                  >
                    {reason}
                  </div>
                )}
              </div>
            )}

            {/* Torch toggle — only when the device supports it */}
            {status === "live" && torchSupported && (
              <button
                type="button"
                onClick={toggleTorch}
                aria-label={torchOn ? "Turn off flash" : "Turn on flash"}
                aria-pressed={torchOn}
                className="absolute flex items-center justify-center rounded-full"
                style={{
                  top: 12,
                  right: 12,
                  width: 40,
                  height: 40,
                  background: torchOn ? "var(--color-cream)" : "rgba(0,0,0,0.5)",
                  color: torchOn ? "#0A0A08" : "var(--color-cream)",
                }}
              >
                {torchOn ? <Zap size={20} /> : <ZapOff size={20} />}
              </button>
            )}
          </div>
        </div>

        <canvas ref={canvasRef} style={{ display: "none" }} />

        {/* Hidden file inputs (fallback path) */}
        <input
          ref={cameraInput}
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          style={{ display: "none" }}
        />
        <input
          ref={galleryInput}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          style={{ display: "none" }}
        />

        {/* Bottom CTAs — pinned */}
        <div
          className="shrink-0 flex flex-col gap-2.5 px-5"
          style={{ paddingTop: 8, paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 24px)" }}
        >
        {atMax ? (
          <button className="btn btn-block" style={{ background: "var(--color-cream)", color: "var(--color-olive-700)" }} disabled>
            Maximum {MAX_PHOTOS} photos
          </button>
        ) : status === "live" ? (
          <button
            className="btn btn-block"
            style={{ background: "var(--color-cream)", color: "var(--color-olive-700)" }}
            onClick={handleShutter}
            disabled={reading}
          >
            <Camera size={18} />
            {reading ? "Capturing…" : "Take a photo"}
          </button>
        ) : (
          <button
            className="btn btn-block"
            style={{ background: "var(--color-cream)", color: "var(--color-olive-700)" }}
            onClick={() => cameraInput.current?.click()}
            disabled={reading || status === "requesting"}
          >
            <Camera size={18} />
            {reading
              ? "Reading photo…"
              : status === "requesting"
                ? "Starting camera…"
                : "Take a photo"}
          </button>
        )}
        <button
          className="btn btn-block btn-ghost"
          style={{ color: "rgba(244,240,222,0.85)", height: 46, fontSize: 14 }}
          onClick={() => galleryInput.current?.click()}
          disabled={reading || atMax}
        >
          <ImagePlus size={18} />
          Choose from gallery
        </button>
        </div>
      </div>
    </Screen>
  );
}
