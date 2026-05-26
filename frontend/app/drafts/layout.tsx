import type { ReactNode } from "react";
import { AuthGate } from "@/components/layout/AuthGate";

/**
 * `/drafts/*` shares the same auth gate as the (app) group but doesn't
 * render a tab bar — drafts are a flow, not a top-level destination.
 */
export default function DraftsLayout({ children }: { children: ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
