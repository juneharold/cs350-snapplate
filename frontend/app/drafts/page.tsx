"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, Clock, Image as ImageIcon } from "lucide-react";
import { Screen } from "@/components/layout/Screen";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { useDeleteDraft, useDrafts } from "@/lib/api/drafts";
import type { DraftSummary } from "@/lib/types";

/**
 * Drafts inbox — every unfinished snap the user has stashed. Each card
 * shows the cover photo, place, captured-at, status sub-line, and two
 * actions: Finish (→ entry form) and Discard (DELETE /drafts/:id).
 */
export default function DraftsInboxPage() {
  const router = useRouter();
  const { data } = useDrafts();
  const items = data?.items ?? [];

  const today = items.filter((d) => isToday(d));
  const earlier = items.filter((d) => !isToday(d));

  return (
    <Screen>
      <div className="flex flex-col h-full">
        <div
          className="px-5 flex items-center gap-2.5 shrink-0"
          style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 36px)", paddingBottom: 12 }}
        >
          <Link
            href="/"
            aria-label="Back"
            className="flex items-center justify-center"
            style={{ width: 40, height: 40, color: "var(--color-ink)" }}
          >
            <ChevronLeft size={22} />
          </Link>
          <div className="flex-1">
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              DRAFTS
            </div>
            <h1
              className="leading-tight"
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 22,
                fontWeight: 500,
                marginTop: 2,
              }}
            >
              {items.length === 0
                ? "Nothing waiting"
                : `${items.length} ${items.length === 1 ? "meal" : "meals"} to finish`}
            </h1>
          </div>
        </div>

        <div className="px-5 pt-1 pb-3 shrink-0">
          <div
            className="flex gap-2.5 items-start"
            style={{
              padding: 12,
              background: "var(--color-bg-soft)",
              border: "1px solid var(--color-border-soft)",
              borderRadius: 12,
              fontSize: 12,
              color: "var(--color-ink-2)",
              lineHeight: 1.5,
            }}
          >
            <span style={{ color: "var(--color-olive-700)", flexShrink: 0, marginTop: 1 }}>
              <Clock size={16} />
            </span>
            <div>
              <b>Drafts wait here</b> until you finish them. Tap a card to add a
              note &mdash; that promotes it to a diary entry.
            </div>
          </div>
        </div>

        {/* Scrollable list on short viewports (min-h-0 lets flex-1 shrink) */}
        <div className="px-5 pb-8 flex-1 overflow-y-auto min-h-0">
          {items.length === 0 && <EmptyState />}
          {today.length > 0 && (
            <>
              <SectionLabel>TODAY</SectionLabel>
              {today.map((d) => (
                <DraftCard key={d.id} d={d} onFinish={() => router.push(`/drafts/${d.id}/finish`)} />
              ))}
            </>
          )}
          {earlier.length > 0 && (
            <>
              <SectionLabel>EARLIER</SectionLabel>
              {earlier.map((d) => (
                <DraftCard key={d.id} d={d} onFinish={() => router.push(`/drafts/${d.id}/finish`)} />
              ))}
            </>
          )}
        </div>
      </div>
    </Screen>
  );
}

function isToday(d: DraftSummary, now = new Date()): boolean {
  const t = new Date(d.captured_at);
  return (
    t.getFullYear() === now.getFullYear() &&
    t.getMonth() === now.getMonth() &&
    t.getDate() === now.getDate()
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mb-2"
      style={{
        fontSize: 10.5,
        fontFamily: "var(--font-mono)",
        color: "var(--color-muted)",
        letterSpacing: "0.06em",
        marginTop: 14,
      }}
    >
      {children}
    </div>
  );
}

function EmptyState() {
  return (
    <div
      className="card p-6 mt-2 text-center"
      style={{ color: "var(--color-muted)" }}
    >
      <div
        style={{ fontFamily: "var(--font-serif)", fontSize: 18, color: "var(--color-ink)" }}
      >
        Nothing in drafts.
      </div>
      <p className="mt-2 leading-relaxed" style={{ fontSize: 13 }}>
        Snap a meal to start a draft &mdash; we&apos;ll save the time and place
        for you.
      </p>
      <Link href="/capture" className="btn mt-3 inline-flex">
        Capture a meal
      </Link>
    </div>
  );
}

function DraftCard({
  d,
  onFinish,
}: {
  d: DraftSummary;
  onFinish: () => void;
}) {
  const del = useDeleteDraft();
  const time = new Date(d.captured_at).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
  const subline =
    d.status === "needs_place"
      ? "Tap to pick a place"
      : d.restaurant_suggested
        ? "Suggested from GPS"
        : "Place set";
  return (
    <div
      className="card flex gap-3 items-start"
      style={{ padding: 14, marginBottom: 10, position: "relative" }}
    >
      <div className="relative shrink-0">
        <FoodPlaceholder
          src={d.cover_media_url}
          tone={d.cover_media_tone}
          label={d.restaurant?.name ?? d.cover_media_label}
          width={78}
          height={78}
          radius={12}
        />
        {d.media_count > 1 && (
          <div
            className="absolute flex items-center gap-1"
            style={{
              bottom: 5,
              right: 5,
              padding: "2px 6px",
              borderRadius: 999,
              background: "rgba(0,0,0,0.6)",
              color: "var(--color-cream)",
              fontSize: 9.5,
              fontFamily: "var(--font-mono)",
            }}
          >
            <ImageIcon size={9} strokeWidth={2} />
            {d.media_count}
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex justify-between gap-2 items-baseline">
          <div
            className="truncate"
            style={{ fontFamily: "var(--font-serif)", fontSize: 16, fontWeight: 500 }}
          >
            {d.restaurant?.name ?? "Unknown place"}
          </div>
          <div
            className="shrink-0"
            style={{
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
            }}
          >
            {d.captured_relative}
          </div>
        </div>
        <div className="mt-0.5" style={{ fontSize: 11.5, color: "var(--color-muted)" }}>
          {`${time} · ${d.restaurant?.neighborhood ?? "no neighborhood"}`}
        </div>
        <div
          style={{
            fontSize: 11.5,
            color: d.status === "needs_place" ? "var(--color-danger)" : "var(--color-olive-700)",
            marginTop: 6,
            fontStyle: "italic",
            fontFamily: "var(--font-serif)",
          }}
        >
          {subline}
        </div>
        <div className="flex gap-2 mt-2.5">
          <button
            className="btn"
            style={{ height: 32, padding: "0 14px", fontSize: 12 }}
            onClick={onFinish}
          >
            Finish
          </button>
          <button
            className="btn btn-ghost"
            style={{
              height: 32,
              padding: "0 10px",
              fontSize: 12,
              color: "var(--color-muted)",
            }}
            disabled={del.isPending}
            onClick={() => {
              if (confirm("Discard this draft? Photos stay on the server for 30 days.")) {
                del.mutate(d.id);
              }
            }}
          >
            Discard
          </button>
        </div>
      </div>
    </div>
  );
}
