"use client";

import { Star } from "lucide-react";

/**
 * Read-only star row. Half-star precision via two overlapping rows —
 * the gold filled set sits on top of the muted outline set, masked to
 * `(value/max)%` width.
 */
export function StarRow({
  value,
  size = 14,
  max = 5,
}: {
  value: number | null | undefined;
  size?: number;
  max?: number;
}) {
  if (value == null) return null;
  const pct = Math.max(0, Math.min(1, value / max)) * 100;
  return (
    <span
      style={{
        position: "relative",
        display: "inline-block",
        lineHeight: 0,
      }}
    >
      {/* Muted outline base */}
      <span
        style={{
          display: "inline-flex",
          gap: 1,
          color: "var(--color-border-strong)",
        }}
      >
        {Array.from({ length: max }).map((_, i) => (
          <Star key={i} size={size} strokeWidth={1.6} />
        ))}
      </span>
      {/* Gold overlay, clipped to the rating percentage */}
      <span
        aria-hidden
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: "100%",
          width: `${pct}%`,
          overflow: "hidden",
          pointerEvents: "none",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            gap: 1,
            color: "var(--color-rating)",
          }}
        >
          {Array.from({ length: max }).map((_, i) => (
            <Star key={i} size={size} strokeWidth={1.6} fill="currentColor" />
          ))}
        </span>
      </span>
    </span>
  );
}

/**
 * Interactive 0.5-step rating used on the entry form.
 *
 * Each star is split into two tap targets — left half = .5, right half
 * = 1.0 — so users can give half-star ratings without a slider.
 */
export function StarPicker({
  value,
  onChange,
  size = 32,
  max = 5,
}: {
  value: number;
  onChange: (next: number) => void;
  size?: number;
  max?: number;
}) {
  return (
    <div className="flex items-center" role="radiogroup" aria-label="Rating">
      {Array.from({ length: max }).map((_, i) => {
        const star = i + 1;
        const halfFilled = value >= star - 0.5 && value < star;
        const fullFilled = value >= star;
        return (
          <span key={i} style={{ position: "relative", width: size + 4, height: size + 8 }}>
            <span
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color:
                  fullFilled || halfFilled
                    ? "var(--color-rating)"
                    : "var(--color-border-strong)",
                pointerEvents: "none",
              }}
            >
              {fullFilled ? (
                <Star size={size} fill="currentColor" strokeWidth={0} />
              ) : halfFilled ? (
                <HalfStar size={size} />
              ) : (
                <Star size={size} strokeWidth={1.6} />
              )}
            </span>
            <button
              type="button"
              aria-label={`${star - 0.5} of ${max}`}
              onClick={() => onChange(value === star - 0.5 ? 0 : star - 0.5)}
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                width: "50%",
                height: "100%",
                background: "transparent",
              }}
            />
            <button
              type="button"
              aria-label={`${star} of ${max}`}
              onClick={() => onChange(value === star ? 0 : star)}
              style={{
                position: "absolute",
                right: 0,
                top: 0,
                width: "50%",
                height: "100%",
                background: "transparent",
              }}
            />
          </span>
        );
      })}
    </div>
  );
}

function HalfStar({ size }: { size: number }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", width: size, height: size }}>
      <Star size={size} strokeWidth={1.6} />
      <span
        style={{
          position: "absolute",
          inset: 0,
          width: "50%",
          overflow: "hidden",
          color: "var(--color-rating)",
        }}
      >
        <Star size={size} fill="currentColor" strokeWidth={0} />
      </span>
    </span>
  );
}
