import { DocScreen, DocSection } from "@/components/layout/DocScreen";

export const metadata = { title: "Terms of Service · SnapPlate" };

export default function TermsPage() {
  return (
    <DocScreen eyebrow="SUPPORT" title="Terms of Service" updated="Last updated · Jun 7, 2026">
      <p style={{ marginBottom: 22 }}>
        SnapPlate is a student project built for KAIST&apos;s CS350 (Introduction to
        Software Engineering). By creating an account or using the app, you agree to
        these terms. If you don&apos;t agree, please don&apos;t use SnapPlate.
      </p>

      <DocSection title="A course project, not a commercial service">
        <p>
          SnapPlate is provided for learning and demonstration. It may change, break,
          or be taken offline at any time, and there&apos;s no guarantee of uptime,
          backups, or long-term availability. Don&apos;t rely on it as your only copy
          of anything important.
        </p>
      </DocSection>

      <DocSection title="Your account">
        <p>
          You sign in with a one-time magic link sent to your email — there&apos;s no
          password to manage. Keep access to that inbox secure, since anyone who can
          open the link can reach your account. You&apos;re responsible for activity
          under your account.
        </p>
      </DocSection>

      <DocSection title="Acceptable use">
        <p>
          Only upload photos and content that are yours to share. Don&apos;t use
          SnapPlate for anything illegal, abusive, or infringing, and don&apos;t try to
          break, overload, or probe the service or other people&apos;s data.
        </p>
      </DocSection>

      <DocSection title="Your content">
        <p>
          Your meal photos, ratings, and notes stay yours. You grant us only the
          permission needed to run the app — to store your entries, create image
          thumbnails, tag the place, and generate your taste analysis. We don&apos;t
          sell your content or share your private entries.
        </p>
      </DocSection>

      <DocSection title="No warranty &amp; liability">
        <p>
          SnapPlate is provided &ldquo;as is,&rdquo; without warranties of any kind. To
          the extent allowed by law, the project team isn&apos;t liable for any loss or
          damage arising from using — or being unable to use — the app.
        </p>
      </DocSection>

      <DocSection title="Ending your account">
        <p>
          You can delete your account anytime from Settings; this immediately wipes
          your drafts, entries, and bookmarks. We may also suspend or remove accounts
          that misuse the service.
        </p>
      </DocSection>

      <DocSection title="Changes to these terms">
        <p>
          We may update these terms as the project evolves. Continuing to use SnapPlate
          after an update means you accept the revised terms.
        </p>
      </DocSection>

      <DocSection title="Contact">
        <p>
          Questions about these terms? Email{" "}
          <a href="mailto:support@snapplate.app" style={{ color: "var(--color-olive-700)" }}>
            support@snapplate.app
          </a>
          .
        </p>
      </DocSection>
    </DocScreen>
  );
}
