import type { ReactNode } from "react";
import { Screen } from "@/components/layout/Screen";
import { Toast } from "@/components/ui/Toast";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <Screen bg="var(--color-surface)">
      {children}
      <Toast />
    </Screen>
  );
}
