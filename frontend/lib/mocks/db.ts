/**
 * Tiny localStorage-backed mock DB. Lets the MSW handlers persist
 * users / drafts / entries across page reloads while the real backend
 * is being built.
 *
 * NOTE: only reachable in the browser. The MSW worker runs in the
 * service-worker scope which DOES have its own localStorage; but to
 * avoid the SW vs window distinction we proxy through fetch handlers
 * that run on the page, so this module is fine to import directly.
 */

import type {
  AuthUser,
  DraftStatus,
  FoodTone,
  RestaurantSummary,
} from "@/lib/types";

const KEY = "snapplate.mock-db.v2";

export type MockMagicLink = {
  email: string;
  token: string;
  created_at: string;
};

export type MockUser = AuthUser & {
  taste_type: string | null;
  created_at: string;
};

export type MockRestaurant = Omit<RestaurantSummary, "distance_m" | "is_bookmarked"> & {
  address: string;
  price_range: string;
  hours: string;
  phone: string;
};

export type MockMedia = {
  id: string;
  user_id: string;
  url: string | null;
  thumbnail_url: string | null;
  width: number;
  height: number;
  bytes: number;
  tone: FoodTone;
  label: string;
  captured_at: string | null;
  lat: number | null;
  lng: number | null;
  created_at: string;
};

export type MockDraft = {
  id: string;
  user_id: string;
  status: DraftStatus;
  media_ids: string[];
  cover_media_id: string;
  captured_at: string;
  lat: number | null;
  lng: number | null;
  restaurant_id: string | null;
  restaurant_suggested: boolean;
  remind_at: string | null;
  created_at: string;
};

export type MockEntry = {
  id: string;
  user_id: string;
  draft_id: string;
  captured_at: string;
  meal_period: string | null;
  media_ids: string[];
  cover_media_id: string;
  rating: number | null;
  note: string;
  ai_tags: string[];
  restaurant_id: string;
  created_at: string;
};

export type MockSettings = {
  notifications: {
    meal_reminders: boolean;
    taste_analysis_complete: boolean;
    weekly_picks: boolean;
  };
  appearance: "light" | "dark" | "system";
};

export type MockBookmark = {
  id: string;
  user_id: string;
  restaurant_id: string;
  bookmarked_at: string;
};

export type MockDB = {
  users: Record<string, MockUser>;
  emailIndex: Record<string, string>;
  magicLinks: Record<string, MockMagicLink>;
  consumedTokens: string[];
  restaurants: Record<string, MockRestaurant>;
  media: Record<string, MockMedia>;
  drafts: Record<string, MockDraft>;
  entries: Record<string, MockEntry>;
  bookmarks: Record<string, MockBookmark>;
  settings: Record<string, MockSettings>;
};

const FOOD_TONES: FoodTone[] = [
  "rust", "ochre", "moss", "cream", "char", "paprika",
  "butter", "berry", "forest", "terra", "hay", "bone",
];

/* ───────────────────────────────────────────────────────────
   Seed restaurants — placeholder names lifted from the design
   prototype. All within walking distance of KAIST in Daejeon.
   ─────────────────────────────────────────────────────────── */
function seedRestaurants(): Record<string, MockRestaurant> {
  const seeds: MockRestaurant[] = [
    {
      id: "r_bonga",
      name: "Bonga BBQ",
      category: "Korean BBQ",
      signature_dish: "Marinated short rib",
      rating: 4.7,
      rating_count: 312,
      thumbnail_url: null,
      thumbnail_tone: "rust",
      thumbnail_label: "soy short rib",
      tags: ["reserve ahead"],
      lat: 36.371,
      lng: 127.361,
      kakao_id: "26338954",
      neighborhood: "Eoeun-dong",
      address: "12 Eoeun-ro, Yuseong-gu, Daejeon",
      price_range: "₩₩",
      hours: "11:30 AM – 10:00 PM",
      phone: "+82-42-555-0101",
    },
    {
      id: "r_sungsim",
      name: "Sungsim Bakery — Main",
      category: "Bakery",
      signature_dish: "Fried streusel bun",
      rating: 4.8,
      rating_count: 2341,
      thumbnail_url: null,
      thumbnail_tone: "cream",
      thumbnail_label: "streusel bun",
      tags: ["local favorite"],
      lat: 36.3275,
      lng: 127.4275,
      kakao_id: "26338955",
      neighborhood: "Daejong-ro",
      address: "15 Daejong-ro 480beon-gil, Jung-gu, Daejeon",
      price_range: "₩₩",
      hours: "8:00 AM – 10:00 PM",
      phone: "+82-42-256-4114",
    },
    {
      id: "r_dotori",
      name: "Cafe Dotori",
      category: "Cafe",
      signature_dish: "Acorn latte",
      rating: 4.5,
      rating_count: 188,
      thumbnail_url: null,
      thumbnail_tone: "char",
      thumbnail_label: "acorn latte",
      tags: [],
      lat: 36.367,
      lng: 127.357,
      kakao_id: "26338956",
      neighborhood: "Gungdong",
      address: "44 Gung-dong, Yuseong-gu, Daejeon",
      price_range: "₩",
      hours: "9:00 AM – 11:00 PM",
      phone: "+82-42-555-0202",
    },
    {
      id: "r_eoeun",
      name: "Eoeun Clam Noodle",
      category: "Noodles",
      signature_dish: "Clam noodle soup",
      rating: 4.6,
      rating_count: 421,
      thumbnail_url: null,
      thumbnail_tone: "bone",
      thumbnail_label: "clam noodle",
      tags: ["lunch rush"],
      lat: 36.3705,
      lng: 127.3615,
      kakao_id: "26338957",
      neighborhood: "Eoeun-dong",
      address: "8 Eoeun-ro 12beon-gil, Yuseong-gu, Daejeon",
      price_range: "₩",
      hours: "10:30 AM – 9:00 PM",
      phone: "+82-42-555-0303",
    },
    {
      id: "r_acorn",
      name: "Acorn Cafe",
      category: "Cafe",
      signature_dish: "Golden butter croissant",
      rating: 4.6,
      rating_count: 256,
      thumbnail_url: null,
      thumbnail_tone: "butter",
      thumbnail_label: "croissant",
      tags: [],
      lat: 36.369,
      lng: 127.363,
      kakao_id: "26338958",
      neighborhood: "Gungdong",
      address: "27 Gung-dong, Yuseong-gu, Daejeon",
      price_range: "₩₩",
      hours: "8:00 AM – 9:00 PM",
      phone: "+82-42-555-0404",
    },
  ];
  const out: Record<string, MockRestaurant> = {};
  for (const r of seeds) out[r.id] = r;
  return out;
}

const initial: MockDB = {
  users: {},
  emailIndex: {},
  magicLinks: {},
  consumedTokens: [],
  restaurants: seedRestaurants(),
  media: {},
  drafts: {},
  entries: {},
  bookmarks: {},
  settings: {},
};

export const defaultSettings = (): MockSettings => ({
  notifications: {
    meal_reminders: true,
    taste_analysis_complete: true,
    weekly_picks: false,
  },
  appearance: "light",
});

let cache: MockDB | null = null;

function ensureSeeded(db: MockDB): MockDB {
  if (!db.restaurants || Object.keys(db.restaurants).length === 0) {
    db.restaurants = seedRestaurants();
  }
  db.media ??= {};
  db.drafts ??= {};
  db.entries ??= {};
  db.bookmarks ??= {};
  db.settings ??= {};
  return db;
}

function read(): MockDB {
  if (cache) return cache;
  if (typeof window === "undefined") {
    cache = structuredClone(initial);
    return cache;
  }
  try {
    const raw = window.localStorage.getItem(KEY);
    cache = ensureSeeded(
      raw ? (JSON.parse(raw) as MockDB) : structuredClone(initial),
    );
  } catch {
    cache = structuredClone(initial);
  }
  return cache;
}

function write(db: MockDB) {
  cache = db;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(KEY, JSON.stringify(db));
  }
}

export const db = {
  get: read,
  update(mutator: (db: MockDB) => void) {
    const next = read();
    mutator(next);
    write(next);
    return next;
  },
  reset() {
    write(structuredClone(initial));
  },
};

/* ───────────────────────────────────────────────────────────
   ID helpers
   ─────────────────────────────────────────────────────────── */
const rand = () => Math.random().toString(36).slice(2, 12);
export const makeUserId = () => `u_${rand()}`;
export const makeToken = () => `tok_${rand()}${Date.now().toString(36)}`;
export const makeMediaId = () => `m_${rand()}`;
export const makeDraftId = () => `d_${rand()}`;
export const makeEntryId = () => `e_${rand()}`;
export const makeBookmarkId = () => `b_${rand()}`;
export const makeJwt = (userId: string) =>
  `mock.${userId}.${Math.random().toString(36).slice(2)}`;

/* ───────────────────────────────────────────────────────────
   Geo + display helpers
   ─────────────────────────────────────────────────────────── */
export function pickToneFor(seed: string): FoodTone {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = ((h << 5) - h + seed.charCodeAt(i)) | 0;
  }
  return FOOD_TONES[Math.abs(h) % FOOD_TONES.length]!;
}

function haversineMeters(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  const R = 6371_000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

export function nearestRestaurant(
  lat: number | null | undefined,
  lng: number | null | undefined,
): MockRestaurant | null {
  if (lat == null || lng == null) return null;
  const all = Object.values(db.get().restaurants);
  let best: { r: MockRestaurant; d: number } | null = null;
  for (const r of all) {
    const d = haversineMeters({ lat, lng }, { lat: r.lat, lng: r.lng });
    if (!best || d < best.d) best = { r, d };
  }
  if (!best) return null;
  return best.d < 1500 ? best.r : null;
}

export function distanceMeters(
  lat: number | null | undefined,
  lng: number | null | undefined,
  r: MockRestaurant,
): number {
  if (lat == null || lng == null) return 0;
  return Math.round(haversineMeters({ lat, lng }, { lat: r.lat, lng: r.lng }));
}

export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso);
  const diffMs = now.getTime() - then.getTime();
  const min = Math.round(diffMs / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.round(hr / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return then.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function dayLabel(iso: string, now: Date = new Date()): string {
  const then = new Date(iso);
  const sameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
  if (sameDay(then, now)) return "Today";
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay(then, yesterday)) return "Yesterday";
  return then.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

export function mealPeriodFor(iso: string): string {
  const h = new Date(iso).getHours();
  if (h < 10) return "breakfast";
  if (h < 14) return "lunch";
  if (h < 17) return "snack";
  if (h < 21) return "dinner";
  return "late night";
}
