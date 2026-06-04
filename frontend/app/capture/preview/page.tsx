"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, MapPin, Pencil, Plus } from "lucide-react";
import { Screen } from "@/components/layout/Screen";
import { useCapture, deriveDraftMeta, MAX_PHOTOS } from "@/lib/store/capture";
import { useAuth } from "@/lib/store/auth";
import { useUploadMedia } from "@/lib/api/media";
import { useCreateDraft } from "@/lib/api/drafts";
import { useNearbyRestaurants } from "@/lib/api/restaurants";

/**
 * Preview the captured photo(s) and choose between two paths:
 *  1. Save as draft & keep eating → POST /media/upload + /drafts → /drafts/saved
 *  2. Or, write notes now →        same upload/create, then jump to
 *                                  /drafts/[id]/finish for the entry form
 */
export default function CapturePreviewPage() {
  const router = useRouter();
  const pending = useCapture((s) => s.pending);
  const coverKey = useCapture((s) => s.coverKey);
  const setCover = useCapture((s) => s.setCover);
  const clear = useCapture((s) => s.clear);
  const location = useAuth((s) => s.currentLocation);

  const upload = useUploadMedia();
  const create = useCreateDraft();
  const [submitting, setSubmitting] = useState<"draft" | "notes" | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Set once we've saved and are navigating onward, so clearing `pending`
  // doesn't trip the "empty → back to camera" guard below.
  const leaving = useRef(false);

  useEffect(() => {
    if (pending.length === 0 && !leaving.current) router.replace("/capture");
  }, [pending.length, router]);

  const cover = useMemo(
    () => pending.find((p) => p.key === coverKey) ?? pending[0],
    [pending, coverKey],
  );

  // No reverse-geocoding backend, so name the location by its nearest
  // restaurant's neighborhood — same proxy the home screen uses.
  const coverLat = cover?.lat ?? location?.lat ?? null;
  const coverLng = cover?.lng ?? location?.lng ?? null;
  const { data: nearby } = useNearbyRestaurants(coverLat, coverLng);
  const placeName = nearby?.items?.[0]?.neighborhood ?? null;

  async function submit(path: "draft" | "notes") {
    if (pending.length === 0) return;
    setError(null);
    setSubmitting(path);
    try {
      const meta = deriveDraftMeta(pending, { now: new Date(), location });
      const { uploads } = await upload.mutateAsync(
        pending.map((p) => ({
          name: p.name,
          bytes: p.bytes,
          width: p.width,
          height: p.height,
          captured_at: p.captured_at,
          lat: p.lat ?? meta.lat,
          lng: p.lng ?? meta.lng,
        })),
      );
      const coverIdx = pending.findIndex((p) => p.key === cover?.key);
      const coverMediaId = uploads[Math.max(0, coverIdx)]?.id;
      const draft = await create.mutateAsync({
        media_ids: uploads.map((u) => u.id),
        cover_media_id: coverMediaId,
        captured_at: meta.captured_at,
        lat: meta.lat,
        lng: meta.lng,
      });
      leaving.current = true;
      clear();
      if (path === "draft") router.replace(`/drafts/saved?id=${draft.id}`);
      else router.replace(`/drafts/${draft.id}/finish`);
    } catch (e) {
      leaving.current = false;
      setError(e instanceof Error ? e.message : "Couldn't save that just yet.");
    } finally {
      setSubmitting(null);
    }
  }

  if (!cover) return null;

  const capturedAt = cover.captured_at ? new Date(cover.captured_at) : new Date();
  const timeLabel = capturedAt.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  const placeLabel = placeName ?? (coverLat != null ? "Around you" : "Location off");

  return (
    <Screen bg="#0A0A08">
      <div className="absolute inset-0 flex flex-col" style={{ color: "var(--color-cream)" }}>
        {/* Header — back button + board on one line, hugging the left edge */}
        <div
          className="shrink-0 px-5 flex items-center gap-2.5"
          style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 16px)" }}
        >
          <Link
            href="/capture"
            aria-label="Back"
            className="flex items-center justify-center rounded-full shrink-0"
            style={{ width: 40, height: 40, background: "rgba(0,0,0,0.5)" }}
          >
            <ChevronLeft size={22} />
          </Link>
          {/* "We'll remember the rest" board, beside the back button */}
          <div
            className="flex-1 min-w-0"
            style={{ background: "rgba(244,240,222,0.07)", borderRadius: 12, padding: 14 }}
          >
            <div className="flex justify-between items-baseline gap-2">
              <div style={{ fontSize: 12, fontFamily: "var(--font-mono)", opacity: 0.7 }}>
                WE&apos;LL REMEMBER THE REST
              </div>
              <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", opacity: 0.7 }}>
                {timeLabel}
              </div>
            </div>
            <div
              className="flex items-center gap-1.5"
              style={{ marginTop: 8, fontSize: 14, opacity: 0.92 }}
            >
              <MapPin size={15} style={{ opacity: 0.8, flexShrink: 0 }} />
              {placeLabel}
            </div>
          </div>
        </div>

        {/* Scrollable content — square photo centered in the remaining space */}
        <div className="flex-1 overflow-y-auto px-5 flex flex-col" style={{ minHeight: 0 }}>
          {/* Square photo + thumbnails — centered */}
          <div style={{ marginTop: "auto", marginBottom: "auto", width: "100%" }}>
          {/* Square photo — never stretched */}
          <div
            style={{
              width: "100%",
              aspectRatio: "1 / 1",
              borderRadius: 24,
              overflow: "hidden",
              background: "#000",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={cover.dataUrl}
              alt={cover.name}
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            />
          </div>

          {/* Thumbnail strip if multiple */}
          {pending.length > 1 && (
            <div
              style={{
                marginTop: 12,
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
          </div>
        </div>

        {/* Bottom action sheet — pinned */}
        <div
          className="shrink-0"
          style={{
            padding: "14px 20px",
            paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 24px)",
            borderTop: "1px solid rgba(244,240,222,0.08)",
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
        <div className="flex justify-between items-center">
          <Link
            href={`/capture?retake=${encodeURIComponent(cover.key)}`}
            style={{ fontSize: 13.5, color: "rgba(244,240,222,0.7)" }}
          >
            ← Retake
          </Link>
          <div
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              opacity: 0.5,
            }}
          >
            {pending.length} {pending.length === 1 ? "photo" : "photos"}
          </div>
          {pending.length < MAX_PHOTOS ? (
            <Link
              href="/capture?add=1"
              aria-label="Add another photo"
              className="flex items-center gap-1"
              style={{ fontSize: 13.5, color: "var(--color-cream)" }}
            >
              <Plus size={16} /> Add
            </Link>
          ) : (
            <span style={{ fontSize: 13, opacity: 0.4 }}>Max {MAX_PHOTOS}</span>
          )}
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
      </div>
    </Screen>
  );
}
