"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Clock, MapPin, Check } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Screen } from "@/components/layout/Screen";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarPicker } from "@/components/ui/StarRating";
import { useDraft, useFinalizeDraft, useUpdateDraft } from "@/lib/api/drafts";
import { useNearbyRestaurants } from "@/lib/api/restaurants";
import { useToast } from "@/lib/store/toast";
import { useAuth, FALLBACK_LOCATION } from "@/lib/store/auth";
import { ApiException } from "@/lib/api/client";

/**
 * The unified entry form.
 *
 * Reached from two paths:
 *  • "Write notes now" right after capture (`/capture/preview`)
 *  • Tapping a draft in /drafts or the home dock
 *
 * Same fields in both cases:
 *  • note      — REQUIRED, 1–500 chars
 *  • rating    — OPTIONAL, 0.5–5.0 in 0.5 steps
 *  • restaurant — pre-filled from GPS; can be changed via the picker
 *
 * No tags input — server generates `ai_tags` from the note.
 */

const schema = z.object({
  note: z.string().trim().min(1, "Drop at least a sentence — it can be tiny.").max(500),
  rating: z.number().min(0).max(5).optional(),
  restaurant_id: z.string().min(1, "Pick a restaurant."),
});
type FormValues = z.infer<typeof schema>;

export default function FinishDraftPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const showToast = useToast((s) => s.show);
  const { data: draft, isLoading } = useDraft(id);
  const finalize = useFinalizeDraft(id);
  const updateDraft = useUpdateDraft(id);
  const location = useAuth((s) => s.currentLocation) ?? FALLBACK_LOCATION;
  const { data: nearby } = useNearbyRestaurants(location.lat, location.lng);
  const [showPicker, setShowPicker] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { note: "", rating: undefined, restaurant_id: "" },
    mode: "onChange",
  });
  const { register, handleSubmit, setValue, watch, formState, setError, reset } = form;

  // Hydrate the form when the draft loads — keeps restaurant_id in sync
  // if the user updates the draft via the picker.
  useEffect(() => {
    if (!draft) return;
    reset({
      note: watch("note") ?? "",
      rating: watch("rating"),
      restaurant_id: draft.restaurant?.id ?? "",
    });
    // We only want this on draft load, not every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft?.id, draft?.restaurant?.id]);

  const note = watch("note") ?? "";
  const rating = watch("rating");
  const restaurantId = watch("restaurant_id");

  const cover = draft?.media.find((m) => m.is_cover) ?? draft?.media[0];

  const capturedAt = draft
    ? new Date(draft.captured_at).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : "";

  const onSubmit = handleSubmit(async (values) => {
    try {
      await finalize.mutateAsync({
        note: values.note.trim(),
        rating: values.rating && values.rating > 0 ? values.rating : undefined,
        restaurant_id: values.restaurant_id,
      });
      showToast("Saved to your diary");
      router.replace("/diary");
    } catch (e) {
      const msg = e instanceof ApiException ? e.message : "Couldn't save just yet.";
      setError("root", { message: msg });
    }
  });

  async function pickRestaurant(rid: string) {
    setShowPicker(false);
    if (!draft) return;
    setValue("restaurant_id", rid, { shouldValidate: true, shouldDirty: true });
    try {
      await updateDraft.mutateAsync({ restaurant_id: rid });
    } catch {
      // The local form value is still correct; finalize will validate
      // server-side. Surface failures only if finalize itself errors.
    }
  }

  if (isLoading || !draft) {
    return (
      <Screen>
        <div className="px-7 pt-24" style={{ color: "var(--color-muted)" }}>
          Loading draft…
        </div>
      </Screen>
    );
  }

  const selectedRestaurant =
    nearby?.items.find((r) => r.id === restaurantId) ??
    (draft.restaurant ? { ...draft.restaurant, thumbnail_tone: draft.media[0]?.tone ?? "ochre" } : null);

  return (
    <Screen>
      {/* Sticky header */}
      <header
        className="absolute left-0 right-0 flex items-center justify-between px-4 z-20"
        style={{
          top: 0,
          paddingTop: "calc(env(safe-area-inset-top, 0px) + 36px)",
          paddingBottom: 14,
          background: "var(--color-bg)",
          borderBottom: "1px solid var(--color-border-soft)",
        }}
      >
        <Link href="/drafts" style={{ fontSize: 14, color: "var(--color-muted)" }}>
          Cancel
        </Link>
        <div style={{ fontFamily: "var(--font-serif)", fontSize: 17, fontWeight: 500 }}>
          Entry
        </div>
        <button
          type="submit"
          form="entry-form"
          disabled={!formState.isValid || finalize.isPending}
          style={{
            fontSize: 14,
            color: formState.isValid
              ? "var(--color-olive-700)"
              : "var(--color-muted-2)",
            fontWeight: 600,
          }}
        >
          {finalize.isPending ? "Saving…" : "Save"}
        </button>
      </header>

      <form
        id="entry-form"
        onSubmit={onSubmit}
        className="absolute inset-x-0"
        style={{
          top: "calc(env(safe-area-inset-top, 0px) + 88px)",
          bottom: 0,
          overflowY: "auto",
          padding: "16px 22px 40px",
        }}
      >
        {/* Captured-a-while-ago banner shown only when reached from a draft */}
        <div
          className="flex items-center gap-2 mb-3"
          style={{
            background: "var(--color-bg-soft)",
            border: "1px solid var(--color-border-soft)",
            color: "var(--color-ink-2)",
            padding: "10px 12px",
            borderRadius: 12,
            fontSize: 12.5,
          }}
        >
          <Clock size={14} style={{ color: "var(--color-olive-700)" }} />
          <span>
            Captured{" "}
            <b>
              {new Date(draft.captured_at).toLocaleTimeString("en-US", {
                hour: "numeric",
                minute: "2-digit",
              })}
            </b>{" "}
            — how was it?
          </span>
        </div>

        {/* Photo strip */}
        <div className="flex gap-2 overflow-x-auto mb-4">
          {draft.media.map((m, i) => (
            <div key={m.id} className="relative shrink-0">
              <FoodPlaceholder
                src={m.thumbnail_url}
                tone={m.tone}
                label={m.label}
                alt={`Photo ${i + 1} of ${draft.media.length}${m.is_cover ? " (cover)" : ""}`}
                width={104}
                height={104}
                radius={14}
              />
              {m.is_cover && (
                <span
                  style={{
                    position: "absolute",
                    top: 6,
                    left: 6,
                    padding: "3px 6px",
                    borderRadius: 4,
                    background: "rgba(0,0,0,0.6)",
                    color: "var(--color-cream)",
                    fontSize: 9,
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  COVER
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Note — REQUIRED */}
        <section className="mb-4">
          <div className="flex justify-between items-baseline mb-2.5">
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              NOTE
              <span style={{ color: "var(--color-danger)", marginLeft: 4 }}>*</span>
            </div>
            <div
              style={{
                fontSize: 10.5,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted-2)",
              }}
            >
              {note.length} / 500
            </div>
          </div>
          <textarea
            {...register("note")}
            className="textarea"
            maxLength={500}
            style={{ minHeight: 120 }}
            placeholder="A sentence is enough — even just 'good' works. We use this to learn your taste."
          />
          {formState.errors.note && (
            <div
              className="mt-1.5"
              style={{ fontSize: 11.5, color: "var(--color-danger)" }}
            >
              {formState.errors.note.message}
            </div>
          )}
        </section>

        {/* Rating — OPTIONAL */}
        <section className="mb-4">
          <div className="flex justify-between items-baseline mb-2.5">
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              RATING
            </div>
            <div
              style={{
                fontSize: 10.5,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted-2)",
              }}
            >
              optional
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StarPicker
              value={rating ?? 0}
              onChange={(v) => setValue("rating", v > 0 ? v : undefined, { shouldDirty: true })}
              size={32}
            />
            <span
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 20,
                color: "var(--color-ink)",
              }}
            >
              {rating ? rating.toFixed(1) : "—"}
            </span>
          </div>
        </section>

        {/* Restaurant */}
        <section className="mb-4">
          <div
            className="mb-2.5"
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
              letterSpacing: "0.06em",
            }}
          >
            RESTAURANT{" "}
            <span style={{ color: "var(--color-danger)", marginLeft: 4 }}>*</span>
          </div>
          {selectedRestaurant ? (
            <div className="card flex items-center gap-3" style={{ padding: 14 }}>
              <FoodPlaceholder
                tone={selectedRestaurant.thumbnail_tone}
                label=""
                width={44}
                height={44}
                radius={10}
              />
              <div className="flex-1 min-w-0">
                <div
                  className="truncate"
                  style={{
                    fontSize: 14.5,
                    fontWeight: 600,
                    fontFamily: "var(--font-serif)",
                  }}
                >
                  {selectedRestaurant.name}
                </div>
                <div
                  className="truncate"
                  style={{ fontSize: 11.5, color: "var(--color-muted)" }}
                >
                  {`${selectedRestaurant.neighborhood}${
                    draft.restaurant_suggested && draft.restaurant?.id === selectedRestaurant.id
                      ? " · suggested from GPS"
                      : ""
                  }`}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowPicker(true)}
                style={{
                  color: "var(--color-olive-700)",
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                Change
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowPicker(true)}
              className="btn btn-secondary btn-block"
            >
              Pick a restaurant
            </button>
          )}
          {formState.errors.restaurant_id && (
            <div
              className="mt-1.5"
              style={{ fontSize: 11.5, color: "var(--color-danger)" }}
            >
              {formState.errors.restaurant_id.message}
            </div>
          )}
        </section>

        {/* When & where */}
        <section className="mb-3">
          <div
            className="mb-2.5"
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
              letterSpacing: "0.06em",
            }}
          >
            WHEN &amp; WHERE
          </div>
          <div className="card" style={{ padding: 0 }}>
            <div className="flex items-center gap-3" style={{ padding: "14px 16px" }}>
              <Clock size={18} style={{ color: "var(--color-muted)" }} />
              <div className="flex-1">
                <div style={{ fontSize: 13.5 }}>{capturedAt}</div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--color-muted)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  auto from photo
                </div>
              </div>
            </div>
            <div
              className="flex items-center gap-3"
              style={{ padding: "14px 16px", borderTop: "1px solid var(--color-border-soft)" }}
            >
              <MapPin size={18} style={{ color: "var(--color-muted)" }} />
              <div className="flex-1 min-w-0">
                <div className="truncate" style={{ fontSize: 13.5 }}>
                  {`${selectedRestaurant?.neighborhood ?? "Unknown"} · ${selectedRestaurant?.name ?? "—"}`}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--color-muted)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {draft.lat != null && draft.lng != null
                    ? `${draft.lat.toFixed(4)}°N ${draft.lng.toFixed(4)}°E`
                    : "no GPS"}
                </div>
              </div>
            </div>
          </div>
        </section>

        <div
          className="flex items-center gap-2.5"
          style={{ fontSize: 11.5, color: "var(--color-muted)" }}
        >
          <span
            className="flex items-center justify-center"
            style={{
              width: 16,
              height: 16,
              borderRadius: 4,
              background: "var(--color-olive-700)",
              color: "var(--color-cream)",
            }}
          >
            <Check size={11} strokeWidth={2.4} />
          </span>
          Private to you — never shared.
        </div>

        {formState.errors.root && (
          <div
            className="mt-4"
            style={{ fontSize: 13, color: "var(--color-danger)" }}
          >
            {formState.errors.root.message}
          </div>
        )}
      </form>

      {/* Restaurant picker sheet */}
      {showPicker && (
        <div
          className="fixed inset-0 z-[60] flex flex-col"
          style={{ background: "rgba(0,0,0,0.45)" }}
          onClick={() => setShowPicker(false)}
        >
          <div className="flex-1" />
          <div
            className="card"
            style={{
              borderRadius: "20px 20px 0 0",
              padding: 18,
              background: "var(--color-bg)",
              maxHeight: "70%",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-2">
              <div style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500 }}>
                Pick a restaurant
              </div>
              <button
                type="button"
                onClick={() => setShowPicker(false)}
                style={{ color: "var(--color-muted)", fontSize: 14 }}
              >
                Close
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {(nearby?.items ?? []).map((r) => {
                const selected = r.id === restaurantId;
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => pickRestaurant(r.id)}
                    className="card flex items-center gap-3 text-left"
                    style={{
                      padding: 12,
                      borderColor: selected
                        ? "var(--color-olive-700)"
                        : "var(--color-border-soft)",
                    }}
                  >
                    <FoodPlaceholder
                      tone={r.thumbnail_tone}
                      label=""
                      width={40}
                      height={40}
                      radius={10}
                    />
                    <div className="flex-1 min-w-0">
                      <div
                        className="truncate"
                        style={{ fontFamily: "var(--font-serif)", fontSize: 15, fontWeight: 500 }}
                      >
                        {r.name}
                      </div>
                      <div
                        className="truncate"
                        style={{ fontSize: 11.5, color: "var(--color-muted)" }}
                      >
                        {`${r.category} · ${r.neighborhood} · ${r.distance_m}m`}
                      </div>
                    </div>
                    {selected && (
                      <Check size={18} style={{ color: "var(--color-olive-700)" }} />
                    )}
                  </button>
                );
              })}
              {(nearby?.items ?? []).length === 0 && (
                <div
                  className="py-6 text-center"
                  style={{ color: "var(--color-muted)", fontSize: 13 }}
                >
                  No nearby restaurants in this build yet.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Screen>
  );
}
