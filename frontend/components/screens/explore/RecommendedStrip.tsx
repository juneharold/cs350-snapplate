"use client";

import Link from "next/link";
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
            className="flex"
            style={{ width: 210, flexShrink: 0 }}
          >
            <div
              className="card flex flex-col"
              style={{ padding: 14, width: "100%" }}
            >
              <div
                className="truncate"
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: 15.5,
                  fontWeight: 500,
                }}
              >
                {r.name}
              </div>
              <div
                className="truncate mt-0.5"
                style={{ fontSize: 11.5, color: "var(--color-muted)" }}
              >
                {r.category} · {r.neighborhood}
              </div>
              <div
                className="leading-snug"
                style={{
                  marginTop: "auto",
                  paddingTop: 12,
                  fontSize: 12,
                  color: "var(--color-olive-700)",
                  fontStyle: "italic",
                  fontFamily: "var(--font-serif)",
                }}
              >
                &ldquo;{r.reason}&rdquo;
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
