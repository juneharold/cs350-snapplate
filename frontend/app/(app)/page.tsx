"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Camera, MapPin, Search } from "lucide-react";
import { DraftDock } from "@/components/screens/explore/DraftDock";
import { CategoryChips } from "@/components/screens/explore/CategoryChips";
import { RecommendedStrip } from "@/components/screens/explore/RecommendedStrip";
import { FALLBACK_LOCATION, useAuth } from "@/lib/store/auth";
import { useMe } from "@/lib/api/auth";
import { useDrafts } from "@/lib/api/drafts";
import { useNearbyRestaurants, useRecommendedRestaurants } from "@/lib/api/restaurants";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { StarRow } from "@/components/ui/StarRating";

/**
 * Home / Explore.
 *
 * Lays out the prototype's ExploreHome:
 *   • header (greeting + avatar)
 *   • drafts dock (magnification — see DraftDock)
 *   • search bar
 *   • category filter chips (seed categories from data + user-added)
 *   • nearby card list, filtered by the active chip
 */

function getTimeBucket(date: Date) {
  const minutes = date.getHours() * 60 + date.getMinutes();
  const isWeekend = date.getDay() === 0 || date.getDay() === 6;

  if (minutes >= 21 * 60 || minutes < 6 * 60) return "late night";
  if (minutes >= 17 * 60 + 30) return "dinner";
  if (minutes >= 14 * 60 + 30) return "afternoon";
  if (minutes >= 11 * 60 + 30) return "lunch";
  if (isWeekend && minutes >= 10 * 60) return "brunch";
  if (minutes >= 6 * 60) return "breakfast";
  return "late night";
}

function buildTypingDelays(label: string) {
  let seed = 0;
  for (let i = 0; i < label.length; i += 1) {
    seed = (seed + label.charCodeAt(i) * (i + 1)) % 233280;
  }
  const rand = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  let acc = 0;
  return Array.from(label).map((char) => {
    const step = 55 + Math.round(rand() * 65);
    acc += step;
    return { char, delay: acc };
  });
}

export default function ExploreHome() {
  const localUser = useAuth((s) => s.user);
  const location = useAuth((s) => s.currentLocation);
  const locationGranted = useAuth((s) => s.locationGranted);
  const setCurrentLocation = useAuth((s) => s.setCurrentLocation);
  const setLocationGranted = useAuth((s) => s.setLocationGranted);
  const { data: me } = useMe();
  const nickname = me?.nickname ?? localUser?.nickname ?? "friend";
  const { data: drafts } = useDrafts();
  const { data: nearby } = useNearbyRestaurants(
    location?.lat ?? null,
    location?.lng ?? null,
  );
  const { data: recommended } = useRecommendedRestaurants(
    location?.lat ?? null,
    location?.lng ?? null,
    { limit: 6 },
  );
  const draftItems = drafts?.items ?? [];
  const didRequestLocation = useRef(false);
  const [now, setNow] = useState(() => new Date());
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const nearbyItems = useMemo(() => nearby?.items ?? [], [nearby]);
  const recommendedItems = useMemo(() => recommended?.items ?? [], [recommended]);

  // The set of "seed" categories powers the chip row AND the strict
  // match path in `matchesChip`. Pull from both lists so a category
  // that only appears in recommendations still gets a chip.
  const seedCategories = useMemo(() => {
    const set = new Set<string>();
    for (const r of nearbyItems) set.add(r.category);
    for (const r of recommendedItems) set.add(r.category);
    return Array.from(set).sort();
  }, [nearbyItems, recommendedItems]);

  const matcher = useMemo(() => {
    // Build the predicate once per chip change. Seed chips do a literal
    // category match; user-added chips do a soft substring search.
    if (!activeCategory) return () => true;
    if (seedCategories.includes(activeCategory)) {
      return (r: { category: string }) => r.category === activeCategory;
    }
    const q = activeCategory.toLowerCase();
    return (r: {
      name: string;
      signature_dish: string | null;
      category: string;
      neighborhood: string;
      tags: string[];
    }) =>
      [r.name, r.signature_dish ?? "", r.category, r.neighborhood, ...r.tags]
        .join(" ")
        .toLowerCase()
        .includes(q);
  }, [activeCategory, seedCategories]);

  const filteredNearby = useMemo(
    () => nearbyItems.filter(matcher),
    [nearbyItems, matcher],
  );
  const filteredRecommended = useMemo(
    () =>
      recommended
        ? { ...recommended, items: recommendedItems.filter(matcher) }
        : null,
    [recommended, recommendedItems, matcher],
  );

  useEffect(() => {
    if (didRequestLocation.current) return;
    if (locationGranted === false) return; // explicitly denied — respect it
    if (typeof navigator === "undefined" || !navigator.geolocation) return;

    const request = () => {
      if (didRequestLocation.current) return;
      didRequestLocation.current = true;
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocationGranted(true);
          setCurrentLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        },
        () => {
          setCurrentLocation(FALLBACK_LOCATION);
        },
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
      );
    };

    if (locationGranted === true) {
      request();
      return;
    }

    // Flag is null (never asked in-app, e.g. after a logout/login cycle).
    // Honor an existing browser-level grant without forcing a prompt.
    navigator.permissions
      ?.query({ name: "geolocation" as PermissionName })
      .then((status) => {
        if (status.state === "granted") request();
      })
      .catch(() => {});
  }, [locationGranted, setCurrentLocation, setLocationGranted]);

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 3_600_000);
    return () => window.clearInterval(id);
  }, []);

  const timeLabel = getTimeBucket(now);
  const timeLetters = useMemo(() => buildTypingDelays(timeLabel), [timeLabel]);

  // No reverse-geocoding backend, so surface the neighborhood of the
  // closest nearby restaurant as the user's area (falls back to a
  // recommended one) instead of a hardcoded placeholder.
  const areaLabel =
    nearbyItems[0]?.neighborhood ?? recommendedItems[0]?.neighborhood ?? null;

  return (
    <div className="pb-12">
      <header
        className="px-4"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 36px)" }}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div
              className="flex items-center gap-1"
              style={{
                fontSize: 12,
                color: "var(--color-muted)",
                fontFamily: "var(--font-mono)",
                letterSpacing: "0.06em",
              }}
            >
              <MapPin size={11} strokeWidth={2} />
              {areaLabel ? `${areaLabel} · ` : ""}
              <span key={timeLabel} className="time-label">
                    {timeLetters.map(({ char, delay }, index) => (
                      <span
                        key={`${char}-${index}`}
                        className="time-letter"
                        style={{ animationDelay: `${delay}ms` }}
                      >
                        {char === " " ? "\u00A0" : char}
                      </span>
                    ))}
              </span>
            </div>
            <h1
              className="leading-tight font-normal mt-1.5"
              style={{ fontSize: 28, overflowWrap: "anywhere" }}
            >
              Hi {nickname}, what shall we{" "}
              <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>
                eat?
              </em>
            </h1>
          </div>
          <Link
            href="/me"
            className="avatar"
            aria-label="Open profile"
            style={{
              width: 52,
              height: 52,
              fontSize: 18,
              flexShrink: 0,
              borderRadius: "50%",
              marginLeft: 12,
              transform: "translateY(8px)",
              overflow: "hidden",
            }}
          >
            {me?.profile_image_url || localUser?.profile_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={me?.profile_image_url ?? localUser?.profile_image_url ?? ""}
                alt={nickname}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            ) : (
              <span className="avatar-letter">
                {(nickname ?? "?").charAt(0).toUpperCase()}
              </span>
            )}
          </Link>
        </div>
      </header>

      {/* Drafts dock */}
      {draftItems.length > 0 ? <DraftDock drafts={draftItems} /> : <EmptyDock />}

      {/* Search */}
      <section className="px-4 mt-4">
        <Link
          href="/search"
          className="input input-search flex items-center gap-2"
          style={{ width: "100%", color: "var(--color-muted)", fontSize: 14 }}
        >
          <Search size={18} />
          Search restaurants or dishes
        </Link>
      </section>

      {/* Category filter — sits right under search and drives Nearby */}
      <div className="mt-2">
        <CategoryChips
          seedCategories={seedCategories}
          active={activeCategory}
          onChange={setActiveCategory}
        />
      </div>

      {/* For your taste — personalized strip; chips filter this too */}
      {filteredRecommended?.has_enough_data &&
        filteredRecommended.items.length > 0 && (
          <RecommendedStrip data={filteredRecommended} />
        )}

      {/* Nearby — filtered by the active category chip */}
      <section className="px-4 mt-3">
        <div className="flex items-baseline justify-between mb-2">
          <h2
            className="leading-tight"
            style={{ fontFamily: "var(--font-serif)", fontSize: 22, fontWeight: 500 }}
          >
            Nearby
          </h2>
          {activeCategory && (
            <button
              type="button"
              onClick={() => setActiveCategory(null)}
              style={{
                fontSize: 12,
                color: "var(--color-olive-700)",
                fontWeight: 500,
              }}
            >
              Clear filter
            </button>
          )}
        </div>
        {filteredNearby.length > 0 ? (
          <div className="list-group">
          {filteredNearby.slice(0, 8).map((r) => (
            <Link
              key={r.id}
              href={`/restaurants/${r.id}`}
              className="flex gap-3 p-3 items-center"
            >
              <FoodPlaceholder
                src={r.thumbnail_url}
                alt={r.name}
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
        ) : (
          <div
            className="card p-4 text-center"
            style={{ color: "var(--color-muted)", fontSize: 13 }}
          >
            {activeCategory
              ? `No nearby spots match “${activeCategory}”.`
              : location
                ? "Nothing nearby in the seed set yet."
                : locationGranted
                  ? "Finding your location…"
                  : "Grant location to see nearby restaurants."}
          </div>
        )}
      </section>
    </div>
  );
}

function EmptyDock() {
  return (
    <section className="mt-3 px-4">
      <div
        className="card relative"
        style={{
          padding: 18,
          background: "var(--color-surface)",
          borderColor: "var(--color-border-soft)",
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center shrink-0"
            style={{ color: "var(--color-olive-700)" }}
          >
            <Camera size={24} strokeWidth={1.6} />
          </div>
          <div className="flex-1">
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 16,
                fontWeight: 500,
              }}
            >
              No drafts yet
            </div>
            <div
              className="leading-relaxed mt-0.5"
              style={{ fontSize: 12.5, color: "var(--color-muted)" }}
            >
              Snap a meal — we&apos;ll save the place and time, you add a note
              after.
            </div>
          </div>
        </div>
        <Link href="/capture" className="btn mt-4 inline-flex">
          Capture a meal
        </Link>
      </div>
    </section>
  );
}
