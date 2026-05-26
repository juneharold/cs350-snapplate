"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MapPin, Check } from "lucide-react";
import { useAuth, FALLBACK_LOCATION } from "@/lib/store/auth";

const PERKS: Array<[string, string]> = [
  ["Nearby restaurants", "Sorted by walking distance from where you are."],
  ["Auto-tag your diary", "Skip typing — we fill in the place for you."],
  ["Your data, your phone", "Location is never shared with other users."],
];

/**
 * Location permission ask.
 *
 * "Allow" → navigator.geolocation.getCurrentPosition; whatever the
 * browser returns we update the auth store. "Not now" stores false and
 * sets a Daejeon fallback so the home screen still loads with content.
 */
export default function PermissionPage() {
  const router = useRouter();
  const setLocationGranted = useAuth((s) => s.setLocationGranted);
  const setCurrentLocation = useAuth((s) => s.setCurrentLocation);
  const [pending, setPending] = useState(false);

  function next() {
    router.replace("/setup");
  }

  async function allow() {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setLocationGranted(false);
      setCurrentLocation(FALLBACK_LOCATION);
      next();
      return;
    }
    setPending(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocationGranted(true);
        setCurrentLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setPending(false);
        next();
      },
      () => {
        setLocationGranted(false);
        setCurrentLocation(FALLBACK_LOCATION);
        setPending(false);
        next();
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    );
  }

  function skip() {
    setLocationGranted(false);
    setCurrentLocation(FALLBACK_LOCATION);
    next();
  }

  return (
    <>
      <div className="absolute left-7 right-7" style={{ top: 80 }}>
        <div
          className="flex items-center justify-center mb-6"
          style={{
            width: 64,
            height: 64,
            borderRadius: 18,
            background: "var(--color-olive-100)",
            color: "var(--color-olive-700)",
          }}
        >
          <MapPin size={30} strokeWidth={1.4} />
        </div>
        <h1 className="text-[28px] leading-[1.15] font-normal mb-3">
          Where are you{" "}
          <em style={{ color: "var(--color-olive-700)" }}>eating?</em>
        </h1>
        <p
          className="leading-relaxed"
          style={{ fontSize: 14.5, color: "var(--color-muted)" }}
        >
          We use your location to suggest places nearby and tag the meals you
          log. You can turn this off anytime in Settings.
        </p>

        <div className="mt-7 flex flex-col gap-3.5">
          {PERKS.map(([t, b]) => (
            <div key={t} className="flex gap-3">
              <span
                className="flex items-center justify-center shrink-0"
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: 999,
                  background: "var(--color-olive-100)",
                  color: "var(--color-olive-700)",
                  marginTop: 2,
                }}
              >
                <Check size={13} strokeWidth={2.4} />
              </span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{t}</div>
                <div
                  className="mt-0.5"
                  style={{ fontSize: 12.5, color: "var(--color-muted)" }}
                >
                  {b}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="absolute left-7 right-7 flex flex-col gap-2.5" style={{ bottom: 48 }}>
        <button className="btn btn-block" onClick={allow} disabled={pending}>
          {pending ? "Asking…" : "Allow while using the app"}
        </button>
        <button
          className="btn btn-block btn-ghost"
          onClick={skip}
          disabled={pending}
          style={{ color: "var(--color-muted)", height: 42, fontSize: 13 }}
        >
          Not now
        </button>
      </div>
    </>
  );
}
