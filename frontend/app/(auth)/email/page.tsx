"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ChevronLeft, Check } from "lucide-react";
import { useMagicLink } from "@/lib/api/auth";
import { ApiException } from "@/lib/api/client";

const schema = z.object({
  email: z.string().trim().toLowerCase().email("Enter a valid email."),
});
type FormValues = z.infer<typeof schema>;

/**
 * Email entry — submits to POST /auth/magic-link, then navigates to
 * /email/sent. The mock returns a `_mock_link_token` we stash in
 * sessionStorage so the next screen can offer a "tap link" button.
 */
export default function EmailPage() {
  const router = useRouter();
  const magic = useMagicLink();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid },
    setError,
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: { email: "" },
  });

  const onSubmit = handleSubmit(async ({ email }) => {
    try {
      const res = await magic.mutateAsync(email);
      if (res._mock_link_token) {
        sessionStorage.setItem("snapplate.last-magic-token", res._mock_link_token);
      }
      sessionStorage.setItem("snapplate.last-magic-email", email);
      router.push("/email/sent");
    } catch (e) {
      if (e instanceof ApiException) {
        setError("email", { message: e.message });
      } else {
        setError("email", { message: "Something went wrong. Try again." });
      }
    }
  });

  const value = watch("email");

  return (
    <form onSubmit={onSubmit} className="contents">
      <div className="absolute top-14 left-4 right-4 flex items-center gap-2">
        <Link
          href="/login"
          className="flex items-center justify-center"
          style={{ width: 40, height: 40, color: "var(--color-ink)" }}
          aria-label="Back"
        >
          <ChevronLeft size={22} />
        </Link>
      </div>

      <div className="absolute left-7 right-7" style={{ top: 124 }}>
        <h1 className="text-[30px] leading-[1.1] font-normal mb-2.5">
          Your <em style={{ color: "var(--color-olive-700)" }}>email,</em> please.
        </h1>
        <p
          className="text-[14px] leading-relaxed"
          style={{ color: "var(--color-muted)" }}
        >
          We&apos;ll send a one-tap sign-in link. No password to remember.
        </p>

        <div className="mt-7">
          <div
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--color-muted)",
              letterSpacing: "0.06em",
              marginBottom: 8,
            }}
          >
            EMAIL
          </div>
          <div className="relative">
            <input
              {...register("email")}
              type="email"
              inputMode="email"
              autoComplete="email"
              autoFocus
              placeholder="you@example.com"
              className="input"
              style={{ height: 52, fontSize: 16, paddingRight: 44 }}
            />
            {!errors.email && schema.shape.email.safeParse(value).success && (
              <span
                className="absolute"
                style={{
                  right: 14,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--color-success)",
                }}
              >
                <Check size={18} strokeWidth={2.2} />
              </span>
            )}
          </div>
          <div
            className="leading-relaxed"
            style={{
              fontSize: 11.5,
              color: errors.email ? "var(--color-danger)" : "var(--color-muted)",
              marginTop: 8,
            }}
          >
            {errors.email?.message ??
              "We'll create an account if this is your first time."}
          </div>
        </div>
      </div>

      <div className="absolute left-7 right-7" style={{ bottom: 200 }}>
        <button
          type="submit"
          className="btn btn-block"
          disabled={!isValid || magic.isPending}
        >
          {magic.isPending ? "Sending…" : "Send sign-in link"}
        </button>
      </div>
    </form>
  );
}
