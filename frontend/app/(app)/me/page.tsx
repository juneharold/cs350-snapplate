"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Bookmark, Camera, ChevronRight, Settings as SettingsIcon, Sparkles } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { useAuth } from "@/lib/store/auth";
import { useMe } from "@/lib/api/auth";
import { useEntries } from "@/lib/api/entries";

/**
 * Me / Profile tab.
 *
 * Identity + headline stats + recent meals strip + saved-restaurants
 * quick link. Settings and log-out live in /me/settings to match the
 * prototype's grouping.
 */
export default function ProfilePage() {
  const localUser = useAuth((s) => s.user);
  const { data: me } = useMe();
  const { data: entries } = useEntries();
  const user = me ?? localUser;
  const nickname = user?.nickname ?? "—";
  const email = user?.email ?? "";

  const recent = useMemo(() => (entries?.items ?? []).slice(0, 5), [entries]);
  const stats = entries?.stats;
  const bookmarksCount = me?.stats.bookmarks_count ?? 0;

  return (
    <div className="pb-12">
      <header
        className="flex justify-between items-start px-4"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 36px)" }}
      >
        <div
          style={{
            fontSize: 12,
            color: "var(--color-muted)",
            fontFamily: "var(--font-mono)",
            letterSpacing: "0.06em",
          }}
        >
          PROFILE
        </div>
        <Link href="/me/settings" aria-label="Settings" style={{ color: "var(--color-ink)" }}>
          <SettingsIcon size={22} strokeWidth={1.6} />
        </Link>
      </header>

      <div className="flex gap-4 items-center px-4 mt-4">
        <div className="avatar" style={{ width: 80, height: 80, fontSize: 32 }}>
          {(nickname ?? "?").charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <h1
            className="leading-tight font-normal"
            style={{ fontSize: 24, lineHeight: 1 }}
          >
            {nickname}
          </h1>
          <div
            className="truncate mt-1"
            style={{ fontSize: 12, color: "var(--color-muted)" }}
          >
            {email}
          </div>
          {me?.taste_type && (
            <div className="mt-2">
              <span
                className="chip"
                style={{
                  height: 24,
                  fontSize: 11.5,
                  color: "var(--color-olive-700)",
                  gap: 4,
                }}
              >
                <Sparkles size={12} />
                {me.taste_type}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="px-4 mt-3">
        <div
          className="card flex items-stretch"
          style={{ padding: "14px 0", background: "var(--color-surface-2)" }}
        >
          <StatPill value={stats?.entries_total ?? 0} label="entries" />
          <Divider />
          <StatPill value={stats?.places_total ?? 0} label="places" />
          <Divider />
          <StatPill value={bookmarksCount} label="saved" />
          <Divider />
          <StatPill
            value={
              stats && stats.avg_rating > 0
                ? stats.avg_rating.toFixed(1)
                : "—"
            }
            label="avg"
          />
        </div>
      </div>

      <section className="mt-4">
        <div className="px-4 flex items-baseline justify-between mb-2">
          <h2
            className="leading-tight"
            style={{ fontFamily: "var(--font-serif)", fontSize: 16, fontWeight: 500 }}
          >
            Recent
          </h2>
          <Link
            href="/diary"
            style={{ fontSize: 13, color: "var(--color-olive-700)", fontWeight: 500 }}
          >
            See all
          </Link>
        </div>
        {recent.length === 0 ? (
          <div className="px-4">
            <Link
              href="/capture"
              className="card flex items-center gap-3"
              style={{ padding: 14, color: "var(--color-muted)" }}
            >
              <div
                className="flex items-center justify-center shrink-0"
                style={{ color: "var(--color-olive-700)" }}
              >
                <Camera size={22} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>
                  Log your first meal
                </div>
                <div className="mt-0.5" style={{ fontSize: 12 }}>
                  It only takes a snap.
                </div>
              </div>
            </Link>
          </div>
        ) : (
          <div
            className="flex gap-2"
            style={{ overflowX: "auto", padding: "0 16px 4px" }}
          >
            {recent.map((e) => (
              <Link
                key={e.id}
                href={`/diary/${e.id}`}
                style={{ width: 102, flexShrink: 0 }}
              >
                {e.cover_media_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={e.cover_media_url}
                    alt={e.restaurant.name}
                    width={102}
                    height={102}
                    style={{ width: 102, height: 102, borderRadius: 12, objectFit: "cover" }}
                  />
                ) : (
                  <FoodPlaceholder
                    tone={e.cover_media_tone}
                    label={e.restaurant.signature_dish ?? e.cover_media_label}
                    width={102}
                    height={102}
                    radius={12}
                  />
                )}
                <div
                  className="truncate mt-1.5"
                  style={{
                    fontSize: 11.5,
                    fontFamily: "var(--font-serif)",
                    fontWeight: 500,
                  }}
                >
                  {e.restaurant.name}
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: "var(--color-muted)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {e.rating != null ? `★ ${e.rating.toFixed(1)}` : "no rating"}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="px-4 mt-4">
        <Link
          href="/me/saved"
          className="card flex items-center gap-3.5"
          style={{ padding: "14px 16px" }}
        >
          <Bookmark size={18} strokeWidth={1.7} style={{ color: "var(--color-olive-700)" }} />
          <span style={{ flex: 1, fontSize: 14 }}>Saved restaurants</span>
          <span
            style={{
              fontSize: 12,
              color: "var(--color-muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {bookmarksCount}
          </span>
          <ChevronRight size={16} style={{ color: "var(--color-muted-2)" }} />
        </Link>
      </section>
    </div>
  );
}

function StatPill({ value, label }: { value: number | string; label: string }) {
  return (
    <div
      className="text-center flex flex-col items-center justify-center"
      style={{ flex: "1 1 0", minWidth: 0 }}
    >
      <div
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: 22,
          fontWeight: 500,
          lineHeight: 1,
          fontVariantNumeric: "tabular-nums",
          fontFeatureSettings: '"tnum"',
        }}
      >
        {value}
      </div>
      <div
        className="mt-1"
        style={{
          fontSize: 10.5,
          color: "var(--color-muted)",
          fontFamily: "var(--font-mono)",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function Divider() {
  return (
    <div
      className="self-center shrink-0"
      style={{
        width: 1,
        height: 28,
        background: "var(--color-border-soft)",
      }}
    />
  );
}
