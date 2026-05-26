"use client";

import Link from "next/link";
import { Image as ImageIcon } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";
import { useEntries } from "@/lib/api/entries";
import type { EntrySummary } from "@/lib/types";

/**
 * Diary list.
 *
 * Entries arrive pre-grouped via the server-computed `day_label` field
 * ("Today", "Yesterday", "Sun, Apr 19"); the client just groups by
 * consecutive equal values.
 */
export default function DiaryPage() {
  const { data, isLoading } = useEntries();

  if (isLoading) {
    return (
      <div className="px-6 pt-16">
        <h1 className="text-[28px] leading-tight font-normal">Diary</h1>
        <p className="mt-2" style={{ color: "var(--color-muted)", fontSize: 13 }}>
          Loading…
        </p>
      </div>
    );
  }

  const items = data?.items ?? [];
  if (items.length === 0) return <DiaryEmpty />;
  const stats = data?.stats;
  const groups = groupByDayLabel(items);

  return (
    <div className="pb-12">
      <header
        className="px-6"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 36px)" }}
      >
        <div
          style={{
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            color: "var(--color-muted)",
            letterSpacing: "0.06em",
          }}
        >
          DIARY
        </div>
        <h1 className="leading-tight font-normal mt-1" style={{ fontSize: 28 }}>
          Every meal,{" "}
          <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>
            remembered.
          </em>
        </h1>
        {stats && (
          <div className="flex gap-5 mt-4" style={{ fontSize: 12, color: "var(--color-muted)" }}>
            <Stat label="entries" value={stats.entries_total} />
            <Stat label="places" value={stats.places_total} />
            <Stat label="this month" value={stats.this_month} />
            <Stat label="avg" value={stats.avg_rating.toFixed(1)} />
          </div>
        )}
      </header>

      <div className="px-6 mt-6">
        {groups.map(({ label, items }) => (
          <section key={label} className="mb-5">
            <div
              className="mb-2.5"
              style={{
                fontSize: 10.5,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              {label.toUpperCase()}
            </div>
            <div className="flex flex-col gap-2.5">
              {items.map((e) => (
                <EntryCard key={e.id} e={e} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <div
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: 18,
          fontWeight: 500,
          color: "var(--color-ink)",
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div
        className="mt-0.5"
        style={{ fontSize: 11, fontFamily: "var(--font-mono)", letterSpacing: "0.04em" }}
      >
        {label}
      </div>
    </div>
  );
}

function EntryCard({ e }: { e: EntrySummary }) {
  const time = new Date(e.captured_at).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
  return (
    <Link href={`/diary/${e.id}`} className="card flex gap-3 p-3 items-start">
      <div className="relative shrink-0">
        <FoodPlaceholder
          tone={e.cover_media_tone}
          label={e.restaurant.signature_dish ?? e.cover_media_label}
          width={92}
          height={92}
          radius={12}
        />
        {e.media_count > 1 && (
          <div
            className="absolute flex items-center gap-1"
            style={{
              bottom: 6,
              right: 6,
              padding: "2px 6px",
              borderRadius: 999,
              background: "rgba(0,0,0,0.55)",
              color: "var(--color-cream)",
              fontSize: 9.5,
              fontFamily: "var(--font-mono)",
            }}
          >
            <ImageIcon size={9} strokeWidth={2} />
            {e.media_count}
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <div
            className="truncate"
            style={{ fontFamily: "var(--font-serif)", fontSize: 16, fontWeight: 500 }}
          >
            {e.restaurant.name}
          </div>
          <div
            className="shrink-0"
            style={{
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
            }}
          >
            {time}
          </div>
        </div>
        <div
          className="truncate mt-0.5"
          style={{ fontSize: 12, color: "var(--color-muted)" }}
        >
          {e.restaurant.signature_dish ?? e.restaurant.neighborhood}
        </div>
        <div className="mt-1.5">
          {e.rating != null ? (
            <StarRow value={e.rating} size={13} />
          ) : (
            <span
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted-2)",
              }}
            >
              no rating
            </span>
          )}
        </div>
        <p
          className="mt-1.5"
          style={{
            fontSize: 12.5,
            lineHeight: 1.45,
            color: "var(--color-ink-2)",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {e.note_excerpt}
        </p>
      </div>
    </Link>
  );
}

function DiaryEmpty() {
  return (
    <div className="px-6 pt-16">
      <div
        style={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--color-muted)",
          letterSpacing: "0.06em",
        }}
      >
        DIARY
      </div>
      <h1 className="text-[28px] leading-tight font-normal mt-1">
        Nothing here{" "}
        <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>
          yet.
        </em>
      </h1>
      <p
        className="mt-3 leading-relaxed"
        style={{ fontSize: 14, color: "var(--color-muted)" }}
      >
        Snap a meal, finish the draft, and it&apos;ll land here forever.
      </p>
      <Link href="/capture" className="btn mt-6 inline-flex">
        Capture a meal
      </Link>
    </div>
  );
}

function groupByDayLabel(items: EntrySummary[]): Array<{ label: string; items: EntrySummary[] }> {
  const groups: Array<{ label: string; items: EntrySummary[] }> = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.label === item.day_label) last.items.push(item);
    else groups.push({ label: item.day_label, items: [item] });
  }
  return groups;
}
