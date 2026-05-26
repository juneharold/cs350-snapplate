import type { ReactNode } from "react";
import { TabBar } from "@/components/layout/TabBar";
import { Screen } from "@/components/layout/Screen";
import { AuthGate } from "@/components/layout/AuthGate";
import { Toast } from "@/components/ui/Toast";

/**
 * Layout for the authed tab-bar area.
 *
 * The Screen wrapper creates a positioning context so individual pages
 * can use absolute layouts (matching the prototype). The TabBar pins
 * itself to the bottom with safe-area-aware padding.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <Screen>
        <main
          className="absolute inset-x-0 top-0 overflow-y-auto"
          style={{ bottom: "calc(74px + env(safe-area-inset-bottom, 0px))" }}
        >
          {children}
        </main>
        <Toast />
        <TabBar />
      </Screen>
    </AuthGate>
  );
}
