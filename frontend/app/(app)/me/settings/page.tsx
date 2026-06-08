"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { Bell, BookOpen, Camera, ChevronLeft, ChevronRight, Compass, Image as ImageIcon, MapPin, Send, Sparkles, Sun, User, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/store/auth";
import { useLogout, useMe, useUpdateMe, useUploadAvatar } from "@/lib/api/auth";
import { useSettings, useUpdateSettings } from "@/lib/api/settings";
import { useToast } from "@/lib/store/toast";
import { ApiException } from "@/lib/api/client";
import type { SettingsResponse } from "@/lib/types";

const AVATAR_MAX_BYTES = 10 * 1024 * 1024;
const AVATAR_TYPES = ["image/jpeg", "image/png"];

const APP_VERSION = "v0.1.0";
const SUPPORT_MAILTO = `mailto:support@snapplate.app?subject=${encodeURIComponent(
  `SnapPlate support · ${APP_VERSION}`,
)}`;

/**
 * Settings screen — list-of-rows pattern, grouped by section.
 *
 * Notification toggles flow through `PATCH /settings`. The Nickname row
 * opens an edit sheet that saves through `PATCH /me`; the Email row stays
 * read-only since it's the account identity.
 */
export default function SettingsPage() {
  const router = useRouter();
  const { data: me } = useMe();
  const { data: settings } = useSettings();
  const update = useUpdateSettings();
  const updateMe = useUpdateMe();
  const upload = useUploadAvatar();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const localUser = useAuth((s) => s.user);
  const logout = useLogout();
  const accessToken = useAuth((s) => s.accessToken);
  const showToast = useToast((s) => s.show);
  const [confirming, setConfirming] = useState<"logout" | "delete" | null>(null);
  const [editingNickname, setEditingNickname] = useState(false);

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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file after an error
    if (!file) return;
    if (file.type && !AVATAR_TYPES.includes(file.type)) {
      showToast("Please choose a JPEG or PNG image.");
      return;
    }
    if (file.size > AVATAR_MAX_BYTES) {
      showToast("That image is over 10MB — pick a smaller one.");
      return;
    }
    try {
      await upload.mutateAsync(file);
    } catch (err) {
      showToast(err instanceof ApiException ? err.message : "Couldn't upload that photo.");
    }
  };

  return (
    <div className="pb-12">
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/jpeg,image/png"
        style={{ display: "none" }}
      />

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
        <Row
          Icon={User}
          label="Nickname"
          value={nickname}
          right="chev"
          onClick={() => setEditingNickname(true)}
        />
        <Row Icon={Send} label="Email" value={email} last />
        <Row
          Icon={upload.isPending ? Loader2 : ImageIcon}
          label={upload.isPending ? "Uploading..." : "Profile photo"}
          right="chev"
          onClick={() => fileInputRef.current?.click()}
          last
        />
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
        <PermissionRow
          Icon={MapPin}
          label="Location"
          name="geolocation"
          requester={requestGeolocation}
        />
        <PermissionRow Icon={Camera} label="Camera" name="camera" requester={requestCamera} last />
        <Row Icon={ImageIcon} label="Photos" value="On request" last />
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
        <Row
          Icon={Send}
          label="Contact support"
          right="chev"
          onClick={() => {
            window.location.href = SUPPORT_MAILTO;
          }}
        />
        <Row
          Icon={BookOpen}
          label="Terms of service"
          right="chev"
          onClick={() => router.push("/me/settings/terms")}
        />
        <Row
          Icon={BookOpen}
          label="Privacy policy"
          right="chev"
          onClick={() => router.push("/me/settings/privacy")}
        />
        <Row
          Icon={Sparkles}
          label="What's new"
          value={APP_VERSION}
          right="chev"
          onClick={() => router.push("/me/settings/whats-new")}
          last
        />
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
        SnapPlate · {APP_VERSION} · Made at KAIST
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

      {editingNickname && (
        <EditNicknameSheet
          current={me?.nickname ?? localUser?.nickname ?? ""}
          saving={updateMe.isPending}
          onCancel={() => setEditingNickname(false)}
          onSave={async (value) => {
            try {
              await updateMe.mutateAsync({ nickname: value });
              setEditingNickname(false);
            } catch (err) {
              showToast(
                err instanceof ApiException ? err.message : "Couldn't save that nickname.",
              );
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
      {right === "chev" && toggle === undefined && !danger && (
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

/* ── Privacy & permissions ──────────────────────────────────────────────
 * Real browser permission state instead of hardcoded labels. We read the
 * live state via the Permissions API (where supported) and let a tap fire
 * the actual prompt — getCurrentPosition for location, getUserMedia for the
 * camera. Browsers without `permissions.query` (notably Safari for camera)
 * skip the read and stay tappable, requesting directly on press.
 */
type PermName = "geolocation" | "camera";
type PermState = "granted" | "denied" | "prompt";

function usePermission(name: PermName) {
  const [state, setState] = useState<PermState>("prompt");
  useEffect(() => {
    let cancelled = false;
    let status: PermissionStatus | null = null;
    const sync = () => {
      if (status && !cancelled) setState(status.state as PermState);
    };
    (async () => {
      if (typeof navigator === "undefined" || !navigator.permissions?.query) return;
      try {
        status = await navigator.permissions.query({ name: name as PermissionName });
        sync();
        status.addEventListener("change", sync);
      } catch {
        // e.g. Firefox/Safari reject the "camera" descriptor — stay tappable.
      }
    })();
    return () => {
      cancelled = true;
      status?.removeEventListener("change", sync);
    };
  }, [name]);
  return [state, setState] as const;
}

async function requestGeolocation(): Promise<PermState> {
  if (typeof navigator === "undefined" || !navigator.geolocation) return "prompt";
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      () => resolve("granted"),
      // Only an explicit PERMISSION_DENIED (code 1) is a real block. A timeout
      // (code 3) or position-unavailable (code 2) means we couldn't get a fix,
      // not that the user denied us — leave the row on "Tap to allow".
      (err) => resolve(err.code === err.PERMISSION_DENIED ? "denied" : "prompt"),
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    );
  });
}

async function requestCamera(): Promise<PermState> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) return "prompt";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    stream.getTracks().forEach((t) => t.stop()); // release immediately; we only wanted the grant
    return "granted";
  } catch {
    return "denied";
  }
}

function PermissionRow({
  Icon,
  label,
  name,
  requester,
}: {
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number; style?: React.CSSProperties }>;
  label: string;
  name: PermName;
  requester: () => Promise<PermState>;
  last?: boolean;
}) {
  const [state, setState] = usePermission(name);
  const [busy, setBusy] = useState(false);
  const showToast = useToast((s) => s.show);

  const valueLabel =
    state === "granted" ? "Allowed" : state === "denied" ? "Blocked" : "Tap to allow";
  const valueColor =
    state === "granted"
      ? "var(--color-olive-700)"
      : state === "denied"
        ? "var(--color-danger)"
        : "var(--color-muted)";

  async function handleClick() {
    if (busy) return;
    if (state === "granted") {
      showToast(`${label} access is already on.`);
      return;
    }
    if (state === "denied") {
      showToast(`${label} is blocked — turn it back on in your browser's site settings.`);
      return;
    }
    setBusy(true);
    const result = await requester();
    setBusy(false);
    setState(result);
    if (result === "denied") {
      showToast(`${label} permission wasn't granted.`);
    } else if (result === "prompt") {
      showToast(`Couldn't reach ${label.toLowerCase()} — try again.`);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="flex items-center gap-3.5 w-full text-left"
      style={{ padding: "13px 16px", color: "var(--color-ink)", background: "transparent" }}
    >
      <Icon size={18} strokeWidth={1.6} style={{ color: "var(--color-olive-700)", flexShrink: 0 }} />
      <span style={{ flex: 1, fontSize: 14 }}>{label}</span>
      {busy ? (
        <Loader2 size={15} className="animate-spin" style={{ color: "var(--color-muted)" }} />
      ) : (
        <span style={{ fontSize: 12.5, color: valueColor }}>{valueLabel}</span>
      )}
    </button>
  );
}

const NICKNAME_MAX = 20;

function EditNicknameSheet({
  current,
  saving,
  onSave,
  onCancel,
}: {
  current: string;
  saving: boolean;
  onSave: (value: string) => void;
  onCancel: () => void;
}) {
  const [value, setValue] = useState(current);
  const trimmed = value.trim();
  const invalid = trimmed.length === 0 || trimmed.length > NICKNAME_MAX;

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
      <form
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          if (!invalid && !saving) onSave(trimmed);
        }}
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
        <div className="flex justify-between items-baseline mb-2">
          <h2 style={{ fontFamily: "var(--font-serif)", fontSize: 19, fontWeight: 600 }}>
            Edit nickname
          </h2>
          <span
            style={{
              fontSize: 10.5,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted-2)",
            }}
          >
            {trimmed.length} / {NICKNAME_MAX}
          </span>
        </div>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="input"
          placeholder="Nickname"
          maxLength={NICKNAME_MAX}
          autoFocus
        />
        <div className="flex gap-2 mt-4">
          <button type="button" onClick={onCancel} className="btn btn-secondary" style={{ flex: 1 }}>
            Cancel
          </button>
          <button type="submit" disabled={invalid || saving} className="btn" style={{ flex: 1 }}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
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
