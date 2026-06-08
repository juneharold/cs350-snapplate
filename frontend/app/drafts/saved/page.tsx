"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Check } from "lucide-react";
import { Screen } from "@/components/layout/Screen";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { useDraft } from "@/lib/api/drafts";

/** How long the confirmation lingers before we drop the user back home. */
const REDIRECT_DELAY_MS = 3500;

function SavedConfirm() {
  const router = useRouter();
  const params = useSearchParams();
  const draftId = params.get("id");
  const { data: draft } = useDraft(draftId);
  const cover = draft?.media.find((m) => m.is_cover) ?? draft?.media[0];

  // Auto-return home — this is a transient confirmation, not a screen to act on.
  // replace() keeps it out of history so Back doesn't bounce here.
  useEffect(() => {
    const t = setTimeout(() => router.replace("/"), REDIRECT_DELAY_MS);
    return () => clearTimeout(t);
  }, [router]);

  const remindAt = draft?.remind_at
    ? new Date(draft.remind_at).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
      })
    : null;

  return (
    <Screen bg="var(--color-olive-700)">
      <div
        className="absolute inset-0 flex flex-col items-center justify-center px-7"
        style={{ color: "var(--color-cream)" }}
      >
        {/* Checkmark with concentric rings */}
        <div className="relative mb-5" style={{ width: 140, height: 140 }}>
          <div
            className="absolute inset-0 rounded-full"
            style={{ border: "1px solid rgba(244,240,222,0.2)" }}
          />
          <div
            className="absolute rounded-full"
            style={{ inset: 16, border: "1px solid rgba(244,240,222,0.3)" }}
          />
          <div
            className="absolute rounded-full flex items-center justify-center"
            style={{
              inset: 32,
              background: "var(--color-cream)",
              color: "var(--color-olive-700)",
            }}
          >
            <Check size={42} strokeWidth={2.2} />
          </div>
        </div>

        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            letterSpacing: "0.1em",
            opacity: 0.7,
          }}
        >
          DRAFT · SAVED
        </div>
        <h1
          className="leading-tight font-normal text-center"
          style={{ fontFamily: "var(--font-serif)", fontSize: 32, marginTop: 8, marginBottom: 14 }}
        >
          Enjoy the meal.
        </h1>
        <p
          className="text-center"
          style={{ fontSize: 14, lineHeight: 1.5, opacity: 0.85, maxWidth: 280 }}
        >
          Photo saved. Place tagged.{" "}
          {remindAt ? (
            <>
              We&apos;ll nudge you around{" "}
              <b style={{ color: "var(--color-cream)" }}>{remindAt}</b> to add a
              rating and a note.
            </>
          ) : (
            <>Come back when you&apos;re done eating to add a rating and a note.</>
          )}
        </p>

        {/* Mini draft preview card */}
        {draft && (
          <div
            className="mt-5 w-full flex items-center gap-3 p-3"
            style={{
              background: "rgba(244,240,222,0.08)",
              borderRadius: 10,
              maxWidth: 320,
              border: "1px solid rgba(244,240,222,0.12)",
            }}
          >
            <FoodPlaceholder
              src={cover?.thumbnail_url}
              tone={cover?.tone}
              label={draft.restaurant?.name ?? "Meal photo"}
              width={48}
              height={48}
              radius={10}
            />
            <div className="flex-1 min-w-0">
              <div
                className="truncate"
                style={{
                  fontSize: 13.5,
                  fontWeight: 600,
                  fontFamily: "var(--font-serif)",
                }}
              >
                {draft.restaurant?.name ?? "Unknown place"}
              </div>
              <div
                style={{
                  fontSize: 11,
                  opacity: 0.65,
                  fontFamily: "var(--font-mono)",
                }}
              >
                {new Date(draft.captured_at).toLocaleTimeString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                })}{" "}
                · {draft.restaurant?.neighborhood ?? "no place"} ·{" "}
                {draft.media.length} photo
                {draft.media.length === 1 ? "" : "s"}
              </div>
            </div>
            <span
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                background: "rgba(244,240,222,0.15)",
                padding: "4px 8px",
                borderRadius: 999,
                letterSpacing: "0.04em",
              }}
            >
              {draft.status === "needs_place" ? "PICK PLACE" : "WAITING"}
            </span>
          </div>
        )}
      </div>

      <div
        className="absolute left-7 right-7 text-center"
        style={{
          bottom: "calc(env(safe-area-inset-bottom, 0px) + 36px)",
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.08em",
          opacity: 0.55,
        }}
      >
        TAKING YOU HOME…
      </div>
    </Screen>
  );
}

export default function DraftSavedPage() {
  return (
    <Suspense fallback={null}>
      <SavedConfirm />
    </Suspense>
  );
}
