"use client";

import Link from "next/link";
import { useState } from "react";
import { Bell, BookOpen, Camera, ChevronLeft, ChevronRight, Compass, Image as ImageIcon, MapPin, Send, Sparkles, Sun, User } from "lucide-react";
import { useAuth } from "@/lib/store/auth";
import { useLogout, useMe } from "@/lib/api/auth";
import { useSettings, useUpdateSettings } from "@/lib/api/settings";
import type { SettingsResponse } from "@/lib/types";

/**
 * Settings screen — list-of-rows pattern, grouped by section.
 *
 * Notification toggles flow through `PATCH /settings`. Account-level
 * read-only rows (email, nickname) link back to the profile setup
 * route once we add edit deep-links — for now they're informational.
 */
export default function SettingsPage() {
  const { data: me } = useMe();
  const { data: settings } = useSettings();
  const update = useUpdateSettings();
  const localUser = useAuth((s) => s.user);
  const logout = useLogout();
  const accessToken = useAuth((s) => s.accessToken);
  const [confirming, setConfirming] = useState<"logout" | "delete" | null>(null);

  const nickname = me?.nickname ?? localUser?.nickname ?? "—";
  const email = me?.email ?? localUser?.email ?? "—";

  function toggleNotification(key: keyof SettingsResponse["notifications"]) {
    if (!settings) return;
    update.mutate({
      notifications: { [key]: !settings.notifications[key] },
    });
  }

  function appearanceLabel(v: SettingsResponse["appearance"]): string {
    return v === "light" ? "Light" : v === "dark" ? "Dark" : "System";
  }

  return (
    <div className="pb-12">
      <header
        className="px-4 flex items-center gap-2"
        style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 24px)" }}
      >
        <Link
          href="/me"
          aria-label="Back"
          className="flex items-center justify-center"
          style={{ width: 40, height: 40, color: "var(--color-ink)" }}
        >
          <ChevronLeft size={22} />
        </Link>
        <h1 style={{ fontSize: 22, fontWeight: 500, fontFamily: "var(--font-serif)" }}>
          Settings
        </h1>
      </header>

      <SectionLabel>ACCOUNT</SectionLabel>
      <Group>
        <Row Icon={User} label="Nickname" value={nickname} />
        <Row Icon={Send} label="Email" value={email} last />
        <Row Icon={ImageIcon} label="Profile photo" right="chev" last />
      </Group>

      <SectionLabel>NOTIFICATIONS</SectionLabel>
      <Group>
        <Row
          Icon={Bell}
          label="Meal reminders"
          toggle={settings?.notifications.meal_reminders ?? true}
          onToggle={() => toggleNotification("meal_reminders")}
        />
        <Row
          Icon={Sparkles}
          label="New taste analysis"
          toggle={settings?.notifications.taste_analysis_complete ?? true}
          onToggle={() => toggleNotification("taste_analysis_complete")}
          last
        />
        <Row
          Icon={Compass}
          label="Weekly picks"
          toggle={settings?.notifications.weekly_picks ?? false}
          onToggle={() => toggleNotification("weekly_picks")}
          last
        />
      </Group>

      <SectionLabel>PRIVACY &amp; PERMISSIONS</SectionLabel>
      <Group>
        <Row Icon={MapPin} label="Location" value="While using" />
        <Row Icon={Camera} label="Camera" value="Allowed" last />
        <Row Icon={ImageIcon} label="Photos" value="All photos" last />
      </Group>

      <SectionLabel>PREFERENCES</SectionLabel>
      <Group>
        <Row
          Icon={Sun}
          label="Appearance"
          value={appearanceLabel(settings?.appearance ?? "light")}
        />
      </Group>

      <SectionLabel>SUPPORT</SectionLabel>
      <Group>
        <Row Icon={Send} label="Contact support" right="chev" />
        <Row Icon={BookOpen} label="Terms of service" right="chev" last />
        <Row Icon={BookOpen} label="Privacy policy" right="chev" last />
        <Row Icon={Sparkles} label="What's new" value="v0.1.0" last />
      </Group>

      <div className="flex gap-2 mt-6 px-4">
        <button
          type="button"
          className="btn btn-secondary"
          style={{ flex: 1 }}
          onClick={() => setConfirming("logout")}
        >
          Log out
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ flex: 1, color: "var(--color-danger)" }}
          onClick={() => setConfirming("delete")}
        >
          Delete account
        </button>
      </div>

      <div
        className="text-center mt-4 px-4"
        style={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--color-muted-2)",
        }}
      >
        SnapPlate · v0.1.0 · Made at KAIST
      </div>

      {confirming === "logout" && (
        <ConfirmSheet
          title="Log out?"
          body="You'll need a fresh sign-in link next time."
          confirmLabel={logout.isPending ? "Logging out…" : "Log out"}
          danger
          onCancel={() => setConfirming(null)}
          onConfirm={() => {
            logout.mutate(undefined, {
              onSettled: () => setConfirming(null),
            });
          }}
        />
      )}

      {confirming === "delete" && (
        <ConfirmSheet
          title="Delete account?"
          body={`This wipes your drafts, entries, and bookmarks immediately in this demo build. Type your email (${email}) to confirm.`}
          confirmLabel="Delete forever"
          danger
          requireText={email}
          onCancel={() => setConfirming(null)}
          onConfirm={async () => {
            try {
              const res = await fetch("/v1/account", {
                method: "DELETE",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${accessToken ?? ""}`,
                },
                body: JSON.stringify({ confirm_email: email }),
              });
              if (res.ok) {
                logout.mutate();
              }
            } finally {
              setConfirming(null);
            }
          }}
        />
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="px-4"
      style={{
        fontSize: 11,
        fontFamily: "var(--font-mono)",
        color: "var(--color-muted)",
        letterSpacing: "0.08em",
        margin: "14px 0 6px",
      }}
    >
      {children}
    </div>
  );
}

function Group({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mx-4"
      style={{
        background: "var(--color-surface-2)",
        border: "1px solid var(--color-border-soft)",
        borderRadius: 10,
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

function Row({
  Icon,
  label,
  value,
  toggle,
  onToggle,
  onClick,
  right,
  danger,
  last,
}: {
  Icon?: React.ComponentType<{ size?: number; strokeWidth?: number; style?: React.CSSProperties }>;
  label: string;
  value?: string;
  toggle?: boolean;
  onToggle?: () => void;
  onClick?: () => void;
  right?: "chev";
  danger?: boolean;
  last?: boolean;
}) {
  const interactive = !!(onClick || onToggle);
  const Element = (interactive ? "button" : "div") as "button" | "div";
  return (
    <Element
      onClick={onToggle ?? onClick}
      className="flex items-center gap-3.5 w-full text-left"
      style={{
        padding: "13px 16px",
        color: danger ? "var(--color-danger)" : "var(--color-ink)",
        background: "transparent",
      }}
    >
      {Icon && (
        <Icon
          size={18}
          strokeWidth={1.6}
          style={{
            color: danger ? "var(--color-danger)" : "var(--color-olive-700)",
            flexShrink: 0,
          }}
        />
      )}
      <span style={{ flex: 1, fontSize: 14 }}>{label}</span>
      {value !== undefined && (
        <span style={{ fontSize: 12.5, color: "var(--color-muted)" }}>{value}</span>
      )}
      {toggle !== undefined && <Toggle on={toggle} />}
      {right === "chev" && toggle === undefined && value === undefined && !danger && (
        <ChevronRight size={16} style={{ color: "var(--color-muted-2)" }} />
      )}
    </Element>
  );
}

function Toggle({ on }: { on: boolean }) {
  return (
    <span
      style={{
        width: 38,
        height: 22,
        borderRadius: 999,
        background: on ? "var(--color-olive-700)" : "var(--color-border-strong)",
        position: "relative",
        transition: "background 0.18s",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          position: "absolute",
          top: 2,
          left: on ? 18 : 2,
          width: 18,
          height: 18,
          borderRadius: 999,
          background: "var(--color-surface-2)",
          transition: "left 0.18s",
        }}
      />
    </span>
  );
}

function ConfirmSheet({
  title,
  body,
  confirmLabel,
  onConfirm,
  onCancel,
  danger,
  requireText,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
  requireText?: string;
}) {
  const [text, setText] = useState("");
  const blocked = requireText ? text !== requireText : false;
  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center"
      style={{
        background: "rgba(18,18,20,0.45)",
        backdropFilter: "blur(3px)",
        WebkitBackdropFilter: "blur(3px)",
        padding: 24,
        animation: "snapplate-dialog-fade 0.18s ease both",
      }}
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 320,
          background: "var(--color-surface-2)",
          borderRadius: 16,
          padding: 22,
          boxShadow: "0 24px 60px -16px rgba(0,0,0,0.4)",
          animation: "snapplate-dialog-in 0.2s cubic-bezier(0.2,0.9,0.3,1) both",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: 19,
            fontWeight: 600,
          }}
        >
          {title}
        </h2>
        <p
          className="mt-2 leading-relaxed"
          style={{ fontSize: 13, color: "var(--color-muted)" }}
        >
          {body}
        </p>
        {requireText && (
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="input mt-3"
            placeholder={requireText}
            autoFocus
          />
        )}
        <div className="flex gap-2 mt-4">
          <button
            type="button"
            onClick={onCancel}
            className="btn btn-secondary"
            style={{ flex: 1 }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={blocked}
            className="btn"
            style={{
              flex: 1,
              background: danger ? "var(--color-danger)" : undefined,
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
