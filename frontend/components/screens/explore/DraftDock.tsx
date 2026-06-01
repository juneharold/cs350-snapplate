"use client";

import Link from "next/link";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import type { DraftSummary } from "@/lib/types";

/**
 * Drafts nudge.
 *
 * The most recent draft is its own tap target straight to its finish
 * page (one tap to rate it). When more are waiting, a small link below
 * jumps to the full /drafts list. No dock, no horizontal scroll.
 */
export function DraftDock({ drafts }: { drafts: DraftSummary[] }) {
  const count = drafts.length;
  const latest = drafts[0];
  if (!latest) return null;

  return (
    <section className="px-4 mt-4">
      <Link
        href={`/drafts/${latest.id}/finish`}
        className="card flex items-center gap-3"
        style={{ padding: 12 }}
      >
        <FoodPlaceholder
          tone={latest.cover_media_tone}
          src={latest.cover_media_url}
          label=""
          width={52}
          height={52}
          radius={10}
          style={{ flexShrink: 0 }}
        />
        <div className="flex-1 min-w-0">
          <div
            className="truncate"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 15,
              fontWeight: 600,
              lineHeight: 1.1,
            }}
          >
            {latest.restaurant?.name ?? "Unplaced meal"}
          </div>
          <div
            className="truncate"
            style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}
          >
            {latest.restaurant
              ? `Snapped ${latest.captured_relative}`
              : "Add a place to finish"}
          </div>
        </div>
        <span
          className="shrink-0"
          style={{
            background: "var(--color-olive-700)",
            color: "var(--color-cream)",
            fontSize: 12,
            fontWeight: 600,
            padding: "7px 14px",
            borderRadius: 999,
          }}
        >
          Finish
        </span>
      </Link>

      {count > 1 && (
        <Link
          href="/drafts"
          className="block"
          style={{
            marginTop: 8,
            fontSize: 12,
            fontWeight: 500,
            color: "var(--color-olive-700)",
          }}
        >
          View all {count} drafts →
        </Link>
      )}
    </section>
  );
}
