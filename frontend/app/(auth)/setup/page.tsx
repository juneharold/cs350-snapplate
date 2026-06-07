"use client";

import { useRouter } from "next/navigation";
import { useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Camera, Send, Loader2 } from "lucide-react";
import { useUpdateMe, useUploadAvatar } from "@/lib/api/auth";
import { useAuth } from "@/lib/store/auth";
import { useToast } from "@/lib/store/toast";
import { ApiException } from "@/lib/api/client";

const AVATAR_MAX_BYTES = 10 * 1024 * 1024;
const AVATAR_TYPES = ["image/jpeg", "image/png"];

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
 */
export default function SetupPage() {
  const router = useRouter();
  const update = useUpdateMe();
  const upload = useUploadAvatar();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const user = useAuth((s) => s.user);
  const email = user?.email ?? "";
  const profileImageUrl = user?.profile_image_url;
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

  const showToast = useToast((s) => s.show);

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
      className="flex flex-col"
      style={{
        height: "100%",
        padding:
          "calc(env(safe-area-inset-top, 0px) + 48px) 28px calc(env(safe-area-inset-bottom, 0px) + 40px)",
      }}
    >
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/jpeg,image/png"
        style={{ display: "none" }}
      />

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
              style={{ width: 96, height: 96, fontSize: 38, lineHeight: 1, overflow: "hidden" }}
            >
              {profileImageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profileImageUrl}
                  alt="Avatar"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : (
                <span className="avatar-letter">{firstLetter}</span>
              )}
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={upload.isPending}
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
              {upload.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Camera size={14} />
              )}
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
