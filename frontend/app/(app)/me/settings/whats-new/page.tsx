import { DocScreen } from "@/components/layout/DocScreen";

export const metadata = { title: "What's New · SnapPlate" };

type Release = { version: string; name: string; date: string; items: string[] };

const RELEASES: Release[] = [
  {
    version: "v0.1.0",
    name: "First taste",
    date: "Jun 2026",
    items: [
      "Capture flow with a live camera viewfinder and gallery fallback",
      "Save photos as private drafts now, add the rating and notes later",
      "Automatic place tagging from your photo's location",
      "Ratings, notes, and a per-meal taste profile",
      "Discover nearby restaurants and bookmark the ones you love",
      "Passwordless sign-in with an emailed magic link",
      "Profile, notifications, and permission controls in Settings",
    ],
  },
];

export default function WhatsNewPage() {
  return (
    <DocScreen eyebrow="SUPPORT" title="What's New" updated="SnapPlate · v0.1.0">
      <p style={{ marginBottom: 24 }}>
        The very first release of SnapPlate — a private food diary that remembers the
        place and time so you can focus on the meal.
      </p>

      {RELEASES.map((r) => (
        <section key={r.version} style={{ marginBottom: 26 }}>
          <div className="flex items-baseline gap-2" style={{ marginBottom: 4 }}>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "var(--color-olive-700)",
                fontWeight: 600,
              }}
            >
              {r.version}
            </span>
            <h2
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: 17,
                fontWeight: 600,
                color: "var(--color-ink)",
              }}
            >
              {r.name}
            </h2>
            <span
              style={{
                marginLeft: "auto",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-muted-2)",
              }}
            >
              {r.date}
            </span>
          </div>
          <ul style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
            {r.items.map((item) => (
              <li key={item} className="flex gap-2.5" style={{ alignItems: "flex-start" }}>
                <span
                  aria-hidden
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: 999,
                    background: "var(--color-olive-700)",
                    flexShrink: 0,
                    marginTop: 8,
                  }}
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </DocScreen>
  );
}
