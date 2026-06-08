import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

/**
 * Reusable shell for the static Support documents (Terms, Privacy, What's
 * new) reached from Settings. Mirrors the sub-page header pattern used
 * elsewhere — a back chevron returning to Settings, a mono eyebrow, a serif
 * title, and a readable prose column.
 */
export function DocScreen({
  eyebrow,
  title,
  updated,
  children,
}: {
  eyebrow: string;
  title: string;
  updated?: string;
  children: ReactNode;
}) {
  return (
    <div className="pb-16">
      <header
        className="px-4"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 24px)" }}
      >
        <Link
          href="/me/settings"
          aria-label="Back to settings"
          className="flex items-center justify-center"
          style={{ width: 40, height: 40, color: "var(--color-ink)", marginLeft: -8 }}
        >
          <ChevronLeft size={22} />
        </Link>
      </header>

      <div className="px-5 mt-1">
        <div
          style={{
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            color: "var(--color-muted)",
            letterSpacing: "0.08em",
          }}
        >
          {eyebrow}
        </div>
        <h1
          className="leading-tight font-normal mt-1"
          style={{ fontFamily: "var(--font-serif)", fontSize: 28 }}
        >
          {title}
        </h1>
        {updated && (
          <div
            className="mt-1.5"
            style={{
              fontSize: 11.5,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted-2)",
            }}
          >
            {updated}
          </div>
        )}

        <div
          className="mt-6"
          style={{ fontSize: 14, lineHeight: 1.6, color: "var(--color-ink-2)" }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

/** A titled block within a DocScreen. */
export function DocSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ marginBottom: 22 }}>
      <h2
        style={{
          fontFamily: "var(--font-serif)",
          fontSize: 16,
          fontWeight: 600,
          color: "var(--color-ink)",
          marginBottom: 6,
        }}
      >
        {title}
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{children}</div>
    </section>
  );
}
