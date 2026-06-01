"use client";

import Link from "next/link";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";
import type { RecommendedResponse } from "@/lib/types";

/**
 * "For your taste" — horizontal strip of recommendations the server
 * computed from the user's logged entries. Shows nothing for users
 * with too few entries; the home page renders an empty branch for that
 * case so this component focuses on the populated state.
 */
export function RecommendedStrip({ data }: { data: RecommendedResponse }) {
  const items = data.items;
  if (items.length === 0) return null;
  return (
    <section className="mt-4">
      <div className="px-4 flex items-baseline justify-between mb-2">
        <h2
          className="leading-tight"
          style={{ fontFamily: "var(--font-serif)", fontSize: 22, fontWeight: 500 }}
        >
          For your{" "}
          <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>
            taste
          </em>
        </h2>
      </div>
      <div
        className="px-4"
        style={{ fontSize: 12, color: "var(--color-muted)", marginBottom: 10 }}
      >
        Based on {data.based_on_entries}{" "}
        {data.based_on_entries === 1 ? "entry" : "entries"}
      </div>
      <div
        className="flex gap-3.5"
        style={{ overflowX: "auto", padding: "0 16px 4px" }}
      >
        {items.map((r) => (
          <Link
            key={r.id}
            href={`/restaurants/${r.id}`}
            style={{ width: 184, flexShrink: 0 }}
          >
            <div className="card" style={{ overflow: "hidden", padding: 0 }}>
              <FoodPlaceholder
                tone={r.thumbnail_tone}
                label={r.signature_dish ?? r.thumbnail_label}
                width="100%"
                height={120}
                radius={0}
              />
              <div style={{ padding: 12 }}>
                <div
                  className="truncate"
                  style={{
                    fontFamily: "var(--font-serif)",
                    fontSize: 15,
                    fontWeight: 500,
                  }}
                >
                  {r.name}
                </div>
                <div
                  className="truncate mt-0.5"
                  style={{ fontSize: 11.5, color: "var(--color-muted)" }}
                >
                  {r.signature_dish ?? r.category}
                </div>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <StarRow value={r.rating} size={11} />
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      color: "var(--color-muted)",
                    }}
                  >
                    {r.rating.toFixed(1)} · {r.distance_m}m
                  </span>
                </div>
              </div>
            </div>
            <div
              className="mt-2 leading-snug"
              style={{
                fontSize: 11.5,
                color: "var(--color-olive-700)",
                fontStyle: "italic",
                fontFamily: "var(--font-serif)",
              }}
            >
              &ldquo;{r.reason}&rdquo;
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
