"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Camera, Send } from "lucide-react";
import { useUpdateMe } from "@/lib/api/auth";
import { useAuth } from "@/lib/store/auth";
import { ApiException } from "@/lib/api/client";

const schema = z.object({
  nickname: z
    .string()
    .trim()
    .min(1, "Pick something we can call you.")
    .max(20, "Up to 20 characters."),
});
type FormValues = z.infer<typeof schema>;

/**
 * Profile setup — sets the user's nickname via PATCH /me. After save
 * we flip `hasSeenOnboarding` and drop them on the home screen.
 *
 * Avatar upload (POST /me/avatar) is intentionally deferred to a later
 * phase — for now the avatar shows the first letter of the nickname.
 */
export default function SetupPage() {
  const router = useRouter();
  const update = useUpdateMe();
  const email = useAuth((s) => s.user?.email ?? "");
  const setHasSeenOnboarding = useAuth((s) => s.setHasSeenOnboarding);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid },
    setError,
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: { nickname: "" },
  });

  const nickname = watch("nickname") ?? "";
  const firstLetter = (nickname.trim().charAt(0) || email.charAt(0) || "?").toUpperCase();

  const onSubmit = handleSubmit(async (values) => {
    try {
      await update.mutateAsync({ nickname: values.nickname.trim() });
      setHasSeenOnboarding(true);
      router.replace("/");
    } catch (e) {
      if (e instanceof ApiException) {
        setError("nickname", { message: e.message });
      } else {
        setError("nickname", { message: "Couldn't save that just yet — try again." });
      }
    }
  });

  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col h-full px-7"
      style={{
        paddingTop: 64,
        paddingBottom: 56,
        boxSizing: "border-box",
      }}
    >
      {/* Progress dots — step 2 of 3 to match the prototype */}
      <div className="flex gap-1.5 justify-center" style={{ marginBottom: 40 }}>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              width: i === 1 ? 22 : 6,
              height: 6,
              borderRadius: 3,
              background:
                i <= 1
                  ? "var(--color-olive-700)"
                  : "var(--color-border-strong)",
            }}
          />
        ))}
      </div>

      {/* Main form content - scrollable on small screens */}
      <div className="flex-1 overflow-y-auto" style={{ minHeight: 0, marginBottom: 20 }}>
        <div
          style={{
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            color: "var(--color-muted)",
            letterSpacing: "0.08em",
            marginBottom: 10,
          }}
        >
          STEP 02 / 03 · ALMOST IN
        </div>
        <h1 className="text-[30px] leading-[1.1] font-normal mb-2.5">
          What should we{" "}
          <em style={{ color: "var(--color-olive-700)" }}>call you?</em>
        </h1>
        <p
          className="leading-relaxed"
          style={{ fontSize: 14, color: "var(--color-muted)" }}
        >
          This is how your diary will greet you. You can change it later.
        </p>

        <div className="flex justify-center mt-5 mb-3">
          <div className="relative">
            <div
              className="avatar"
              style={{ width: 96, height: 96, fontSize: 38, lineHeight: 1 }}
            >
              <span className="avatar-letter">{firstLetter}</span>
            </div>
            <button
              type="button"
              aria-label="Upload avatar"
              className="flex items-center justify-center"
              style={{
                position: "absolute",
                bottom: 0,
                right: 0,
                width: 32,
                height: 32,
                borderRadius: 999,
                background: "var(--color-olive-700)",
                color: "var(--color-cream)",
                border: "2px solid var(--color-surface)",
              }}
            >
              <Camera size={14} />
            </button>
          </div>
        </div>

        <div>
          <div className="flex justify-between items-baseline mb-2">
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted)",
                letterSpacing: "0.06em",
              }}
            >
              NICKNAME
            </div>
            <div
              style={{
                fontSize: 10.5,
                fontFamily: "var(--font-mono)",
                color: "var(--color-muted-2)",
              }}
            >
              {nickname.length} / 20
            </div>
          </div>
          <input
            {...register("nickname")}
            type="text"
            autoFocus
            maxLength={20}
            placeholder="Nickname"
            className="input"
            style={{
              height: 52,
              fontSize: 18,
              fontFamily: "var(--font-serif)",
            }}
          />
          <div
            className="mt-2 leading-relaxed"
            style={{
              fontSize: 11.5,
              color: errors.nickname ? "var(--color-danger)" : "var(--color-muted)",
            }}
          >
            {errors.nickname?.message ?? "Up to 20 characters."}
          </div>
        </div>

        <div
          className="mt-3 flex items-center gap-3 p-3"
          style={{ background: "var(--color-bg-soft)", borderRadius: 12 }}
        >
          <span
            className="flex items-center justify-center shrink-0"
            style={{ color: "var(--color-olive-700)" }}
          >
            <Send size={16} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="truncate" style={{ fontSize: 12.5, fontWeight: 500 }}>
              {email}
            </div>
            <div
              style={{
                fontSize: 11,
                color: "var(--color-muted)",
                fontFamily: "var(--font-mono)",
              }}
            >
              verified · signed in
            </div>
          </div>
        </div>
      </div>

      <div className="w-full">
        <button
          type="submit"
          className="btn btn-block"
          disabled={!isValid || update.isPending}
        >
          {update.isPending ? "Saving…" : "Continue →"}
        </button>
      </div>
    </form>
  );
}
