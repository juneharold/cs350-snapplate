"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronLeft, Send } from "lucide-react";
import { useVerifyToken } from "@/lib/api/auth";
import { useAuth } from "@/lib/store/auth";
import { WordmarkBadge } from "@/components/ui/Wordmark";
import { ApiException } from "@/lib/api/client";

/**
 * "Check your inbox" screen.
 *
 * For the MVP we fake the email tap with a button — POST /auth/verify
 * with the token MSW handed us on the previous step. New users go to
 * /onboarding; returning users to /.
 */
export default function EmailSentPage() {
  const router = useRouter();
  const verify = useVerifyToken();
  const setHasSeenOnboarding = useAuth((s) => s.setHasSeenOnboarding);
  const [email, setEmail] = useState<string | null>(null);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEmail(sessionStorage.getItem("snapplate.last-magic-email"));
    setLinkToken(sessionStorage.getItem("snapplate.last-magic-token"));
  }, []);

  async function tapLink() {
    if (!linkToken) {
      setError("No pending sign-in link. Send a new one.");
      return;
    }
    setError(null);
    try {
      const data = await verify.mutateAsync(linkToken);
      sessionStorage.removeItem("snapplate.last-magic-token");
      if (data.user.is_new) {
        setHasSeenOnboarding(false);
        router.replace("/onboarding");
      } else {
        setHasSeenOnboarding(true);
        router.replace("/");
      }
    } catch (e) {
      setError(e instanceof ApiException ? e.message : "That link didn't work.");
    }
  }

  return (
    <>
      <div className="absolute top-14 left-4 right-4 flex items-center gap-2">
        <Link
          href="/email"
          className="flex items-center justify-center"
          style={{ width: 40, height: 40, color: "var(--color-ink)" }}
          aria-label="Back"
        >
          <ChevronLeft size={22} />
        </Link>
      </div>

      <div className="absolute left-7 right-7" style={{ top: 130 }}>
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
          <Send size={28} strokeWidth={1.4} />
        </div>
        <h1 className="text-[28px] leading-[1.15] font-normal mb-3">
          Check your <em style={{ color: "var(--color-olive-700)" }}>inbox.</em>
        </h1>
        <p
          className="text-[14.5px] leading-relaxed"
          style={{ color: "var(--color-muted)" }}
        >
          We sent a sign-in link to{" "}
          <b style={{ color: "var(--color-ink)" }}>{email ?? "your inbox"}</b>.
          Tap it from your phone to come back here, signed in.
        </p>

        <div
          className="card mt-5 flex items-start gap-3 p-3.5"
        >
          <div
            className="flex items-center justify-center shrink-0"
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "var(--color-olive-700)",
            }}
          >
            <WordmarkBadge size={20} innerColor="var(--color-cream)" color="var(--color-cream)" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline justify-between gap-2">
              <div style={{ fontSize: 13, fontWeight: 600 }}>SnapPlate</div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--color-muted)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                now
              </div>
            </div>
            <div className="mt-0.5" style={{ fontSize: 13.5, fontWeight: 600 }}>
              Your sign-in link
            </div>
            <div
              className="mt-0.5 leading-snug"
              style={{ fontSize: 12, color: "var(--color-muted)" }}
            >
              Tap the button inside to finish signing in. The link expires in 15
              minutes.
            </div>
          </div>
        </div>

        <div
          className="mt-5 leading-relaxed"
          style={{ fontSize: 12.5, color: "var(--color-muted)" }}
        >
          MVP shortcut: we don&apos;t actually send email yet. Hit the button
          below to simulate tapping the link.
        </div>
        {error && (
          <div className="mt-3" style={{ fontSize: 13, color: "var(--color-danger)" }}>
            {error}
          </div>
        )}
      </div>

      <div className="absolute left-7 right-7 flex flex-col gap-2" style={{ bottom: 48 }}>
        <button
          className="btn btn-block"
          onClick={tapLink}
          disabled={verify.isPending || !linkToken}
        >
          {verify.isPending ? "Signing you in…" : "Tap the magic link"}
        </button>
        <Link
          href="/email"
          className="btn btn-block btn-ghost"
          style={{ color: "var(--color-muted)", height: 38, fontSize: 13 }}
        >
          Use a different email
        </Link>
      </div>
    </>
  );
}
