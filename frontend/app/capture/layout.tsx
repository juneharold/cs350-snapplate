import type { ReactNode } from "react";
import { AuthGate } from "@/components/layout/AuthGate";

/**
 * `/capture/*` lives outside the (app) tab-bar group on purpose — the
 * camera takes the whole viewport. It still needs the same auth gate.
 */
export default function CaptureLayout({ children }: { children: ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
