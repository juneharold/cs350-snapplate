"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft, Bookmark, BookmarkCheck, Clock, MapPin, Phone, Footprints, Sparkles, BookOpen } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";
import { useRestaurant, useToggleBookmark } from "@/lib/api/restaurants";

/**
 * Restaurant detail.
 *
 * Phase 7 scope: hero photo, name + category + price, rating row,
 * personalization blurb (when available), info rows, popular dishes,
 * sticky bottom CTAs. Multi-photo carousel + map embed land later;
 * the prototype's design uses a placeholder map and we follow suit.
 */
export default function RestaurantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: r, isLoading } = useRestaurant(id);
  const toggle = useToggleBookmark();

  if (isLoading || !r) {
    return (
      <div className="px-6 pt-16" style={{ color: "var(--color-muted)" }}>
        Loading…
      </div>
    );
  }

  return (
    <div className="pb-32">
      <div className="relative">
        <FoodPlaceholder
          tone={r.thumbnail_tone}
          label={r.signature_dish ?? r.thumbnail_label}
          width="100%"
          height={320}
          radius={0}
        />
        <div
          className="absolute left-4 right-4 flex justify-between"
          style={{ top: "calc(env(safe-area-inset-top, 0px) + 24px)" }}
        >
          <Link
            href="/"
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
          <button
            type="button"
            aria-label={r.is_bookmarked ? "Remove bookmark" : "Save"}
            disabled={toggle.isPending}
            onClick={() =>
              toggle.mutate({ restaurantId: r.id, next: !r.is_bookmarked })
            }
            className="flex items-center justify-center rounded-full"
            style={{
              width: 40,
              height: 40,
              background: "rgba(255,255,255,0.85)",
              backdropFilter: "blur(10px)",
              color: r.is_bookmarked
                ? "var(--color-olive-700)"
                : "var(--color-ink)",
            }}
          >
            {r.is_bookmarked ? (
              <BookmarkCheck size={20} strokeWidth={1.8} />
            ) : (
              <Bookmark size={20} strokeWidth={1.8} />
            )}
          </button>
        </div>
      </div>

      <div className="px-6 pt-5">
        <div className="flex justify-between items-baseline gap-3">
          <h1 className="leading-tight font-normal flex-1" style={{ fontSize: 28 }}>
            {r.name}
          </h1>
          {r.tags[0] && (
            <span className="chip" style={{ height: 24, fontSize: 11 }}>
              {r.tags[0]}
            </span>
          )}
        </div>
        <div className="mt-1.5" style={{ fontSize: 13, color: "var(--color-muted)" }}>
          {r.signature_dish ? `${r.signature_dish} · ` : ""}
          {r.category} · {r.price_range}
        </div>
        <div className="flex items-center gap-3 mt-3.5">
          <StarRow value={r.rating} size={14} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>{r.rating.toFixed(1)}</span>
          <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
            ({r.rating_count.toLocaleString()})
          </span>
        </div>

        {r.personalization.reason && (
          <div
            className="flex gap-3 mt-4"
            style={{
              padding: 14,
              background: "var(--color-olive-100)",
              borderRadius: 14,
              color: "var(--color-olive-900)",
            }}
          >
            <span style={{ color: "var(--color-olive-700)", flexShrink: 0 }}>
              <Sparkles size={18} />
            </span>
            <div style={{ fontSize: 12.5, lineHeight: 1.5 }}>
              <b>Why this is for you</b> — {r.personalization.reason}
            </div>
          </div>
        )}
      </div>

      <section className="px-6 mt-6">
        <h2
          className="leading-tight mb-2"
          style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500 }}
        >
          Info
        </h2>
        <div className="card" style={{ padding: 0 }}>
          <InfoRow Icon={MapPin} label={r.address} />
          <InfoRow Icon={Clock} label={r.hours} />
          {r.distance_m > 0 && (
            <InfoRow
              Icon={Footprints}
              label={`${Math.round(r.distance_m)}m from you`}
            />
          )}
          <InfoRow Icon={Phone} label={r.phone} />
        </div>
      </section>

      {r.popular_dishes.length > 0 && (
        <section className="px-6 mt-6">
          <h2
            className="leading-tight mb-2"
            style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500 }}
          >
            Popular dishes
          </h2>
          <div className="flex gap-2.5" style={{ overflowX: "auto" }}>
            {r.popular_dishes.map((d) => (
              <div key={d.name} style={{ width: 110, flexShrink: 0 }}>
                <FoodPlaceholder
                  tone={d.tone}
                  label={d.name}
                  width={110}
                  height={110}
                  radius={12}
                />
                <div className="mt-2" style={{ fontSize: 12.5, fontWeight: 500 }}>
                  {d.name}
                </div>
                <div style={{ fontSize: 11, color: "var(--color-muted)" }}>
                  {d.price}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex gap-2 px-6 mt-8">
        <Link
          href="/capture"
          className="btn btn-secondary"
          style={{ flex: 1 }}
        >
          <BookOpen size={18} />
          Log a meal
        </Link>
        <a
          href={r.kakao_place_url}
          target="_blank"
          rel="noreferrer"
          className="btn"
          style={{ flex: 1 }}
        >
          <MapPin size={18} />
          Open in Kakao
        </a>
      </div>
    </div>
  );
}

function InfoRow({
  Icon,
  label,
}: {
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number; style?: React.CSSProperties }>;
  label: string;
}) {
  return (
    <div
      className="flex items-center gap-3"
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--color-border-soft)",
      }}
    >
      <Icon size={18} style={{ color: "var(--color-muted)", flexShrink: 0 }} />
      <span style={{ fontSize: 13.5 }}>{label}</span>
    </div>
  );
}
