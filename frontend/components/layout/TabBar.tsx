"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, BookOpen, Camera, Sparkles, User } from "lucide-react";
import clsx from "clsx";

/**
 * Bottom tab bar — 5 slots with a centered camera FAB.
 *
 * The capture FAB intentionally lives outside the authed (app) route
 * group (it's at /capture) so it can render a fullscreen black sheet
 * over the camera view without the tab bar.
 */
type TabId = "explore" | "diary" | "capture" | "taste" | "me";

function activeFromPath(pathname: string): TabId | null {
  if (pathname === "/" || pathname.startsWith("/restaurants") || pathname.startsWith("/search"))
    return "explore";
  if (pathname.startsWith("/diary") || pathname.startsWith("/drafts")) return "diary";
  if (pathname.startsWith("/taste")) return "taste";
  if (pathname.startsWith("/me")) return "me";
  if (pathname.startsWith("/capture")) return "capture";
  return null;
}

export function TabBar() {
  const pathname = usePathname();
  const active = activeFromPath(pathname);

  return (
    <nav
      aria-label="Primary"
      className="absolute inset-x-0 bottom-0 z-50 grid grid-cols-5 border-t backdrop-blur"
      style={{
        background: "rgba(250, 246, 234, 0.92)",
        borderTopColor: "rgba(0,0,0,0.06)",
        paddingTop: 8,
        paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 14px)",
        backdropFilter: "blur(20px) saturate(180%)",
        WebkitBackdropFilter: "blur(20px) saturate(180%)",
      }}
    >
      <TabLink href="/" id="explore" active={active} label="Explore" Icon={Compass} />
      <TabLink href="/diary" id="diary" active={active} label="Diary" Icon={BookOpen} />
      <CaptureLink active={active === "capture"} />
      <TabLink href="/taste" id="taste" active={active} label="Taste" Icon={Sparkles} />
      <TabLink href="/me" id="me" active={active} label="Me" Icon={User} />
    </nav>
  );
}

type TabLinkProps = {
  href: string;
  id: TabId;
  active: TabId | null;
  label: string;
  Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>;
};
function TabLink({ href, id, active, label, Icon }: TabLinkProps) {
  const isActive = id === active;
  return (
    <Link
      href={href}
      className={clsx(
        "flex flex-col items-center justify-center gap-[3px] py-1 text-[10.5px] font-medium transition-colors",
        "min-h-[44px]",
        isActive ? "text-olive-900" : "text-muted",
      )}
      style={{
        color: isActive ? "var(--color-olive-900)" : "var(--color-muted)",
        transform: isActive ? "translateY(-1px)" : "none",
      }}
    >
      <Icon size={24} strokeWidth={isActive ? 2.1 : 1.6} />
      <span style={{ fontWeight: isActive ? 700 : 500 }}>{label}</span>
    </Link>
  );
}

function CaptureLink({ active }: { active: boolean }) {
  return (
    <Link
      href="/capture"
      aria-label="Capture a meal"
      className="flex items-center justify-center py-1"
    >
      <span
        className="flex items-center justify-center rounded-full"
        style={{
          width: 56,
          height: 56,
          marginTop: -22,
          background: "var(--color-olive-700)",
          color: "var(--color-cream)",
          boxShadow: "0 6px 20px rgba(63, 74, 44, 0.35)",
          transform: active ? "scale(0.96)" : undefined,
          transition: "transform 0.1s ease",
        }}
      >
        <Camera size={26} strokeWidth={1.6} />
      </span>
    </Link>
  );
}
