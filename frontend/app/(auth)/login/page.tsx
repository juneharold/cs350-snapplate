"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { WordmarkBadge } from "@/components/ui/Wordmark";
import { AppleLogo, GoogleLogo } from "@/components/ui/BrandLogos";
import { useAuth } from "@/lib/store/auth";

/**
 * Login screen. Apple / Google are decorative in the MVP — only the
 * "Use email instead" button is wired (to /email which kicks off the
 * magic-link flow described in api-mvp.md §1).
 *
 * If the user is already signed in we bounce them onward — this lets
 * "log out" round-trip without flashing the login screen briefly.
 */
export default function LoginPage() {
  const router = useRouter();
  const accessToken = useAuth((s) => s.accessToken);
  const nickname = useAuth((s) => s.user?.nickname);
  const hasSeenOnboarding = useAuth((s) => s.hasSeenOnboarding);

  useEffect(() => {
    if (!accessToken) return;
    if (!hasSeenOnboarding || !nickname) router.replace("/onboarding");
    else router.replace("/");
  }, [accessToken, hasSeenOnboarding, nickname, router]);

  return (
    <>
      <div className="absolute top-20 left-0 right-0 flex justify-center">
        <WordmarkBadge size={72} />
      </div>

      <div
        className="absolute left-7 right-7 text-center"
        style={{ top: "35%", transform: "translateY(-50%)" }}
      >
        <h1 className="text-[34px] leading-[1.1] font-normal mb-2">Welcome to SnapPlate</h1>
        <p className="text-[14px]" style={{ color: "var(--color-muted)" }}>
          Sign in to start tasting.
        </p>
      </div>

      <div className="absolute left-7 right-7 flex flex-col gap-2.5" style={{ bottom: 56 }}>
        <button
          className="btn btn-block"
          style={{ background: "#1F1F19", color: "var(--color-cream)" }}
          onClick={() => router.push("/email")}
        >
          <AppleLogo size={18} /> Continue with Apple
        </button>
        <button
          className="btn btn-block btn-secondary"
          onClick={() => router.push("/email")}
        >
          <GoogleLogo size={18} /> Continue with Google
        </button>
        <Link
          href="/email"
          className="btn btn-block btn-ghost"
          style={{
            color: "var(--color-olive-700)",
            height: 44,
            fontSize: 13,
          }}
        >
          Use email instead
        </Link>
        <div
          className="text-center leading-relaxed mt-2"
          style={{ fontSize: 11, color: "var(--color-muted-2)" }}
        >
          By continuing you agree to our <u>Terms</u> and <u>Privacy Policy</u>.
        </div>
      </div>
    </>
  );
}
