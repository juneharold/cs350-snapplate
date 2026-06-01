"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronLeft, Search, BookmarkX } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";
import { useBookmarks, useToggleBookmark } from "@/lib/api/restaurants";

/**
 * Bookmarks sub-screen — reached from the Me tab. MVP scope: a single
 * "All" collection with search-within-saved. Multi-collection support
 * (Date nights, Quick lunch…) is intentionally deferred per the build
 * spec.
 */
export default function SavedPage() {
  const [q, setQ] = useState("");
  const { data, isLoading } = useBookmarks(q);
  const toggle = useToggleBookmark();
  const items = data?.items ?? [];

  return (
    <div className="pb-12">
      <header
        className="px-4"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 24px)" }}
      >
        <div className="flex items-center gap-2">
          <Link
            href="/me"
            aria-label="Back"
            className="flex items-center justify-center"
            style={{ width: 40, height: 40, color: "var(--color-ink)" }}
          >
            <ChevronLeft size={22} />
          </Link>
          <div className="flex-1" />
        </div>
      </header>

      <div className="px-4 mt-1">
        <div
          style={{
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            color: "var(--color-muted)",
            letterSpacing: "0.06em",
          }}
        >
          YOUR PLACES
        </div>
        <h1
          className="leading-tight font-normal mt-0.5"
          style={{ fontSize: 30 }}
        >
          Saved
        </h1>
        <div
          className="mt-1"
          style={{
            fontSize: 12,
            color: "var(--color-muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {isLoading
            ? "Loading…"
            : `${data?.total ?? items.length} place${(data?.total ?? items.length) === 1 ? "" : "s"}`}
        </div>

        <div className="relative mt-4 mb-3">
          <span
            className="absolute"
            style={{
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--color-muted)",
            }}
          >
            <Search size={16} />
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search saved"
            className="input input-search"
            style={{ paddingLeft: 42, height: 40, fontSize: 13 }}
          />
        </div>

        {items.length === 0 && !isLoading && (
          <div
            className="card p-6 text-center"
            style={{ color: "var(--color-muted)" }}
          >
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 18,
                color: "var(--color-ink)",
              }}
            >
              {q ? "No matches" : "Nothing saved yet."}
            </div>
            {!q && (
              <p className="mt-2" style={{ fontSize: 13 }}>
                Bookmark places from the restaurant detail screen and they&apos;ll
                land here.
              </p>
            )}
          </div>
        )}

        {items.length > 0 && (
          <div className="list-group">
          {items.map((b) => (
            <div
              key={b.id}
              className="flex gap-3 p-3 items-center"
            >
              <Link
                href={`/restaurants/${b.restaurant_id}`}
                className="flex gap-3 items-center flex-1 min-w-0"
              >
                <FoodPlaceholder
                  tone={b.restaurant.thumbnail_tone}
                  label={b.restaurant.signature_dish ?? b.restaurant.thumbnail_label}
                  width={68}
                  height={68}
                  radius={12}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2">
                    <div
                      className="truncate"
                      style={{
                        fontFamily: "var(--font-serif)",
                        fontSize: 16,
                        fontWeight: 500,
                      }}
                    >
                      {b.restaurant.name}
                    </div>
                    <div
                      className="shrink-0"
                      style={{
                        fontSize: 10.5,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-muted)",
                      }}
                    >
                      {b.restaurant.distance_m}m
                    </div>
                  </div>
                  <div
                    className="truncate mt-0.5"
                    style={{ fontSize: 12, color: "var(--color-muted)" }}
                  >
                    {b.restaurant.signature_dish ?? b.restaurant.category} ·{" "}
                    {b.restaurant.neighborhood}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <StarRow value={b.restaurant.rating} size={12} />
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 10.5,
                        color: "var(--color-muted)",
                      }}
                    >
                      {b.restaurant.rating.toFixed(1)}
                    </span>
                  </div>
                </div>
              </Link>
              <button
                type="button"
                aria-label="Remove bookmark"
                onClick={() =>
                  toggle.mutate({
                    restaurantId: b.restaurant_id,
                    next: false,
                  })
                }
                disabled={toggle.isPending}
                style={{
                  color: "var(--color-muted)",
                  width: 36,
                  height: 36,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <BookmarkX size={18} />
              </button>
            </div>
          ))}
          </div>
        )}
      </div>
    </div>
  );
}
