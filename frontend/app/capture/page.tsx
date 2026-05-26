"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Camera, ImagePlus, X } from "lucide-react";
import { Screen } from "@/components/layout/Screen";
import { useCapture } from "@/lib/store/capture";
import { readManyFiles } from "@/lib/files";

/**
 * Capture entry. Two file inputs:
 *  • `capture="environment"` — opens the rear camera on mobile
 *  • plain file input         — opens the gallery picker
 *
 * Both feed into the same in-memory `useCapture` store and forward to
 * `/capture/preview`. Real in-app camera via MediaDevices.getUserMedia
 * lands in a later phase per the build spec.
 */
export default function CapturePage() {
  const router = useRouter();
  const setPending = useCapture((s) => s.setPending);
  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const [reading, setReading] = useState(false);

  useEffect(() => {
    // Fresh capture session — drop anything stale from a prior visit.
    useCapture.getState().clear();
  }, []);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setReading(true);
    try {
      const photos = await readManyFiles(files);
      const limited = photos.slice(0, 10);
      setPending(limited);
      router.push("/capture/preview");
    } finally {
      setReading(false);
    }
  }

  return (
    <Screen bg="#0A0A08">
      {/* Top close */}
      <div
        className="absolute left-4 right-4 flex items-center justify-between"
        style={{ top: "calc(env(safe-area-inset-top, 0px) + 24px)", color: "var(--color-cream)" }}
      >
        <Link
          href="/"
          aria-label="Close"
          className="flex items-center justify-center rounded-full"
          style={{ width: 40, height: 40, background: "rgba(0,0,0,0.5)" }}
        >
          <X size={22} />
        </Link>
        <div
          className="flex items-center gap-2"
          style={{
            background: "rgba(0,0,0,0.5)",
            padding: "6px 14px",
            borderRadius: 999,
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            color: "var(--color-cream)",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: 999,
              background: "var(--color-rating)",
            }}
          />
          PICK A MEAL · GPS ON
        </div>
        <div style={{ width: 40, height: 40 }} />
      </div>

      {/* Big copy block */}
      <div className="absolute left-0 right-0 px-7" style={{ top: 110, color: "var(--color-cream)" }}>
        <h1 className="leading-tight font-normal mb-3" style={{ fontSize: 30 }}>
          What did you{" "}
          <em style={{ color: "#F4E37A", fontStyle: "italic" }}>just eat?</em>
        </h1>
        <p style={{ fontSize: 14, lineHeight: 1.55, opacity: 0.78 }}>
          Snap it now — we&apos;ll remember the place and time. Add the rating
          later when you&apos;re done eating.
        </p>
      </div>

      {/* Decorative viewfinder grid */}
      <div
        className="absolute pointer-events-none"
        style={{
          left: 16,
          right: 16,
          top: 260,
          bottom: 240,
          borderRadius: 24,
          border: "1px solid rgba(244,240,222,0.18)",
          overflow: "hidden",
        }}
      >
        <div
          className="absolute"
          style={{
            top: "33%",
            left: 0,
            right: 0,
            height: 1,
            background: "rgba(255,255,255,0.10)",
          }}
        />
        <div
          className="absolute"
          style={{
            top: "66%",
            left: 0,
            right: 0,
            height: 1,
            background: "rgba(255,255,255,0.10)",
          }}
        />
        <div
          className="absolute"
          style={{
            left: "33%",
            top: 0,
            bottom: 0,
            width: 1,
            background: "rgba(255,255,255,0.10)",
          }}
        />
        <div
          className="absolute"
          style={{
            left: "66%",
            top: 0,
            bottom: 0,
            width: 1,
            background: "rgba(255,255,255,0.10)",
          }}
        />
        <div
          className="absolute left-1/2 top-1/2 flex flex-col items-center"
          style={{ transform: "translate(-50%, -50%)", color: "rgba(244,240,222,0.55)" }}
        >
          <Camera size={36} strokeWidth={1.4} />
          <div
            className="mt-2"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.08em",
            }}
          >
            VIEWFINDER · MVP STUB
          </div>
        </div>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={cameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        onChange={(e) => handleFiles(e.target.files)}
        style={{ display: "none" }}
      />
      <input
        ref={galleryInput}
        type="file"
        accept="image/*"
        multiple
        onChange={(e) => handleFiles(e.target.files)}
        style={{ display: "none" }}
      />

      {/* Bottom CTAs */}
      <div
        className="absolute left-0 right-0 flex flex-col gap-2.5 px-7"
        style={{ bottom: "calc(env(safe-area-inset-bottom, 0px) + 36px)" }}
      >
        <button
          className="btn btn-block"
          style={{ background: "var(--color-cream)", color: "var(--color-olive-700)" }}
          onClick={() => cameraInput.current?.click()}
          disabled={reading}
        >
          <Camera size={18} />
          {reading ? "Reading photo…" : "Take a photo"}
        </button>
        <button
          className="btn btn-block btn-ghost"
          style={{ color: "rgba(244,240,222,0.85)", height: 46, fontSize: 14 }}
          onClick={() => galleryInput.current?.click()}
          disabled={reading}
        >
          <ImagePlus size={18} />
          Choose from gallery
        </button>
      </div>
    </Screen>
  );
}
