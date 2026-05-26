import type { CSSProperties, ReactNode } from "react";

/**
 * Phone-screen wrapper used inside the phone frame.
 *
 * Sets a tinted background and creates a positioning context so screen
 * children can use `absolute` positioning the way the prototype does.
 */
export function Screen({
  children,
  bg = "var(--color-bg)",
  style,
  className,
}: {
  children: ReactNode;
  bg?: string;
  style?: CSSProperties;
  className?: string;
}) {
  return (
    <div
      className={className}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        background: bg,
        overflow: "hidden",
        ...style,
      }}
    >
      {children}
    </div>
  );
}
