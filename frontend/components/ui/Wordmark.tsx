type Props = {
  size?: number;
  color?: string;
  showText?: boolean;
};

/**
 * The SnapPlate wordmark — a tilted teardrop pin + serif text. Pulled
 * straight from the prototype's `Wordmark` component.
 */
export function Wordmark({
  size = 22,
  color = "var(--color-olive-700)",
  showText = true,
}: Props) {
  return (
    <span
      style={{
        fontFamily: "var(--font-serif)",
        fontSize: size,
        fontWeight: 500,
        letterSpacing: "-0.015em",
        color,
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
      }}
    >
      <span
        style={{
          width: size * 0.55,
          height: size * 0.55,
          borderRadius: "50% 50% 50% 0",
          background: color,
          transform: "rotate(-45deg)",
          display: "inline-block",
        }}
      />
      {showText && "SnapPlate"}
    </span>
  );
}

/**
 * Larger boxed-version used on the login screen + startup splash.
 */
export function WordmarkBadge({
  size = 72,
  color = "var(--color-olive-700)",
  innerColor = "var(--color-surface)",
}: {
  size?: number;
  color?: string;
  innerColor?: string;
}) {
  const innerInset = size * 0.19;
  const dotInset = size * 0.3;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50% 50% 50% 0",
        background: color,
        transform: "rotate(-45deg)",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: innerInset,
          borderRadius: "50%",
          background: innerColor,
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: dotInset,
          borderRadius: "50%",
          background: color,
        }}
      />
    </div>
  );
}
