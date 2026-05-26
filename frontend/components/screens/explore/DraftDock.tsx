"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import type { DraftSummary } from "@/lib/types";

/**
 * Horizontal "drafts waiting" dock.
 *
 * The card closest to the focal point (a tunable offset from the left
 * edge) scales up to 1.0; the rest fall off via a cosine bump down to
 * `MIN_SCALE` at `FALLOFF` slots out. Math + tunables copied verbatim
 * from the prototype's `DraftStrip`.
 *
 * Scroll handler uses rAF to batch the state updates so we don't
 * thrash on fast scrolls.
 */
const SLOT_W = 176;
const STRIP_GAP = 10;
const PHOTO_H = 132;
const MIN_SCALE = 0.66;
const FALLOFF = 1.7;

export function DraftDock({ drafts }: { drafts: DraftSummary[] }) {
  const router = useRouter();
  const scrollerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [overflows, setOverflows] = useState(false);

  useEffect(() => {
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Decide whether the strip needs to scroll. Compute the cards'
  // natural rest width (without the trailing focus-pad) and compare
  // to the container's inner width. A ResizeObserver keeps it honest
  // when the viewport changes.
  useLayoutEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const naturalContent =
      drafts.length * SLOT_W + Math.max(0, drafts.length - 1) * STRIP_GAP;
    const check = () => {
      const cs = window.getComputedStyle(el);
      const padX = parseFloat(cs.paddingLeft || "0") + parseFloat(cs.paddingRight || "0");
      const inner = el.clientWidth - padX;
      setOverflows(naturalContent > inner + 1);
    };
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [drafts.length]);

  // Reset scroll position whenever we collapse back to non-scrolling.
  useEffect(() => {
    if (!overflows && scrollerRef.current) {
      scrollerRef.current.scrollLeft = 0;
      setScrollLeft(0);
    }
  }, [overflows]);

  function onScroll(e: React.UIEvent<HTMLDivElement>) {
    if (!overflows) return;
    const next = e.currentTarget.scrollLeft;
    if (rafRef.current != null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      setScrollLeft(next);
    });
  }

  const focalIdx = scrollLeft / (SLOT_W + STRIP_GAP);

  function scaleFor(i: number): number {
    const d = Math.abs(i - focalIdx);
    if (d >= FALLOFF) return MIN_SCALE;
    const k = 0.5 * (1 + Math.cos((Math.PI * d) / FALLOFF));
    return MIN_SCALE + (1 - MIN_SCALE) * k;
  }

  const firstName = drafts[0]?.restaurant?.name?.split(" ")[0] ?? "that meal";

  return (
    <section style={{ paddingTop: 20 }}>
      <div className="px-6 flex items-baseline justify-between">
        <div className="flex items-baseline gap-2">
          <h2
            className="leading-tight"
            style={{ fontFamily: "var(--font-serif)", fontSize: 18, fontWeight: 500 }}
          >
            <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>
              {drafts.length} {drafts.length === 1 ? "meal" : "meals"}
            </em>{" "}
            waiting
          </h2>
          <span
            className="chip"
            style={{
              height: 22,
              padding: "0 8px",
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              color: "var(--color-olive-700)",
              borderColor: "var(--color-olive-300)",
              gap: 4,
            }}
          >
            <span
              style={{
                width: 5,
                height: 5,
                borderRadius: 999,
                background: "var(--color-olive-700)",
              }}
            />
            DRAFTS
          </span>
        </div>
        <Link
          href="/drafts"
          style={{ fontSize: 12, color: "var(--color-olive-700)", fontWeight: 500 }}
        >
          See all →
        </Link>
      </div>
      <div
        className="px-6"
        style={{ fontSize: 12, color: "var(--color-muted)", marginBottom: 12, marginTop: 4 }}
      >
        How was that {firstName}? Drop a rating to finish each.
      </div>

      <div
        ref={scrollerRef}
        onScroll={onScroll}
        style={{
          display: "flex",
          gap: STRIP_GAP,
          padding: "12px 22px 14px",
          overflowX: overflows ? "auto" : "hidden",
          alignItems: "center",
          scrollbarWidth: "none",
        }}
      >
        {drafts.map((d, i) => {
          const s = scaleFor(i);
          const isFocal = Math.abs(i - focalIdx) < 0.5;
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => router.push(`/drafts/${d.id}/finish`)}
              className="text-left"
              style={{
                width: SLOT_W * s,
                flexShrink: 0,
                background: "var(--color-olive-700)",
                borderRadius: 14,
                color: "var(--color-cream)",
                overflow: "hidden",
                transition: "width 80ms linear",
                boxShadow: isFocal
                  ? "0 10px 24px -8px rgba(63,74,44,0.45)"
                  : "none",
              }}
            >
              <div style={{ height: PHOTO_H * s, transition: "height 80ms linear" }}>
                <FoodPlaceholder
                  tone={d.cover_media_tone}
                  label={d.restaurant?.name ?? d.cover_media_label}
                  width="100%"
                  height="100%"
                  radius={0}
                />
              </div>
              <div style={{ padding: 10 * s + 4 }}>
                <div className="flex items-baseline justify-between gap-1.5">
                  <div
                    className="truncate"
                    style={{
                      fontFamily: "var(--font-serif)",
                      fontSize: 14.5 * Math.max(s, 0.78),
                      fontWeight: 500,
                    }}
                  >
                    {d.restaurant?.name ?? "Unknown"}
                  </div>
                  {isFocal && (
                    <span
                      className="shrink-0"
                      style={{
                        fontSize: 9,
                        fontFamily: "var(--font-mono)",
                        background: "rgba(244,240,222,0.18)",
                        padding: "2px 6px",
                        borderRadius: 999,
                        letterSpacing: "0.04em",
                      }}
                    >
                      {i === 0 ? "LATEST" : "NEXT"}
                    </span>
                  )}
                </div>
                <div
                  className="flex justify-between mt-0.5"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 10 * Math.max(s, 0.85),
                    opacity: 0.72,
                  }}
                >
                  <span>{d.captured_relative}</span>
                  <span>
                    {d.status === "needs_place"
                      ? "Needs place"
                      : d.restaurant_suggested
                        ? "GPS-matched"
                        : "Place set"}
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    marginTop: 8,
                    height: 28 + 4 * s,
                    borderRadius: 8,
                    background: "var(--color-cream)",
                    color: "var(--color-olive-700)",
                    fontSize: 12 * Math.max(s, 0.9),
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  Finish →
                </div>
              </div>
            </button>
          );
        })}
        {/* trailing pad so the last card can scroll into focus — only
            needed when the strip actually scrolls */}
        {overflows && <div style={{ width: SLOT_W * 2, flexShrink: 0 }} />}
      </div>
    </section>
  );
}
