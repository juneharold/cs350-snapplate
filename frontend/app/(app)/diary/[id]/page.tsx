"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft, MapPin } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";
import { useEntry } from "@/lib/api/entries";

/**
 * Diary entry detail.
 *
 * Phase-4 scope: cover photo, captured-at line, restaurant + signature
 * dish, rating, the verbatim note, and a small map placeholder. The
 * "you've been here" carousel + edit / share actions land in phase 6.
 */
export default function DiaryDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: entry, isLoading } = useEntry(id);

  if (isLoading || !entry) {
    return (
      <div className="px-4 pt-16" style={{ color: "var(--color-muted)" }}>
        Loading…
      </div>
    );
  }

  const cover = entry.media.find((m) => m.is_cover) ?? entry.media[0];
  const captured = new Date(entry.captured_at).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div className="pb-12">
      <div className="relative">
        {cover?.url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover.url}
            alt={entry.restaurant.name}
            style={{ width: "100%", height: 320, objectFit: "cover", display: "block" }}
          />
        ) : (
          <FoodPlaceholder
            tone={cover?.tone}
            label={entry.restaurant.signature_dish ?? cover?.label}
            width="100%"
            height={320}
            radius={0}
          />
        )}
        <div
          className="absolute left-4 right-4 flex justify-between"
          style={{ top: "calc(env(safe-area-inset-top, 0px) + 24px)" }}
        >
          <Link
            href="/diary"
            aria-label="Back"
            className="flex items-center justify-center rounded-full"
            style={{
              width: 40,
              height: 40,
              background: "rgba(255,255,255,0.85)",
              backdropFilter: "blur(10px)",
              color: "var(--color-ink)",
            }}
          >
            <ChevronLeft size={22} />
          </Link>
        </div>
        {entry.media.length > 1 && (
          <div
            className="absolute flex gap-1.5 justify-center"
            style={{ bottom: 16, left: 0, right: 0 }}
          >
            {entry.media.map((m, i) => (
              <span
                key={m.id}
                style={{
                  width: i === 0 ? 22 : 6,
                  height: 6,
                  borderRadius: 3,
                  background: i === 0 ? "var(--color-cream)" : "rgba(255,255,255,0.5)",
                }}
              />
            ))}
          </div>
        )}
      </div>

      <div className="px-4 pt-5">
        <div
          style={{
            fontSize: 12,
            color: "var(--color-muted)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.06em",
            marginBottom: 8,
          }}
        >
          {captured.toUpperCase()}
          {entry.meal_period ? ` · ${entry.meal_period.toUpperCase()}` : ""}
        </div>
        <h1 className="leading-tight font-normal" style={{ fontSize: 28 }}>
          {entry.restaurant.name}
        </h1>
        <div className="mt-1" style={{ fontSize: 13, color: "var(--color-muted)" }}>
          {entry.restaurant.signature_dish
            ? `${entry.restaurant.signature_dish} · ${entry.restaurant.category}`
            : entry.restaurant.category}
        </div>
        <div className="flex items-center gap-3 mt-4">
          {entry.rating != null ? (
            <>
              <StarRow value={entry.rating} size={18} />
              <span
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: 22,
                  fontWeight: 500,
                }}
              >
                {entry.rating.toFixed(1)}
              </span>
            </>
          ) : (
            <span
              className="chip"
              style={{ fontSize: 11.5, color: "var(--color-muted)" }}
            >
              no rating
            </span>
          )}
          {entry.ai_tags.length > 0 && (
            <>
              <div
                style={{
                  width: 1,
                  height: 18,
                  background: "var(--color-border-soft)",
                }}
              />
              {entry.ai_tags.map((t) => (
                <span key={t} className="chip" style={{ height: 26, fontSize: 11.5 }}>
                  {t}
                </span>
              ))}
            </>
          )}
        </div>
      </div>

      <div className="px-4 pt-3">
        <p
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 18,
            lineHeight: 1.5,
            color: "var(--color-ink-2)",
            fontStyle: "italic",
          }}
        >
          “{entry.note}”
        </p>
      </div>

      <div className="px-4 pt-5">
        <h2
          className="leading-tight mb-2"
          style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500 }}
        >
          Where
        </h2>
        <div className="card flex items-center justify-between" style={{ padding: 14 }}>
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="flex items-center justify-center shrink-0"
              style={{ color: "var(--color-olive-700)" }}
            >
              <MapPin size={20} />
            </div>
            <div className="min-w-0">
              <div
                className="truncate"
                style={{ fontSize: 14, fontWeight: 600 }}
              >
                {entry.restaurant.name}
              </div>
              <div
                className="truncate"
                style={{ fontSize: 11.5, color: "var(--color-muted)" }}
              >
                {entry.restaurant.neighborhood}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
