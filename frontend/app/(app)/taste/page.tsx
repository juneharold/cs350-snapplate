"use client";

import Link from "next/link";
import { BookOpen, Camera, Clock, Compass, Sparkles } from "lucide-react";
import { FoodPlaceholder } from "@/components/ui/FoodPlaceholder";
import { useTasteProfile } from "@/lib/api/taste";
import type { FoodTone, TasteProfileResponse } from "@/lib/types";

/**
 * Taste analysis screen. Two states:
 *  • has_enough_data: false → progress bar + "what you'll get" list
 *  • has_enough_data: true  → profile card, summary stats, top categories
 *                             bar chart, time heatmap, radar, top dishes.
 *
 * Bar chart + heatmap are inline SVG/divs — keeping bundle small while
 * the rest of the MVP settles. Recharts swap is a phase-12 polish.
 */
export default function TastePage() {
  const { data, isLoading } = useTasteProfile();

  if (isLoading || !data) {
    return (
      <div className="px-4 pt-16" style={{ color: "var(--color-muted)" }}>
        Loading…
      </div>
    );
  }

  if (!data.has_enough_data) return <TasteEmpty data={data} />;
  return <TasteFull data={data} />;
}

function TasteEmpty({ data }: { data: Extract<TasteProfileResponse, { has_enough_data: false }> }) {
  const pct = Math.round((data.current_entries / data.min_entries_required) * 100);
  const remaining = data.min_entries_required - data.current_entries;
  return (
    <div className="pb-16">
      <header
        className="px-4"
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
          TASTE ANALYSIS
        </div>
        <h1 className="leading-tight font-normal mt-1" style={{ fontSize: 28 }}>
          Almost{" "}
          <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>
            ready.
          </em>
        </h1>
      </header>

      <div className="px-4 mt-5">
        <div className="card" style={{ padding: 18 }}>
          <div className="flex items-baseline justify-between mb-2">
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              PROGRESS
            </div>
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 500 }}>
              {data.current_entries} / {data.min_entries_required} meals
            </div>
          </div>
          <div
            style={{
              height: 8,
              background: "var(--color-bg-soft)",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${Math.min(100, pct)}%`,
                height: "100%",
                background: "var(--color-olive-700)",
                transition: "width 0.3s ease",
              }}
            />
          </div>
          <p
            className="leading-relaxed mt-2"
            style={{ fontSize: 12.5, color: "var(--color-muted)" }}
          >
            Log{" "}
            <b style={{ color: "var(--color-ink)" }}>
              {Math.max(0, remaining)} more meal{remaining === 1 ? "" : "s"}
            </b>{" "}
            and we&apos;ll generate your gastronomic profile. The more variety,
            the better.
          </p>
        </div>

        <div
          className="mt-5 mb-2"
          style={{
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            color: "var(--color-muted)",
            letterSpacing: "0.06em",
          }}
        >
          WHAT YOU&apos;LL GET
        </div>
        <div className="card" style={{ padding: 0 }}>
          {[
            { Icon: Sparkles, title: "A taste type", body: "Like \"The Broth-Seeker\" — a one-line read of how you eat." },
            { Icon: BookOpen, title: "Flavor lean chart", body: "See which of the five tastes you gravitate toward." },
            { Icon: Clock, title: "When-you-eat heatmap", body: "Your dining rhythm across the week." },
            { Icon: Compass, title: "Smarter picks", body: "Recommendations stop being generic, start being yours." },
          ].map((item, i) => (
            <div
              key={item.title}
              className="flex gap-3.5 items-start"
              style={{
                padding: "14px 16px",
                borderTop: i > 0 ? "1px solid var(--color-border-soft)" : "none",
              }}
            >
              <item.Icon
                size={18}
                style={{
                  color: "var(--color-olive-700)",
                  flexShrink: 0,
                  marginTop: 2,
                }}
              />
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 600 }}>{item.title}</div>
                <div
                  className="mt-0.5 leading-snug"
                  style={{ fontSize: 12, color: "var(--color-muted)" }}
                >
                  {item.body}
                </div>
              </div>
            </div>
          ))}
        </div>

        <Link href="/capture" className="btn btn-block mt-4">
          <Camera size={18} />
          Log another meal
        </Link>
      </div>
    </div>
  );
}

function TasteFull({ data }: { data: Extract<TasteProfileResponse, { has_enough_data: true }> }) {
  return (
    <div className="pb-16">
      <header
        className="px-4"
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
          TASTE ANALYSIS · UPDATED{" "}
          {new Date(data.computed_at).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </div>
        <h1 className="leading-tight font-normal mt-1" style={{ fontSize: 28 }}>
          Your gastronomic profile
        </h1>
      </header>

      <section className="px-4 mt-4">
        <div
          className="card"
          style={{
            padding: 18,
            background: "var(--color-olive-700)",
            color: "var(--color-cream)",
            border: "none",
          }}
        >
          <div className="flex justify-between items-start mb-2.5">
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10.5,
                letterSpacing: "0.06em",
                opacity: 0.7,
              }}
            >
              TYPE / 04
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10.5,
                opacity: 0.7,
              }}
            >
              {data.current_entries} entries
            </div>
          </div>
          <div
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 30,
              fontWeight: 400,
              lineHeight: 1,
              fontStyle: "italic",
            }}
          >
            {data.type.label}
          </div>
          <p
            className="mt-2 leading-relaxed"
            style={{ fontSize: 13, opacity: 0.88 }}
          >
            {data.type.blurb}
          </p>
        </div>
      </section>

      <section className="px-4 mt-4 grid grid-cols-2 gap-2">
        <SummaryStat
          value={data.summary.avg_rating.toFixed(1)}
          label="avg rating"
          sub={`${data.summary.avg_rating_delta_month > 0 ? "+" : ""}${data.summary.avg_rating_delta_month.toFixed(1)} vs last month`}
        />
        <SummaryStat
          value={data.summary.places_count.toString()}
          label="unique places"
          sub={`${data.summary.new_places_month} new this month`}
        />
        <SummaryStat
          value={data.current_entries.toString()}
          label="entries"
          sub={`${data.categories.length} categor${data.categories.length === 1 ? "y" : "ies"}`}
        />
        <SummaryStat
          value={data.summary.top_day_of_week.slice(0, 3)}
          label="top day"
          sub="when you log most"
        />
      </section>

      <section className="px-4 mt-4">
        <div className="flex justify-between items-baseline mb-2">
          <h2
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 16,
              fontWeight: 500,
            }}
          >
            Top categories
          </h2>
          <span
            style={{
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
            }}
          >
            BY VISITS
          </span>
        </div>
        <div className="flex flex-col gap-1.5">
          {data.categories.slice(0, 7).map((c) => (
            <CategoryBar key={c.name} name={c.name} weight={c.weight} visits={c.visits} tone={c.tone} />
          ))}
        </div>
      </section>

      <section className="px-4 mt-4">
        <h2
          className="mb-2"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 16,
            fontWeight: 500,
          }}
        >
          When you eat
        </h2>
        <Heatmap rows={data.time_heatmap.rows} cols={data.time_heatmap.cols} data={data.time_heatmap.data} />
        {data.insights[0] && (
          <div
            className="mt-2"
            style={{
              fontSize: 12,
              color: "var(--color-ink-2)",
              lineHeight: 1.5,
            }}
          >
            <b>Insight</b> — {data.insights[0]}
          </div>
        )}
      </section>

      <section className="px-4 mt-4">
        <h2
          className="mb-2"
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 16,
            fontWeight: 500,
          }}
        >
          Flavor lean
        </h2>
        <div className="card flex items-center gap-3.5" style={{ padding: 18 }}>
          <FlavorRadar lean={data.flavor_lean} />
          <div
            className="flex-1"
            style={{ fontSize: 12, lineHeight: 1.55, color: "var(--color-ink-2)" }}
          >
            <FlavorBlurb lean={data.flavor_lean} />
          </div>
        </div>
      </section>

      {data.top_dishes.length > 0 && (
        <section className="px-4 mt-4">
          <h2
            className="mb-2"
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: 16,
              fontWeight: 500,
            }}
          >
            Your top {data.top_dishes.length} dish{data.top_dishes.length === 1 ? "" : "es"}
          </h2>
          <div className="flex gap-2.5">
            {data.top_dishes.map((d) => (
              <div key={d.name} style={{ flex: 1 }}>
                <FoodPlaceholder
                  tone={d.tone as FoodTone}
                  label={d.name}
                  width="100%"
                  height="100%"
                  radius={12}
                  style={{ aspectRatio: "1 / 1.05" }}
                />
                <div
                  className="mt-2"
                  style={{
                    fontSize: 12.5,
                    fontWeight: 500,
                    fontFamily: "var(--font-serif)",
                  }}
                >
                  {d.name}
                </div>
                <div
                  className="mt-0.5"
                  style={{
                    fontSize: 10.5,
                    color: "var(--color-muted)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  ★ {d.rating.toFixed(1)} · {d.visits} visit{d.visits === 1 ? "" : "s"}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div
        className="text-center px-4 mt-5"
        style={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--color-muted)",
        }}
      >
        Updated {new Date(data.computed_at).toLocaleString()}
      </div>
    </div>
  );
}

function SummaryStat({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="card" style={{ padding: 14 }}>
      <div
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: 22,
          fontWeight: 500,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div
        className="mt-1"
        style={{
          fontSize: 11,
          color: "var(--color-muted)",
          fontFamily: "var(--font-mono)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </div>
      <div
        className="mt-1.5"
        style={{ fontSize: 10.5, color: "var(--color-olive-700)" }}
      >
        {sub}
      </div>
    </div>
  );
}

function CategoryBar({
  name,
  weight,
  visits,
  tone,
}: {
  name: string;
  weight: number;
  visits: number;
  tone: FoodTone;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className="shrink-0"
        style={{ width: 90, fontSize: 12.5, color: "var(--color-ink-2)" }}
      >
        {name}
      </div>
      <div
        className="flex-1 relative overflow-hidden"
        style={{
          height: 22,
          background: "var(--color-surface-2)",
          border: "1px solid var(--color-border-soft)",
          borderRadius: 6,
        }}
      >
        <FoodPlaceholder
          tone={tone}
          label=""
          width={`${Math.max(2, weight * 100)}%`}
          height="100%"
          radius={0}
        />
      </div>
      <div
        className="shrink-0 text-right"
        style={{
          width: 28,
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--color-muted)",
        }}
      >
        {visits}
      </div>
    </div>
  );
}

function Heatmap({
  rows,
  cols,
  data,
}: {
  rows: string[];
  cols: string[];
  data: number[][];
}) {
  const max = Math.max(1, ...data.flat());
  return (
    <div className="card" style={{ padding: 14 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `32px repeat(${cols.length}, 1fr)`,
          gap: 4,
          fontSize: 9.5,
          fontFamily: "var(--font-mono)",
          color: "var(--color-muted)",
        }}
      >
        <div />
        {cols.map((c, i) => (
          <div key={i} style={{ textAlign: "center" }}>
            {c}
          </div>
        ))}
        {rows.map((label, rowIdx) => (
          <HeatmapRow
            key={label}
            label={label}
            rowIdx={rowIdx}
            cols={cols}
            cells={data[rowIdx] ?? []}
            max={max}
          />
        ))}
      </div>
    </div>
  );
}

function HeatmapRow({
  label,
  rowIdx,
  cols,
  cells,
  max,
}: {
  label: string;
  rowIdx: number;
  cols: string[];
  cells: number[];
  max: number;
}) {
  return (
    <>
      <div style={{ alignSelf: "center" }}>{label}</div>
      {cols.map((_, i) => {
        const v = cells[i] ?? 0;
        const intensity = v === 0 ? 0 : 0.18 + (v / max) * 0.6;
        return (
          <div
            key={`${rowIdx}-${i}`}
            style={{
              aspectRatio: "1 / 1",
              borderRadius: 4,
              background:
                v === 0
                  ? "var(--color-bg-soft)"
                  : `rgba(63, 74, 44, ${intensity})`,
            }}
          />
        );
      })}
    </>
  );
}

function FlavorRadar({ lean }: { lean: Record<string, number> }) {
  const axes = [
    { label: "Umami", deg: 0, key: "umami" as const },
    { label: "Sweet", deg: 60, key: "sweet" as const },
    { label: "Salty", deg: 120, key: "salty" as const },
    { label: "Sour", deg: 180, key: "sour" as const },
    { label: "Spicy", deg: 240, key: "spicy" as const },
    { label: "Bitter", deg: 300, key: "bitter" as const },
  ];
  const r = 80;
  const point = (deg: number, scale: number) => {
    const a = ((deg - 90) * Math.PI) / 180;
    return [100 + r * scale * Math.cos(a), 100 + r * scale * Math.sin(a)];
  };
  const ringPoints = (scale: number) =>
    axes.map((a) => point(a.deg, scale).join(",")).join(" ");
  const valuePoints = axes
    .map((a) => point(a.deg, lean[a.key] ?? 0).join(","))
    .join(" ");
  return (
    <svg width="140" height="140" viewBox="0 0 200 200">
      {[1, 0.75, 0.5, 0.25].map((s) => (
        <polygon
          key={s}
          points={ringPoints(s)}
          fill="none"
          stroke="var(--color-border-strong)"
          strokeWidth="1"
        />
      ))}
      <polygon
        points={valuePoints}
        fill="rgba(63, 74, 44, 0.32)"
        stroke="var(--color-olive-700)"
        strokeWidth="2"
      />
      {axes.map((a) => {
        const [x, y] = point(a.deg, 1.2);
        return (
          <text
            key={a.label}
            x={x}
            y={y}
            fontFamily="var(--font-sans)"
            fontSize="11"
            fontWeight="500"
            fill="var(--color-ink-2)"
            textAnchor="middle"
            dy="3"
          >
            {a.label}
          </text>
        );
      })}
    </svg>
  );
}

function FlavorBlurb({ lean }: { lean: Record<string, number> }) {
  const ranked = Object.entries(lean).sort((a, b) => b[1] - a[1]);
  const top = ranked[0]?.[0];
  const second = ranked[1]?.[0];
  const lowest = ranked[ranked.length - 1]?.[0];
  return (
    <>
      Strongly leaning{" "}
      <b style={{ color: "var(--color-olive-700)" }}>{top}</b>
      {second ? (
        <>
          {" "}and <b style={{ color: "var(--color-olive-700)" }}>{second}</b>
        </>
      ) : null}
      . Low on {lowest} — that&apos;s your taste edge.
    </>
  );
}
