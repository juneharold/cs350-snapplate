import type { ReactNode } from "react";
import { Screen } from "@/components/layout/Screen";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <Screen bg="var(--color-surface)">{children}</Screen>;
}
