import type { ReactNode } from "react";

/**
 * Mobile-only frame.
 *
 * On phones (< 480px) the inner div fills the viewport edge-to-edge.
 * On tablets/laptops we render a centered 390px-wide phone-shaped card
 * (border-radius + black bezel) so reviewers see the app the way it's
 * meant to be experienced.
 *
 * Children get `height: 100dvh` so the bottom tab bar always sits above
 * the iOS Safari URL bar.
 */
export function PhoneFrame({ children }: { children: ReactNode }) {
  return <div className="phone-frame">{children}</div>;
}
