"use client";

import { useToast } from "@/lib/store/toast";

/**
 * Single-line toast pinned just above the tab bar. Rendered from the
 * (app) layout so any authed screen can call `useToast().show(...)`.
 */
export function Toast() {
  const message = useToast((s) => s.message);
  if (!message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="absolute left-0 right-0 flex justify-center pointer-events-none z-20"
      style={{ bottom: "calc(94px + env(safe-area-inset-bottom, 0px))" }}
    >
      <div
        className="card pointer-events-auto"
        style={{
          padding: "10px 16px",
          fontSize: 13,
          fontWeight: 500,
          borderRadius: 999,
          background: "var(--color-olive-700)",
          color: "var(--color-cream)",
          borderColor: "var(--color-olive-700)",
          boxShadow: "0 8px 24px rgba(31,31,25,0.18)",
          animation: "snapplate-toast-in 0.2s ease-out",
        }}
      >
        {message}
      </div>
      <style>{`@keyframes snapplate-toast-in { from { transform: translateY(8px); opacity: 0 } to { transform: none; opacity: 1 } }`}</style>
    </div>
  );
}
