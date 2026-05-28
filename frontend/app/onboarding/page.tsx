"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Camera } from "lucide-react";
import { Screen } from "@/components/layout/Screen";

/**
 * 3-slide onboarding carousel.
 *
 * Same artwork as the prototype (food cards, restaurant list, flavor
 * hexagon) but driven by local state — Skip jumps straight to /permission,
 * "Let's eat" on the last slide does the same.
 */

function OnboardArt1() {
  const cards = [
    { tone: "terra", label: "bibimbap", dish: "bibimbap", when: "apr 22 · 12:43", rot: -8, x: 6, y: 18 },
    { tone: "moss", label: "namul", dish: "seasoned greens", when: "apr 21 · 19:02", rot: 4, x: 78, y: 64 },
    { tone: "ochre", label: "kimchi-jjigae", dish: "kimchi stew", when: "apr 21 · 12:30", rot: -3, x: 32, y: 130 },
  ];
  return (
    <div style={{ position: "relative", width: 280, height: 320 }}>
      {cards.map((c, i) => (
        <div
          key={i}
          className="card"
          style={{
            position: "absolute",
            left: c.x,
            top: c.y,
            width: 168,
            padding: 10,
            paddingBottom: 14,
            transform: `rotate(${c.rot}deg)`,
            boxShadow:
              "0 18px 40px -8px rgba(31,31,25,0.18), 0 2px 6px rgba(31,31,25,0.06)",
            borderRadius: 10,
            zIndex: i,
          }}
        >
          <div
            className="food"
            data-tone={c.tone}
            data-label={c.label}
            style={{ width: "100%", height: 148, borderRadius: 4 }}
          />
          <div className="flex justify-between items-baseline mt-2 px-0.5">
            <span style={{ fontFamily: "var(--font-serif)", fontSize: 14, fontWeight: 500 }}>
              {c.dish}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                color: "var(--color-muted)",
              }}
            >
              {c.when}
            </span>
          </div>
        </div>
      ))}
      <div
        className="flex items-center justify-center"
        style={{
          position: "absolute",
          top: 4,
          right: 6,
          width: 44,
          height: 44,
          borderRadius: "50%",
          background: "var(--color-olive-700)",
          color: "var(--color-cream)",
          boxShadow: "0 6px 16px rgba(15,118,110,0.30)",
          zIndex: 10,
          transform: "rotate(8deg)",
        }}
      >
        <Camera size={22} />
      </div>
    </div>
  );
}

function OnboardArt2() {
  const rows = [
    { tone: "rust", n: "Bonga BBQ", l: "soy-marinated short rib" },
    { tone: "cream", n: "Sungsim Bakery", l: "fried streusel bun" },
    { tone: "forest", n: "Eoeun Noodle", l: "clam noodle soup" },
  ];
  return (
    <div
      style={{
        position: "relative",
        width: 280,
        height: 320,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        justifyContent: "center",
      }}
    >
      {rows.map((r, i) => (
        <div
          key={i}
          className="card flex gap-3 p-3 items-center"
          style={{ transform: `rotate(${(i - 1) * 2}deg)` }}
        >
          <div
            className="food shrink-0"
            data-tone={r.tone}
            data-label={r.l}
            style={{ width: 60, height: 60, borderRadius: 14 }}
          />
          <div className="flex-1 min-w-0">
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 16, fontWeight: 500 }}>
              {r.n}
            </div>
            <div style={{ fontSize: 11, color: "var(--color-muted)" }}>{r.l}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function OnboardArt3() {
  const points: Array<[string, number, number, string]> = [
    ["Salty", 140, 30, "#3F4A2C"],
    ["Sweet", 245, 90, "#5D6B43"],
    ["Umami", 245, 210, "#8B6B47"],
    ["Spicy", 140, 270, "#A8553A"],
    ["Sour", 35, 210, "#C49B3A"],
    ["Bitter", 35, 90, "#6E7C53"],
  ];
  return (
    <div style={{ position: "relative", width: 280, height: 320 }}>
      <svg
        width="280"
        height="280"
        viewBox="0 0 280 280"
        style={{ position: "absolute", top: 20 }}
      >
        <defs>
          <radialGradient id="og1">
            <stop offset="0%" stopColor="#A8B393" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#A8B393" stopOpacity="0" />
          </radialGradient>
        </defs>
        <polygon
          points="140,30 245,90 245,210 140,270 35,210 35,90"
          fill="url(#og1)"
          stroke="#5D6B43"
          strokeWidth="1"
          opacity="0.4"
        />
        <polygon
          points="140,80 195,110 195,180 140,210 85,180 85,110"
          fill="none"
          stroke="#5D6B43"
          strokeWidth="1"
          opacity="0.3"
        />
        <polygon
          points="140,55 220,100 220,200 140,245 60,200 60,100"
          fill="none"
          stroke="#5D6B43"
          strokeWidth="1"
          opacity="0.2"
        />
        {points.map(([l, x, y, c], i) => (
          <g key={i}>
            <circle cx={x} cy={y} r="4" fill={c} />
            <text
              x={x}
              y={y - 12}
              fontFamily="Newsreader"
              fontSize="13"
              fill="#3F4A2C"
              textAnchor="middle"
            >
              {l}
            </text>
          </g>
        ))}
        <polygon
          points="140,80 230,130 215,195 110,190 70,150"
          fill="#5D6B43"
          fillOpacity="0.25"
          stroke="#3F4A2C"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  );
}

const SLIDES = [
  {
    title: (
      <>
        What did you eat{" "}
        <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>today?</em>
      </>
    ),
    body: "Snap your meals. Capture the moment, the place, the feeling — all in one photo.",
    art: <OnboardArt1 />,
  },
  {
    title: (
      <>
        A diary that{" "}
        <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>remembers.</em>
      </>
    ),
    body: "Every entry stores the time, place, and your honest take. Search and revisit any meal.",
    art: <OnboardArt2 />,
  },
  {
    title: (
      <>
        Find your <em style={{ color: "var(--color-olive-700)", fontStyle: "italic" }}>taste.</em>
      </>
    ),
    body: "The more you log, the better we understand what you love. Personal recommendations — never crowdsourced averages.",
    art: <OnboardArt3 />,
  },
];

type Slide = (typeof SLIDES)[number];


export default function OnboardingPage() {
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const displayIdxRef = useRef(0);
  const [displayIdx, setDisplayIdx] = useState(0);

  useEffect(() => {
    displayIdxRef.current = displayIdx;
  }, [displayIdx]);

  useEffect(() => {
    return () => {
    };
  }, []);

  const handleSkip = () => router.replace("/permission");

  const scrollToSlide = (nextIndex: number) => {
    const container = scrollRef.current;
    if (!container) return;
    container.scrollTo({
      left: nextIndex * container.clientWidth,
      behavior: "smooth",
    });
  };

  const handleNext = () => {
    if (displayIdx >= SLIDES.length - 1) {
      router.replace("/permission");
      return;
    }
    scrollToSlide(displayIdx + 1);
  };

  const startFadeTo = (nextIdx: number) => {
    if (nextIdx === displayIdxRef.current) return;
    setDisplayIdx(nextIdx);
    displayIdxRef.current = nextIdx;
  };

  const handleScroll = () => {
    const container = scrollRef.current;
    if (!container) return;
    const rawIndex = Math.round(container.scrollLeft / container.clientWidth);
    const nextIndex = Math.max(0, Math.min(SLIDES.length - 1, rawIndex));
    startFadeTo(nextIndex);
  };

  const slide = SLIDES[displayIdx] ?? SLIDES[0]!;
  const renderMessage = (messageSlide: Slide) => (
    <>
      <h1 className="leading-tight mb-2 font-normal" style={{ fontSize: 30 }}>
        {messageSlide.title}
      </h1>
      <p className="leading-relaxed" style={{ fontSize: 15, color: "var(--color-muted)" }}>
        {messageSlide.body}
      </p>
    </>
  );

  return (
    <Screen bg="var(--color-surface)">
      <div
        className="absolute left-0 right-0"
        style={{
          top: 56,
          bottom: 0,
          display: "flex",
          flexDirection: "column",
          padding: "0 28px 36px",
        }}
      >
        <div className="relative flex-1">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="onboard-scroll flex h-full overflow-x-auto overflow-y-hidden snap-x snap-mandatory"
            style={{ scrollBehavior: "smooth", WebkitOverflowScrolling: "touch" }}
          >
            {SLIDES.map((item, index) => (
              <div
                key={index}
                className="onboard-slide snap-start shrink-0 w-full h-full flex items-center justify-center"
              >
                {item.art}
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-1.5 justify-center mb-4">
          {SLIDES.map((_, i) => (
            <span
              key={i}
              style={{
                width: i === displayIdx ? 22 : 6,
                height: 6,
                borderRadius: 3,
                background:
                  i === displayIdx
                    ? "var(--color-olive-700)"
                    : "var(--color-border-strong)",
                transition: "width 0.25s ease",
              }}
            />
          ))}
        </div>

        <div className="mb-5">
          {renderMessage(slide)}
        </div>

        <div className="flex gap-3">
          <button onClick={handleSkip} className="btn btn-secondary flex-1">
            Skip
          </button>
          <button onClick={handleNext} className="btn" style={{ flex: 2 }}>
            {displayIdx === SLIDES.length - 1 ? "Let's eat" : "Next"}
          </button>
        </div>
      </div>

      <div
        className="absolute"
        style={{
          top: 56,
          right: 28,
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          color: "var(--color-muted-2)",
          letterSpacing: "0.08em",
        }}
      >
        0{displayIdx + 1} / 03
      </div>
    </Screen>
  );
}
