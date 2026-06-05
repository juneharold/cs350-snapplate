"use client";

import { useEffect, useMemo, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Clock, Pencil } from "lucide-react";
import { Screen } from "@/components/layout/Screen";
import { useCapture, deriveDraftMeta } from "@/lib/store/capture";
import { useAuth } from "@/lib/store/auth";
import { useUploadMedia } from "@/lib/api/media";
import { useCreateDraft } from "@/lib/api/drafts";

/**
 * Preview the captured photo(s) and choose between two paths:
 *  1. Save as draft & keep eating → POST /media/upload + /drafts → /drafts/saved
 *  2. Or, write notes now →        same upload/create, then jump to
 *                                  /drafts/[id]/finish for the entry form
 */
function CapturePreviewContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const restaurantId = searchParams.get("restaurant_id");
  // Carry the restaurant selection back to /capture on every exit (reload
  // redirect, Back, Retake) so it survives the round trip, mirroring the
  // forward navigation in capture/page.tsx.
  const captureHref = restaurantId ? `/capture?restaurant_id=${restaurantId}` : "/capture";
  const pending = useCapture((s) => s.pending);
  const coverKey = useCapture((s) => s.coverKey);
  const setCover = useCapture((s) => s.setCover);
  const clear = useCapture((s) => s.clear);
  const location = useAuth((s) => s.currentLocation);

  const upload = useUploadMedia();
  const create = useCreateDraft();
  const [submitting, setSubmitting] = useState<"draft" | "notes" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && pending.length === 0) {
      router.replace(captureHref);
    }
    // Intentionally omit `pending.length`. If included, submit()'s clear()
    // would re-fire this effect after upload and race the router.replace()
    // into /drafts/[id]/finish, bouncing the user back to /capture.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, router]);

  const cover = useMemo(
    () => pending.find((p) => p.key === coverKey) ?? pending[0],
    [pending, coverKey],
  );

  async function submit(path: "draft" | "notes") {
    if (pending.length === 0) return;
    setError(null);
    setSubmitting(path);
    try {
      const meta = deriveDraftMeta(pending, { now: new Date(), location });
      // Send the raw File bytes as multipart; the backend reads EXIF + makes variants.
      const { uploads } = await upload.mutateAsync(pending.map((p) => p.file));
      const coverIdx = pending.findIndex((p) => p.key === cover?.key);
      const coverMediaId = uploads[Math.max(0, coverIdx)]?.id;
      const draft = await create.mutateAsync({
        media_ids: uploads.map((u) => u.id),
        cover_media_id: coverMediaId,
        captured_at: meta.captured_at,
        lat: meta.lat,
        lng: meta.lng,
        restaurant_id: restaurantId,
        restaurant_suggested: false,
      });
      clear();
      if (path === "draft") router.replace(`/drafts/saved?id=${draft.id}`);
      else router.replace(`/drafts/${draft.id}/finish`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save that just yet.");
    } finally {
      setSubmitting(null);
    }
  }

  if (!mounted) return null;
  if (!cover) return null;

  const detected = cover.lat != null && cover.lng != null
    ? `${cover.lat.toFixed(4)}°N ${cover.lng.toFixed(4)}°E`
    : location
      ? `${location.lat.toFixed(4)}°N ${location.lng.toFixed(4)}°E (device)`
      : "Location not available";

  return (
    <Screen bg="#0A0A08">
      {/* Top */}
      <div
        className="absolute left-4 right-4 flex items-center justify-between"
        style={{ top: "calc(env(safe-area-inset-top, 0px) + 24px)", color: "var(--color-cream)" }}
      >
        <Link
          href={captureHref}
          aria-label="Back"
          className="flex items-center justify-center rounded-full"
          style={{ width: 40, height: 40, background: "rgba(0,0,0,0.5)" }}
        >
          <ChevronLeft size={22} />
        </Link>
        <div
          style={{
            background: "rgba(0,0,0,0.5)",
            padding: "6px 14px",
            borderRadius: 999,
            fontSize: 11,
            fontFamily: "var(--font-mono)",
          }}
        >
          PREVIEW · 1 OF {pending.length}
        </div>
        <div style={{ width: 40, height: 40 }} />
      </div>

      {/* Cover */}
      <div
        className="absolute left-0 right-0"
        style={{ top: 0, bottom: 280, background: "#0A0A08" }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={cover.dataUrl}
          alt={cover.name}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      </div>

      {/* Thumbnail strip if multiple */}
      {pending.length > 1 && (
        <div
          className="absolute"
          style={{
            left: 16,
            right: 16,
            bottom: 410,
            display: "flex",
            gap: 6,
            overflowX: "auto",
            padding: "4px 2px",
          }}
        >
          {pending.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => setCover(p.key)}
              aria-label={`Cover: ${p.name}`}
              style={{
                width: 56,
                height: 56,
                flexShrink: 0,
                borderRadius: 10,
                overflow: "hidden",
                border:
                  p.key === cover.key
                    ? "2px solid var(--color-cream)"
                    : "2px solid transparent",
                opacity: p.key === cover.key ? 1 : 0.75,
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={p.dataUrl}
                alt=""
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </button>
          ))}
        </div>
      )}

      {/* Metadata card */}
      <div
        className="absolute"
        style={{
          left: 16,
          right: 16,
          bottom: 300,
          background: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
          borderRadius: 10,
          padding: 14,
          color: "var(--color-cream)",
        }}
      >
        <div className="flex justify-between items-baseline">
          <div
            style={{
              fontSize: 12,
              fontFamily: "var(--font-mono)",
              opacity: 0.7,
            }}
          >
            WE&apos;LL REMEMBER THE REST
          </div>
          <div
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              opacity: 0.7,
            }}
          >
            {new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
          </div>
        </div>
        <div style={{ marginTop: 6, fontSize: 13.5 }}>
          <span style={{ opacity: 0.92 }}>EXIF · location</span>
          <div style={{ marginTop: 2, opacity: 0.65, fontFamily: "var(--font-mono)", fontSize: 11 }}>
            {detected}
          </div>
        </div>
      </div>

      {/* Bottom action sheet */}
      <div
        className="absolute left-0 right-0"
        style={{
          bottom: 0,
          height: 280,
          background: "#0A0A08",
          borderRadius: "24px 24px 0 0",
          padding: "22px 20px 40px",
          color: "var(--color-cream)",
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <div className="flex justify-between items-center">
          <Link href={captureHref} style={{ fontSize: 13.5, color: "rgba(244,240,222,0.7)" }}>
            ← Retake
          </Link>
          <div
            style={{
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              opacity: 0.5,
            }}
          >
            {cover.width}×{cover.height} · {(cover.bytes / (1024 * 1024)).toFixed(1)} MB
          </div>
          <div style={{ fontSize: 13.5, opacity: 0.55 }}>+{pending.length - 1 > 0 ? ` ${pending.length - 1}` : ""}</div>
        </div>

        <div
          style={{
            background: "rgba(244,240,222,0.07)",
            borderRadius: 12,
            padding: 12,
            fontSize: 12,
            lineHeight: 1.45,
            color: "rgba(244,240,222,0.78)",
            display: "flex",
            gap: 10,
          }}
        >
          <span style={{ color: "#F4E37A", flexShrink: 0, marginTop: 1 }}>
            <Clock size={16} />
          </span>
          <div>
            <b style={{ color: "var(--color-cream)" }}>Eat first, log later.</b>{" "}
            We&apos;ll save the photo and ping you in about an hour to add your
            rating.
          </div>
        </div>

        {error && (
          <div style={{ fontSize: 13, color: "var(--color-danger)" }}>{error}</div>
        )}

        <button
          className="btn btn-block"
          style={{ background: "var(--color-cream)", color: "var(--color-olive-700)" }}
          disabled={!!submitting}
          onClick={() => submit("draft")}
        >
          {submitting === "draft" ? "Saving…" : "Save as draft & keep eating"}
        </button>
        <button
          className="btn btn-block btn-ghost"
          style={{ color: "rgba(244,240,222,0.7)", height: 36, fontSize: 13 }}
          disabled={!!submitting}
          onClick={() => submit("notes")}
        >
          <Pencil size={14} />
          {submitting === "notes" ? "Saving…" : "Or, write notes now →"}
        </button>
      </div>
    </Screen>
  );
}

export default function CapturePreviewPage() {
  return (
    <Suspense fallback={null}>
      <CapturePreviewContent />
    </Suspense>
  );
}
