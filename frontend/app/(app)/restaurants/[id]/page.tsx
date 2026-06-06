"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft, Bookmark, BookmarkCheck, MapPin, Phone, Footprints, Sparkles, BookOpen } from "lucide-react";
import { useRestaurant, useToggleBookmark } from "@/lib/api/restaurants";

/**
 * Restaurant detail.
 *
 * Image-free by design: the Kakao Local API gives us no restaurant photos
 * or business hours, so rather than show fake placeholders we lead with a
 * clean text header (name + category + neighborhood + rating) and point
 * users to Kakao for hours, photos, and menu.
 */
export default function RestaurantDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: r, isLoading } = useRestaurant(id);
  const toggle = useToggleBookmark();

  if (isLoading || !r) {
    return (
      <div className="px-4 pt-16" style={{ color: "var(--color-muted)" }}>
        Loading…
      </div>
    );
  }

  return (
    <div className="pb-32">
      <header
        className="px-4 flex items-center justify-between"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 24px)" }}
      >
        <Link
          href="/"
          aria-label="Back"
          className="flex items-center justify-center"
          style={{ width: 40, height: 40, color: "var(--color-ink)", marginLeft: -8 }}
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
            color: r.is_bookmarked ? "var(--color-olive-700)" : "var(--color-ink)",
          }}
        >
          {r.is_bookmarked ? (
            <BookmarkCheck size={20} strokeWidth={1.8} />
          ) : (
            <Bookmark size={20} strokeWidth={1.8} />
          )}
        </button>
      </header>

      <div className="px-4 pt-2">
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
          {r.category} · {r.neighborhood}
        </div>

        {r.personalization.reason && (
          <div
            className="flex gap-3 mt-4"
            style={{
              padding: 14,
              background: "var(--color-bg-soft)",
              border: "1px solid var(--color-border-soft)",
              borderRadius: 10,
              color: "var(--color-ink-2)",
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

      <section className="px-4 mt-4">
        <h2
          className="leading-tight mb-2"
          style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500 }}
        >
          Info
        </h2>
        <div className="card" style={{ padding: 0 }}>
          <InfoRow Icon={MapPin} label={r.address} />
          {r.distance_m > 0 && (
            <InfoRow
              Icon={Footprints}
              label={`${Math.round(r.distance_m)}m from you`}
            />
          )}
          {r.phone && <InfoRow Icon={Phone} label={r.phone} href={`tel:${r.phone}`} />}
        </div>
      </section>

      <div className="flex gap-2 px-4 mt-5">
        <Link
          href={`/capture?restaurant_id=${r.id}`}
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
      <p
        className="px-4 mt-2 text-center"
        style={{ fontSize: 11.5, color: "var(--color-muted-2)" }}
      >
        Hours, photos & menu on Kakao
      </p>
    </div>
  );
}

function InfoRow({
  Icon,
  label,
  href,
}: {
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number; style?: React.CSSProperties }>;
  label: string;
  href?: string;
}) {
  const Element = (href ? "a" : "div") as "a" | "div";
  return (
    <Element
      {...(href ? { href } : {})}
      className="flex items-center gap-3"
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--color-border-soft)",
        color: "inherit",
      }}
    >
      <Icon size={18} style={{ color: "var(--color-muted)", flexShrink: 0 }} />
      <span style={{ fontSize: 13.5 }}>{label}</span>
    </Element>
  );
}
