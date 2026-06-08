import { DocScreen, DocSection } from "@/components/layout/DocScreen";

export const metadata = { title: "Privacy Policy · SnapPlate" };

export default function PrivacyPage() {
  return (
    <DocScreen eyebrow="SUPPORT" title="Privacy Policy" updated="Last updated · Jun 7, 2026">
      <p style={{ marginBottom: 22 }}>
        SnapPlate is a private food diary first. Your entries are for you — they&apos;re
        never shared or sold. This page explains what we collect and why, in plain
        terms. SnapPlate is a KAIST CS350 student project.
      </p>

      <DocSection title="What we collect">
        <p>
          <b>Account:</b> your email address, a nickname, and an optional profile photo.
          <br />
          <b>Content you create:</b> meal photos, ratings, and notes.
          <br />
          <b>Location:</b> the GPS coordinates attached when you capture a photo — read
          from your device or the photo&apos;s EXIF — used to tag where you ate.
          <br />
          <b>Basic technical data:</b> standard request logs needed to operate and debug
          the service.
        </p>
      </DocSection>

      <DocSection title="How we use it">
        <p>
          We use your data only to run SnapPlate: to store your diary, build photo
          thumbnails, label the place you ate, generate your taste analysis, and send
          the reminders and notifications you&apos;ve turned on. We don&apos;t use it for
          advertising.
        </p>
      </DocSection>

      <DocSection title="Location is optional">
        <p>
          Location is only read when you capture a photo and allow it. It&apos;s used to
          name the place near you. You can deny location access in your browser or in
          Settings — SnapPlate still works, your entries just won&apos;t be place-tagged.
        </p>
      </DocSection>

      <DocSection title="Where your data lives">
        <p>
          Photos are kept in object storage and served through short-lived signed links;
          your account and entry data live in the project&apos;s database. Access is
          limited to what&apos;s needed to operate the app.
        </p>
      </DocSection>

      <DocSection title="Sharing">
        <p>
          We don&apos;t sell your data and we don&apos;t share your private entries. Your
          drafts and diary entries are visible only to you by default.
        </p>
      </DocSection>

      <DocSection title="Your choices">
        <p>
          Manage notification preferences and app permissions anytime in Settings.
          Deleting your account from Settings immediately and permanently removes your
          drafts, entries, and bookmarks.
        </p>
      </DocSection>

      <DocSection title="Retention">
        <p>
          We keep your data until you delete it or remove your account. As a course
          project, SnapPlate may also be wound down, after which stored data is removed.
        </p>
      </DocSection>

      <DocSection title="Contact">
        <p>
          Privacy questions? Email{" "}
          <a href="mailto:support@snapplate.app" style={{ color: "var(--color-olive-700)" }}>
            support@snapplate.app
          </a>
          .
        </p>
      </DocSection>
    </DocScreen>
  );
}
