import type { CSSProperties } from "react";
import type { FoodTone } from "@/lib/types";

/**
 * Tinted, striped CSS-only food placeholder used until the user uploads
 * real photos. The label sits in the corner in monospace, the tone
 * tints the whole tile via the `[data-tone="..."]` rules in globals.css.
 */
type Props = {
  tone?: FoodTone;
  label?: string;
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  className?: string;
  style?: CSSProperties;
  /** When we DO have a real image URL, render it instead of the placeholder tile. */
  src?: string | null;
  alt?: string;
};

export function FoodPlaceholder({
  tone = "ochre",
  label = "",
  width = "100%",
  height = "100%",
  radius = 12,
  className,
  style,
  src,
  alt,
}: Props) {
  if (src) {
    return (
      <div
        className={className}
        style={{
          width,
          height,
          borderRadius: radius,
          overflow: "hidden",
          position: "relative",
          background: "var(--color-bg-soft)",
          ...style,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={alt ?? label}
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
        />
      </div>
    );
  }
  return (
    <div
      className={`food ${className ?? ""}`}
      data-tone={tone}
      data-label={label}
      style={{ width, height, borderRadius: radius, ...style }}
    >
      {/* Hidden empty span keeps `::before`/`::after` working in browsers
          that strip pseudo-elements off "empty" elements. */}
      <span />
    </div>
  );
}
