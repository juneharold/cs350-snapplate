"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Check, ChevronLeft, Search, SlidersHorizontal, X } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";
import { useSearchRestaurants } from "@/lib/api/restaurants";
import { useAuth, FALLBACK_LOCATION } from "@/lib/store/auth";

const RECENT_PLACEHOLDERS = [
  "Sungsim Bakery",
  "pork belly",
  "Cafe Dotori",
  "cold noodle",
];

const RATING_BUCKETS = [
  { label: "Any", value: null as number | null },
  { label: "3.5+", value: 3.5 },
  { label: "4.0+", value: 4.0 },
  { label: "4.5+", value: 4.5 },
];
const SORTS = [
  { label: "Distance", value: "distance" },
  { label: "Rating", value: "rating" },
  { label: "Recommended for you", value: "recommended" },
];

/**
 * Distance slider stops — log-ish spacing so the close-by detail isn't
 * crushed by the long tail. Index 4 (10km) is "any" — anything past
 * that is rarely useful for a walking-distance app.
 */
const DISTANCE_STOPS = [
  { label: "200m", value: 200 },
  { label: "500m", value: 500 },
  { label: "1km", value: 1000 },
  { label: "3km", value: 3000 },
  { label: "10km", value: 10000 },
];
const DISTANCE_ANY_INDEX = DISTANCE_STOPS.length - 1;

function formatDistance(meters: number): string {
  if (meters >= 1000) {
    const km = meters / 1000;
    return km % 1 === 0 ? `${km}km` : `${km.toFixed(1)}km`;
  }
  return `${meters}m`;
}

export default function SearchPage() {
  const location = useAuth((s) => s.currentLocation) ?? FALLBACK_LOCATION;
  const [raw, setRaw] = useState("");
  const [debounced, setDebounced] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [minRating, setMinRating] = useState<number | null>(null);
  const [maxDistance, setMaxDistance] = useState<number | null>(null);
  const [sort, setSort] = useState<string>("distance");

  // Debounce: 300ms per the spec.
  useEffect(() => {
    const t = setTimeout(() => setDebounced(raw.trim()), 300);
    return () => clearTimeout(t);
  }, [raw]);

  const { data, isFetching } = useSearchRestaurants(debounced, location.lat, location.lng);
  const items = useMemo(() => {
    let list = data?.items ?? [];
    if (minRating != null) list = list.filter((r) => r.rating >= minRating);
    if (maxDistance != null) list = list.filter((r) => r.distance_m <= maxDistance);
    if (sort === "rating") list = [...list].sort((a, b) => b.rating - a.rating);
    else if (sort === "distance") list = [...list].sort((a, b) => a.distance_m - b.distance_m);
    return list;
  }, [data, minRating, maxDistance, sort]);

  const activeFilters =
    (minRating != null ? 1 : 0) +
    (maxDistance != null ? 1 : 0) +
    (sort !== "distance" ? 1 : 0);

  return (
    <div className="pb-12">
      <header
        className="px-4"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 36px)" }}
      >
        <div className="flex items-center gap-2">
          <Link
            href="/"
            aria-label="Back"
            className="flex items-center justify-center"
            style={{ width: 40, height: 40, color: "var(--color-ink)" }}
          >
            <ChevronLeft size={22} />
          </Link>
          <div className="flex-1 relative">
            <span
              className="absolute"
              style={{
                left: 14,
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--color-olive-700)",
              }}
            >
              <Search size={18} />
            </span>
            <input
              autoFocus
              type="search"
              inputMode="search"
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              placeholder="Search restaurants or dishes"
              className="input input-search"
              style={{ paddingLeft: 42, paddingRight: 40 }}
            />
            {raw && (
              <button
                type="button"
                onClick={() => setRaw("")}
                aria-label="Clear"
                className="absolute"
                style={{
                  right: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--color-muted)",
                }}
              >
                <X size={16} />
              </button>
            )}
          </div>
          <button
            type="button"
            aria-label="Filters"
            onClick={() => setShowFilters(true)}
            className="relative"
            style={{
              width: 40,
              height: 40,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: activeFilters
                ? "var(--color-olive-700)"
                : "var(--color-ink)",
            }}
          >
            <SlidersHorizontal size={20} />
            {activeFilters > 0 && (
              <span
                className="absolute flex items-center justify-center"
                style={{
                  top: 6,
                  right: 6,
                  width: 14,
                  height: 14,
                  borderRadius: 999,
                  background: "var(--color-olive-700)",
                  color: "var(--color-cream)",
                  fontSize: 9,
                  fontWeight: 700,
                }}
              >
                {activeFilters}
              </span>
            )}
          </button>
        </div>
      </header>

      <div className="px-6 mt-3">
        {debounced ? (
          <div
            className="mb-3"
            style={{
              fontSize: 12,
              color: "var(--color-muted)",
              fontFamily: "var(--font-mono)",
              letterSpacing: "0.04em",
            }}
          >
            {isFetching
              ? "Searching…"
              : items.length === 0
                ? "No matches"
                : `${items.length} match${items.length === 1 ? "" : "es"}`}
          </div>
        ) : (
          <div className="mt-2">
            <div
              className="mb-2"
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              TRY
            </div>
            <div className="flex flex-wrap gap-2">
              {RECENT_PLACEHOLDERS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setRaw(t)}
                  className="chip"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-col gap-2.5 mt-1">
          {items.map((r) => (
            <Link
              key={r.id}
              href={`/restaurants/${r.id}`}
              className="card flex gap-3 p-3 items-center"
            >
              <FoodPlaceholder
                tone={r.thumbnail_tone}
                label={r.signature_dish ?? r.thumbnail_label}
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
                    {r.name}
                  </div>
                  <div
                    className="shrink-0"
                    style={{
                      fontSize: 10.5,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-muted)",
                    }}
                  >
                    {r.distance_m}m
                  </div>
                </div>
                <div
                  className="truncate mt-0.5"
                  style={{ fontSize: 12, color: "var(--color-muted)" }}
                >
                  {r.signature_dish ?? r.category} · {r.neighborhood}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <StarRow value={r.rating} size={12} />
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10.5,
                      color: "var(--color-muted)",
                    }}
                  >
                    {r.rating.toFixed(1)} · {r.rating_count}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {showFilters && (
        <FilterSheet
          minRating={minRating}
          maxDistance={maxDistance}
          sort={sort}
          onClose={() => setShowFilters(false)}
          onApply={(next) => {
            setMinRating(next.minRating);
            setMaxDistance(next.maxDistance);
            setSort(next.sort);
            setShowFilters(false);
          }}
        />
      )}
    </div>
  );
}

function FilterSheet({
  minRating,
  maxDistance,
  sort,
  onClose,
  onApply,
}: {
  minRating: number | null;
  maxDistance: number | null;
  sort: string;
  onClose: () => void;
  onApply: (next: {
    minRating: number | null;
    maxDistance: number | null;
    sort: string;
  }) => void;
}) {
  const [draftMinRating, setDraftMinRating] = useState(minRating);
  const [draftSort, setDraftSort] = useState(sort);
  // Slider works in DISTANCE_STOPS index-space. Anything at the topmost
  // stop is treated as "no filter" — see `commit` below.
  const initialDistanceIdx = (() => {
    if (maxDistance == null) return DISTANCE_ANY_INDEX;
    const i = DISTANCE_STOPS.findIndex((s) => s.value === maxDistance);
    return i === -1 ? DISTANCE_ANY_INDEX : i;
  })();
  const [draftDistanceIdx, setDraftDistanceIdx] = useState(initialDistanceIdx);

  function reset() {
    setDraftMinRating(null);
    setDraftDistanceIdx(DISTANCE_ANY_INDEX);
    setDraftSort("distance");
  }

  function commit() {
    const stop = DISTANCE_STOPS[draftDistanceIdx]!;
    onApply({
      minRating: draftMinRating,
      maxDistance: draftDistanceIdx >= DISTANCE_ANY_INDEX ? null : stop.value,
      sort: draftSort,
    });
  }

  return (
    <div
      className="absolute inset-0 z-30 flex items-center justify-center"
      style={{
        background: "rgba(31,31,25,0.55)",
        padding: "20px",
        animation: "snapplate-dialog-fade 0.18s ease-out",
      }}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Filters"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--color-surface)",
          borderRadius: 20,
          padding: "20px 22px 22px",
          width: "100%",
          maxWidth: 340,
          maxHeight: "calc(100% - 40px)",
          overflowY: "auto",
          boxShadow:
            "0 24px 48px -12px rgba(31,31,25,0.45), 0 0 0 1px rgba(0,0,0,0.04)",
          animation: "snapplate-dialog-in 0.2s cubic-bezier(0.2, 0.9, 0.3, 1)",
        }}
      >
        <div className="flex justify-between items-baseline mb-5">
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 22, fontWeight: 500 }}>
            Filters
          </h2>
          <button
            type="button"
            onClick={reset}
            style={{
              fontSize: 13,
              color: "var(--color-olive-700)",
              fontWeight: 500,
            }}
          >
            Reset
          </button>
        </div>

        <section className="mb-5">
          <div
            className="mb-2.5"
            style={{
              fontSize: 12,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
              letterSpacing: "0.06em",
            }}
          >
            RATING
          </div>
          <div className="flex gap-2">
            {RATING_BUCKETS.map((b) => {
              const active = b.value === draftMinRating;
              return (
                <button
                  key={b.label}
                  type="button"
                  onClick={() => setDraftMinRating(b.value)}
                  className={`chip ${active ? "chip-solid" : ""}`}
                  style={{ flex: 1, justifyContent: "center" }}
                >
                  {b.label}
                </button>
              );
            })}
          </div>
        </section>

        <section className="mb-5">
          <div className="flex justify-between items-baseline mb-2.5">
            <div
              style={{
                fontSize: 12,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              DISTANCE
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--color-ink)",
                fontWeight: 500,
              }}
            >
              {draftDistanceIdx >= DISTANCE_ANY_INDEX
                ? "Any distance"
                : `Within ${formatDistance(DISTANCE_STOPS[draftDistanceIdx]!.value)}`}
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={DISTANCE_STOPS.length - 1}
            step={1}
            value={draftDistanceIdx}
            onChange={(e) => setDraftDistanceIdx(parseInt(e.target.value, 10))}
            aria-label="Maximum distance"
            className="snapplate-range"
            style={{
              ["--snapplate-range-pct" as string]: `${
                (draftDistanceIdx / (DISTANCE_STOPS.length - 1)) * 100
              }%`,
            }}
          />
          <div
            className="flex justify-between mt-1.5"
            style={{
              fontSize: 10,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
            }}
          >
            {DISTANCE_STOPS.map((s) => (
              <span key={s.value}>{s.label}</span>
            ))}
          </div>
        </section>

        <section className="mb-6">
          <div
            className="mb-2.5"
            style={{
              fontSize: 12,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
              letterSpacing: "0.06em",
            }}
          >
            SORT BY
          </div>
          {SORTS.map((s, i) => {
            const active = draftSort === s.value;
            return (
              <button
                key={s.value}
                type="button"
                onClick={() => setDraftSort(s.value)}
                className="flex justify-between items-center w-full"
                style={{
                  padding: "12px 0",
                  fontSize: 14,
                  color: "var(--color-ink)",
                  borderTop: i > 0 ? "1px solid var(--color-border-soft)" : "none",
                }}
              >
                <span style={{ fontWeight: active ? 600 : 400 }}>{s.label}</span>
                {active && (
                  <Check size={18} style={{ color: "var(--color-olive-700)" }} />
                )}
              </button>
            );
          })}
        </section>

        <button
          type="button"
          onClick={commit}
          className="btn btn-block"
        >
          Apply filters
        </button>
      </div>
    </div>
  );
}
