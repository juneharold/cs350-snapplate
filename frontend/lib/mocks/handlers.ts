/**
 * MSW handlers for SnapPlate's MVP API contract.
 *
 * Scope so far: auth, /me, media uploads, drafts CRUD + finalize,
 * entries list/detail, single-restaurant lookup, and a stub for
 * /restaurants/nearby that returns the seed list. Taste, search,
 * bookmarks, and full restaurant explore land in later phases.
 */

import { http, HttpResponse, delay } from "msw";
import {
  dayLabel,
  db,
  defaultSettings,
  distanceMeters,
  makeBookmarkId,
  makeDraftId,
  makeEntryId,
  makeJwt,
  makeMediaId,
  makeToken,
  makeUserId,
  mealPeriodFor,
  nearestRestaurant,
  pickToneFor,
  relativeTime,
  type MockDraft,
  type MockEntry,
  type MockMedia,
  type MockRestaurant,
  type MockUser,
} from "@/lib/mocks/db";
import type {
  ApiError,
  DraftDetail,
  DraftListResponse,
  DraftSummary,
  EntryDetail,
  EntryListResponse,
  EntrySummary,
  FoodTone,
  MediaRecord,
  RestaurantSummary,
} from "@/lib/types";

const BASE = "/v1";

function err(status: number, code: string, message: string, field?: string): Response {
  const body: ApiError = { error: { code, message, field, trace_id: makeToken() } };
  return HttpResponse.json(body, { status });
}

function userFromAuthHeader(req: Request): MockUser | null {
  const auth = req.headers.get("Authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  const token = auth.slice(7);
  const parts = token.split(".");
  if (parts.length !== 3 || parts[0] !== "mock") return null;
  const userId = parts[1];
  if (!userId) return null;
  return db.get().users[userId] ?? null;
}

/* ───────────────────────────────────────────────────────────
   Projections — db row → API shape
   ─────────────────────────────────────────────────────────── */
function isBookmarked(userId: string | null, restaurantId: string): boolean {
  if (!userId) return false;
  return Object.values(db.get().bookmarks).some(
    (b) => b.user_id === userId && b.restaurant_id === restaurantId,
  );
}

function restaurantSummary(
  r: MockRestaurant,
  lat?: number | null,
  lng?: number | null,
  userId: string | null = null,
): RestaurantSummary {
  const distance_m = distanceMeters(lat ?? null, lng ?? null, r);
  return {
    id: r.id,
    name: r.name,
    category: r.category,
    signature_dish: r.signature_dish,
    rating: r.rating,
    rating_count: r.rating_count,
    distance_m,
    thumbnail_url: r.thumbnail_url,
    thumbnail_tone: r.thumbnail_tone,
    thumbnail_label: r.thumbnail_label,
    tags: r.tags,
    lat: r.lat,
    lng: r.lng,
    kakao_id: r.kakao_id,
    neighborhood: r.neighborhood,
    is_bookmarked: isBookmarked(userId, r.id),
  };
}

function mediaToRecord(m: MockMedia): MediaRecord {
  return {
    id: m.id,
    url: m.url,
    thumbnail_url: m.thumbnail_url,
    width: m.width,
    height: m.height,
    bytes: m.bytes,
    tone: m.tone,
    label: m.label,
    exif: {
      captured_at: m.captured_at,
      lat: m.lat,
      lng: m.lng,
      has_location: m.lat != null && m.lng != null,
      has_timestamp: m.captured_at != null,
    },
  };
}

function draftSummary(d: MockDraft): DraftSummary {
  const cover = db.get().media[d.cover_media_id];
  const restaurant = d.restaurant_id ? db.get().restaurants[d.restaurant_id] : null;
  return {
    id: d.id,
    status: d.status,
    captured_at: d.captured_at,
    captured_relative: relativeTime(d.captured_at),
    cover_media_url: cover?.url ?? null,
    cover_media_tone: cover?.tone ?? "ochre",
    cover_media_label: cover?.label ?? "meal",
    media_count: d.media_ids.length,
    restaurant: restaurant
      ? { id: restaurant.id, name: restaurant.name, neighborhood: restaurant.neighborhood }
      : null,
    restaurant_suggested: d.restaurant_suggested,
    remind_at: d.remind_at,
  };
}

function draftDetail(d: MockDraft, userId: string | null = null): DraftDetail {
  const restaurant = d.restaurant_id ? db.get().restaurants[d.restaurant_id] ?? null : null;
  return {
    id: d.id,
    status: d.status,
    media: d.media_ids.map((mid) => {
      const m = db.get().media[mid];
      return {
        id: mid,
        url: m?.url ?? null,
        thumbnail_url: m?.thumbnail_url ?? null,
        is_cover: mid === d.cover_media_id,
        tone: m?.tone ?? "ochre",
        label: m?.label ?? "meal",
      };
    }),
    captured_at: d.captured_at,
    lat: d.lat,
    lng: d.lng,
    restaurant: restaurant ? restaurantSummary(restaurant, d.lat, d.lng, userId) : null,
    restaurant_suggested: d.restaurant_suggested,
    created_at: d.created_at,
    remind_at: d.remind_at,
  };
}

function entrySummary(e: MockEntry): EntrySummary {
  const cover = db.get().media[e.cover_media_id];
  const restaurant = db.get().restaurants[e.restaurant_id]!;
  return {
    id: e.id,
    captured_at: e.captured_at,
    day_label: dayLabel(e.captured_at),
    cover_media_url: cover?.url ?? null,
    cover_media_tone: cover?.tone ?? "ochre",
    cover_media_label: cover?.label ?? "meal",
    media_count: e.media_ids.length,
    restaurant: {
      id: restaurant.id,
      name: restaurant.name,
      signature_dish: restaurant.signature_dish,
      neighborhood: restaurant.neighborhood,
    },
    rating: e.rating,
    note_excerpt: e.note.length > 100 ? `${e.note.slice(0, 100).trimEnd()}…` : e.note,
  };
}

function entryDetail(e: MockEntry, userId: string | null = null): EntryDetail {
  const restaurant = db.get().restaurants[e.restaurant_id]!;
  return {
    id: e.id,
    captured_at: e.captured_at,
    meal_period: e.meal_period,
    media: e.media_ids.map((mid) => {
      const m = db.get().media[mid];
      return {
        id: mid,
        url: m?.url ?? null,
        is_cover: mid === e.cover_media_id,
        tone: m?.tone ?? "ochre",
        label: m?.label ?? "meal",
      };
    }),
    rating: e.rating,
    note: e.note,
    ai_tags: e.ai_tags,
    restaurant: restaurantSummary(restaurant, restaurant.lat, restaurant.lng, userId),
    created_at: e.created_at,
  };
}

function statsFor(userId: string) {
  const entries = Object.values(db.get().entries).filter((e) => e.user_id === userId);
  const placeIds = new Set(entries.map((e) => e.restaurant_id));
  const ratings = entries.map((e) => e.rating).filter((r): r is number => r != null);
  const now = new Date();
  const thisMonth = entries.filter((e) => {
    const t = new Date(e.captured_at);
    return t.getFullYear() === now.getFullYear() && t.getMonth() === now.getMonth();
  }).length;
  return {
    entries_total: entries.length,
    places_total: placeIds.size,
    this_month: thisMonth,
    avg_rating: ratings.length
      ? Math.round((ratings.reduce((a, b) => a + b, 0) / ratings.length) * 10) / 10
      : 0,
  };
}

function bookmarksCount(userId: string): number {
  return Object.values(db.get().bookmarks).filter((b) => b.user_id === userId).length;
}

export const handlers = [
  /* ───────────────────────────────────────────────────────────
     POST /v1/auth/magic-link
     ─────────────────────────────────────────────────────────── */
  http.post(`${BASE}/auth/magic-link`, async ({ request }) => {
    await delay(350);
    const body = (await request.json().catch(() => null)) as { email?: string } | null;
    const email = body?.email?.trim().toLowerCase();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return err(400, "INVALID_EMAIL", "That doesn't look like a valid email.");
    }
    const token = makeToken();
    db.update((d) => {
      d.magicLinks[token] = {
        email,
        token,
        created_at: new Date().toISOString(),
      };
    });
    return HttpResponse.json({
      sent: true,
      resend_available_at: new Date(Date.now() + 60_000).toISOString(),
      _mock_link_token: token,
    });
  }),

  /* ───────────────────────────────────────────────────────────
     POST /v1/auth/verify
     ─────────────────────────────────────────────────────────── */
  http.post(`${BASE}/auth/verify`, async ({ request }) => {
    await delay(300);
    const body = (await request.json().catch(() => null)) as { token?: string } | null;
    const token = body?.token;
    if (!token) return err(401, "INVALID_TOKEN", "Missing token.");
    const state = db.get();
    if (state.consumedTokens.includes(token)) {
      return err(401, "EXPIRED_TOKEN", "This link has already been used.");
    }
    const link = state.magicLinks[token];
    if (!link) return err(401, "INVALID_TOKEN", "This sign-in link is invalid.");

    let userId = state.emailIndex[link.email];
    let isNew = false;
    if (!userId) {
      userId = makeUserId();
      isNew = true;
      db.update((d) => {
        const u: MockUser = {
          id: userId!,
          email: link.email,
          nickname: null,
          profile_image_url: null,
          is_new: true,
          taste_type: null,
          created_at: new Date().toISOString(),
        };
        d.users[userId!] = u;
        d.emailIndex[link.email] = userId!;
      });
    }
    db.update((d) => {
      delete d.magicLinks[token];
      d.consumedTokens.push(token);
    });
    const user = db.get().users[userId]!;
    return HttpResponse.json({
      access_token: makeJwt(userId),
      expires_in: 60 * 60 * 24 * 30,
      user: {
        id: user.id,
        email: user.email,
        nickname: user.nickname,
        profile_image_url: user.profile_image_url,
        is_new: isNew,
      },
    });
  }),

  /* ─── POST /v1/auth/logout ─── */
  http.post(`${BASE}/auth/logout`, async () => {
    await delay(120);
    return new HttpResponse(null, { status: 204 });
  }),

  /* ─── GET /v1/me ─── */
  http.get(`${BASE}/me`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const stats = statsFor(user.id);
    return HttpResponse.json({
      id: user.id,
      email: user.email,
      nickname: user.nickname,
      profile_image_url: user.profile_image_url,
      taste_type: user.taste_type,
      stats: {
        entries_count: stats.entries_total,
        places_count: stats.places_total,
        bookmarks_count: bookmarksCount(user.id),
        avg_rating: stats.avg_rating,
      },
      created_at: user.created_at,
    });
  }),

  /* ─── PATCH /v1/me ─── */
  http.patch(`${BASE}/me`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const body = (await request.json().catch(() => null)) as { nickname?: string } | null;
    if (body && "nickname" in body) {
      const nickname = (body.nickname ?? "").trim();
      if (!nickname) return err(400, "NICKNAME_EMPTY", "Pick something we can call you.", "nickname");
      if (nickname.length > 20) return err(400, "NICKNAME_TOO_LONG", "Up to 20 characters.", "nickname");
      db.update((d) => {
        const u = d.users[user.id]!;
        u.nickname = nickname;
        u.is_new = false;
      });
    }
    const u = db.get().users[user.id]!;
    const stats = statsFor(u.id);
    return HttpResponse.json({
      id: u.id,
      email: u.email,
      nickname: u.nickname,
      profile_image_url: u.profile_image_url,
      taste_type: u.taste_type,
      stats: {
        entries_count: stats.entries_total,
        places_count: stats.places_total,
        bookmarks_count: bookmarksCount(u.id),
        avg_rating: stats.avg_rating,
      },
      created_at: u.created_at,
    });
  }),

  /* ───────────────────────────────────────────────────────────
     GET /v1/restaurants/nearby
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/restaurants/nearby`, ({ request }) => {
    const user = userFromAuthHeader(request);
    const url = new URL(request.url);
    const lat = parseFloat(url.searchParams.get("lat") ?? "");
    const lng = parseFloat(url.searchParams.get("lng") ?? "");
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);
    const category = url.searchParams.get("category");
    const minRating = parseFloat(url.searchParams.get("min_rating") ?? "");
    const sort = url.searchParams.get("sort") ?? "distance";
    let all = Object.values(db.get().restaurants);
    if (category) all = all.filter((r) => r.category === category);
    if (isFinite(minRating)) all = all.filter((r) => r.rating >= minRating);
    const items = all.map((r) =>
      restaurantSummary(r, isFinite(lat) ? lat : null, isFinite(lng) ? lng : null, user?.id ?? null),
    );
    if (sort === "rating") items.sort((a, b) => b.rating - a.rating);
    else items.sort((a, b) => a.distance_m - b.distance_m);
    return HttpResponse.json({
      items: items.slice(0, limit),
      next_cursor: null,
      has_more: false,
    });
  }),

  /* ───────────────────────────────────────────────────────────
     GET /v1/restaurants/search?q=
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/restaurants/search`, ({ request }) => {
    const user = userFromAuthHeader(request);
    const url = new URL(request.url);
    const q = (url.searchParams.get("q") ?? "").trim().toLowerCase();
    const lat = parseFloat(url.searchParams.get("lat") ?? "");
    const lng = parseFloat(url.searchParams.get("lng") ?? "");
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);
    const category = url.searchParams.get("category");
    const minRating = parseFloat(url.searchParams.get("min_rating") ?? "");
    let all = Object.values(db.get().restaurants);
    if (category) all = all.filter((r) => r.category === category);
    if (isFinite(minRating)) all = all.filter((r) => r.rating >= minRating);
    const scored = all
      .map((r) => {
        const hay = `${r.name} ${r.signature_dish ?? ""} ${r.category} ${r.neighborhood}`.toLowerCase();
        let score = 0;
        if (!q) score = 0.5;
        else if (hay.includes(q)) score = q.length / Math.max(hay.length, 1) + 0.5;
        else {
          // Fuzzy fallback — count letter overlap.
          const qLetters = new Set(q.split(""));
          const overlap = [...qLetters].filter((c) => hay.includes(c)).length;
          score = overlap / Math.max(qLetters.size, 1) * 0.3;
        }
        return { r, score };
      })
      .filter((x) => x.score > 0.05)
      .sort((a, b) => b.score - a.score);
    const items = scored.slice(0, limit).map(({ r, score }) => ({
      ...restaurantSummary(r, isFinite(lat) ? lat : null, isFinite(lng) ? lng : null, user?.id ?? null),
      match_score: Math.round(score * 100) / 100,
    }));
    return HttpResponse.json({
      items,
      next_cursor: null,
      has_more: false,
    });
  }),

  /* ───────────────────────────────────────────────────────────
     GET /v1/restaurants/recommended
     ──────────────────────────────────────────────────────────
     Reads the user's logged entries, weights each category by
     avg-rating × log(visits + 1), then suggests restaurants in
     the top-weighted categories that they haven't been to yet.
     Reason string references their highest-rated past meal so it
     feels personal, not generic.
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/restaurants/recommended`, ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const url = new URL(request.url);
    const lat = parseFloat(url.searchParams.get("lat") ?? "");
    const lng = parseFloat(url.searchParams.get("lng") ?? "");
    const limit = parseInt(url.searchParams.get("limit") ?? "10", 10);
    const MIN_ENTRIES = 3;

    const entries = Object.values(db.get().entries).filter((e) => e.user_id === user.id);
    if (entries.length < MIN_ENTRIES) {
      return HttpResponse.json({
        items: [],
        based_on_entries: entries.length,
        has_enough_data: false,
      });
    }

    // Aggregate per-category preference signal.
    const byCat = new Map<string, { ratingSum: number; ratingN: number; visits: number }>();
    for (const e of entries) {
      const r = db.get().restaurants[e.restaurant_id];
      if (!r) continue;
      const c = byCat.get(r.category) ?? { ratingSum: 0, ratingN: 0, visits: 0 };
      c.ratingSum += e.rating ?? 4.0;
      c.ratingN += 1;
      c.visits += 1;
      byCat.set(r.category, c);
    }
    const ranked = [...byCat.entries()]
      .map(([cat, c]) => ({
        cat,
        avg: c.ratingN > 0 ? c.ratingSum / c.ratingN : 0,
        visits: c.visits,
        score: (c.ratingN > 0 ? c.ratingSum / c.ratingN : 0) * Math.log(c.visits + 1),
      }))
      .sort((a, b) => b.score - a.score);

    // Find the user's highest-rated past entry in each top category so
    // we can name it in the "reason" string.
    function topMealIn(cat: string): MockRestaurant | null {
      const candidates = entries
        .map((e) => ({ entry: e, r: db.get().restaurants[e.restaurant_id] }))
        .filter((x): x is { entry: MockEntry; r: MockRestaurant } => !!x.r && x.r.category === cat)
        .sort((a, b) => (b.entry.rating ?? 0) - (a.entry.rating ?? 0));
      return candidates[0]?.r ?? null;
    }

    const visited = new Set(entries.map((e) => e.restaurant_id));
    const seen = new Set<string>();
    const items: Array<RestaurantSummary & { reason: string }> = [];

    for (const { cat } of ranked) {
      if (items.length >= limit) break;
      const muse = topMealIn(cat);
      const candidates = Object.values(db.get().restaurants)
        .filter((r) => r.category === cat && !visited.has(r.id) && !seen.has(r.id))
        .sort((a, b) => b.rating - a.rating);
      for (const c of candidates) {
        if (items.length >= limit) break;
        seen.add(c.id);
        const reason = muse && muse.id !== c.id
          ? `You loved ${muse.name} — same ${cat.toLowerCase()} energy.`
          : `Strong on ${cat.toLowerCase()} — worth a try.`;
        items.push({
          ...restaurantSummary(c, isFinite(lat) ? lat : null, isFinite(lng) ? lng : null, user.id),
          reason,
        });
      }
    }

    // Fall-through filler: anything else they haven't visited, sorted by rating.
    if (items.length < limit) {
      const filler = Object.values(db.get().restaurants)
        .filter((r) => !visited.has(r.id) && !seen.has(r.id))
        .sort((a, b) => b.rating - a.rating);
      for (const r of filler) {
        if (items.length >= limit) break;
        seen.add(r.id);
        items.push({
          ...restaurantSummary(r, isFinite(lat) ? lat : null, isFinite(lng) ? lng : null, user.id),
          reason: `Highly rated near you.`,
        });
      }
    }

    return HttpResponse.json({
      items,
      based_on_entries: entries.length,
      has_enough_data: true,
    });
  }),

  /* ───────────────────────────────────────────────────────────
     GET /v1/restaurants/:id
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/restaurants/:id`, ({ params, request }) => {
    const user = userFromAuthHeader(request);
    const id = params.id as string;
    const r = db.get().restaurants[id];
    if (!r) return err(404, "NOT_FOUND", "Restaurant not found.");

    const userEntries = user
      ? Object.values(db.get().entries).filter(
          (e) => e.user_id === user.id && e.restaurant_id === r.id,
        )
      : [];
    userEntries.sort((a, b) => a.captured_at.localeCompare(b.captured_at));

    return HttpResponse.json({
      ...restaurantSummary(r, r.lat, r.lng, user?.id ?? null),
      price_range: r.price_range,
      address: r.address,
      hours: r.hours,
      phone: r.phone,
      kakao_place_url: `https://place.map.kakao.com/${r.kakao_id}`,
      popular_dishes: r.signature_dish
        ? [{ name: r.signature_dish, price: "—", photo_url: null, tone: r.thumbnail_tone }]
        : [],
      personalization: {
        reason: userEntries.length > 0
          ? `You've logged this place ${userEntries.length} time${userEntries.length === 1 ? "" : "s"} before.`
          : null,
        user_visited_count: userEntries.length,
        user_first_visit: userEntries[0]?.captured_at ?? null,
        user_last_visit: userEntries[userEntries.length - 1]?.captured_at ?? null,
      },
    });
  }),

  /* ───────────────────────────────────────────────────────────
     Bookmarks — GET /v1/bookmarks, POST /v1/bookmarks,
                 DELETE /v1/bookmarks/:restaurant_id
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/bookmarks`, ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const url = new URL(request.url);
    const q = (url.searchParams.get("q") ?? "").trim().toLowerCase();
    const items: Array<{
      id: string;
      restaurant_id: string;
      bookmarked_at: string;
      restaurant: RestaurantSummary;
    }> = [];
    const bookmarks = Object.values(db.get().bookmarks)
      .filter((b) => b.user_id === user.id)
      .sort((a, b) => b.bookmarked_at.localeCompare(a.bookmarked_at));
    for (const b of bookmarks) {
      const r = db.get().restaurants[b.restaurant_id];
      if (!r) continue;
      if (q && !r.name.toLowerCase().includes(q)) continue;
      items.push({
        id: b.id,
        restaurant_id: b.restaurant_id,
        bookmarked_at: b.bookmarked_at,
        restaurant: restaurantSummary(r, r.lat, r.lng, user.id),
      });
    }
    return HttpResponse.json({
      items,
      next_cursor: null,
      total: items.length,
    });
  }),

  http.post(`${BASE}/bookmarks`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const body = (await request.json().catch(() => null)) as { restaurant_id?: string } | null;
    const restaurantId = body?.restaurant_id;
    if (!restaurantId) return err(400, "VALIDATION_ERROR", "Missing restaurant_id.", "restaurant_id");
    if (!db.get().restaurants[restaurantId]) {
      return err(404, "RESTAURANT_NOT_FOUND", "Restaurant not found.");
    }
    const existing = Object.values(db.get().bookmarks).find(
      (b) => b.user_id === user.id && b.restaurant_id === restaurantId,
    );
    if (existing) return err(409, "ALREADY_BOOKMARKED", "You already saved that.");
    const id = makeBookmarkId();
    const bookmarked_at = new Date().toISOString();
    db.update((d) => {
      d.bookmarks[id] = {
        id,
        user_id: user.id,
        restaurant_id: restaurantId,
        bookmarked_at,
      };
    });
    return HttpResponse.json(
      { id, restaurant_id: restaurantId, bookmarked_at },
      { status: 201 },
    );
  }),

  http.delete(`${BASE}/bookmarks/:restaurant_id`, ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const restaurantId = params.restaurant_id as string;
    const existing = Object.values(db.get().bookmarks).find(
      (b) => b.user_id === user.id && b.restaurant_id === restaurantId,
    );
    if (!existing) return err(404, "NOT_FOUND", "Not bookmarked.");
    db.update((d) => {
      delete d.bookmarks[existing.id];
    });
    return new HttpResponse(null, { status: 204 });
  }),

  /* ───────────────────────────────────────────────────────────
     POST /v1/media/upload
     ──────────────────────────────────────────────────────────
     Accepts JSON (mock-friendly) — the client sends one record
     per file with metadata it already extracted. Real backend
     will accept multipart/form-data; the call shape stays the
     same on the response side.
     ─────────────────────────────────────────────────────────── */
  http.post(`${BASE}/media/upload`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    await delay(450);

    type IncomingFile = {
      name?: string;
      bytes?: number;
      width?: number;
      height?: number;
      captured_at?: string | null;
      lat?: number | null;
      lng?: number | null;
      label?: string;
    };
    const body = (await request.json().catch(() => null)) as {
      files?: IncomingFile[];
    } | null;
    const files = body?.files ?? [];
    if (files.length === 0) {
      return err(400, "VALIDATION_ERROR", "Attach at least one file.");
    }
    if (files.length > 10) {
      return err(400, "TOO_MANY_FILES", "Up to 10 photos per upload.");
    }

    const uploads: MediaRecord[] = [];
    db.update((d) => {
      for (const f of files) {
        const id = makeMediaId();
        const tone = pickToneFor(`${user.id}-${f.name ?? id}`) as FoodTone;
        const label = (f.label ?? "meal").slice(0, 24);
        const m: MockMedia = {
          id,
          user_id: user.id,
          url: null,
          thumbnail_url: null,
          width: f.width ?? 3024,
          height: f.height ?? 4032,
          bytes: f.bytes ?? 1024 * 1024,
          tone,
          label,
          captured_at: f.captured_at ?? new Date().toISOString(),
          lat: f.lat ?? null,
          lng: f.lng ?? null,
          created_at: new Date().toISOString(),
        };
        d.media[id] = m;
        uploads.push(mediaToRecord(m));
      }
    });
    return HttpResponse.json({ uploads });
  }),

  /* ───────────────────────────────────────────────────────────
     POST /v1/drafts
     ─────────────────────────────────────────────────────────── */
  http.post(`${BASE}/drafts`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    await delay(220);

    const body = (await request.json().catch(() => null)) as {
      media_ids?: string[];
      cover_media_id?: string;
      captured_at?: string | null;
      lat?: number | null;
      lng?: number | null;
      restaurant_id?: string | null;
      restaurant_suggested?: boolean;
    } | null;

    const media_ids = body?.media_ids ?? [];
    if (!media_ids.length) return err(400, "VALIDATION_ERROR", "Need at least one media item.");

    const cover = body?.cover_media_id ?? media_ids[0]!;
    let restaurantId = body?.restaurant_id ?? null;
    let suggested = body?.restaurant_suggested ?? false;
    if (!restaurantId) {
      const r = nearestRestaurant(body?.lat ?? null, body?.lng ?? null);
      if (r) {
        restaurantId = r.id;
        suggested = true;
      }
    }
    const status = restaurantId ? "waiting" : "needs_place";
    const id = makeDraftId();
    const now = new Date();
    const captured = body?.captured_at ?? now.toISOString();
    const draft: MockDraft = {
      id,
      user_id: user.id,
      status,
      media_ids,
      cover_media_id: cover,
      captured_at: captured,
      lat: body?.lat ?? null,
      lng: body?.lng ?? null,
      restaurant_id: restaurantId,
      restaurant_suggested: suggested,
      remind_at: new Date(now.getTime() + 60 * 60 * 1000).toISOString(),
      created_at: now.toISOString(),
    };
    db.update((d) => {
      d.drafts[id] = draft;
    });
    return HttpResponse.json(draftDetail(draft, user.id), { status: 201 });
  }),

  /* ─── GET /v1/drafts ─── */
  http.get(`${BASE}/drafts`, ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const items = Object.values(db.get().drafts)
      .filter((d) => d.user_id === user.id)
      .filter((d) => (status ? d.status === status : true))
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(draftSummary);
    const res: DraftListResponse = { items, next_cursor: null, total: items.length };
    return HttpResponse.json(res);
  }),

  /* ─── GET /v1/drafts/:id ─── */
  http.get(`${BASE}/drafts/:id`, ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const id = params.id as string;
    const d = db.get().drafts[id];
    if (!d || d.user_id !== user.id) return err(404, "NOT_FOUND", "Draft not found.");
    return HttpResponse.json(draftDetail(d, user.id));
  }),

  /* ─── PATCH /v1/drafts/:id ─── */
  http.patch(`${BASE}/drafts/:id`, async ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const id = params.id as string;
    const existing = db.get().drafts[id];
    if (!existing || existing.user_id !== user.id) {
      return err(404, "NOT_FOUND", "Draft not found.");
    }
    const patch = (await request.json().catch(() => null)) as {
      restaurant_id?: string;
      cover_media_id?: string;
      captured_at?: string;
    } | null;
    db.update((d) => {
      const draft = d.drafts[id]!;
      if (patch?.restaurant_id) {
        draft.restaurant_id = patch.restaurant_id;
        draft.restaurant_suggested = false;
        if (draft.status === "needs_place") draft.status = "waiting";
      }
      if (patch?.cover_media_id) draft.cover_media_id = patch.cover_media_id;
      if (patch?.captured_at) draft.captured_at = patch.captured_at;
    });
    return HttpResponse.json(draftDetail(db.get().drafts[id]!, user.id));
  }),

  /* ─── DELETE /v1/drafts/:id ─── */
  http.delete(`${BASE}/drafts/:id`, ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const id = params.id as string;
    const existing = db.get().drafts[id];
    if (!existing || existing.user_id !== user.id) {
      return err(404, "NOT_FOUND", "Draft not found.");
    }
    db.update((d) => {
      delete d.drafts[id];
    });
    return new HttpResponse(null, { status: 204 });
  }),

  /* ─── POST /v1/drafts/:id/finalize ─── */
  http.post(`${BASE}/drafts/:id/finalize`, async ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    await delay(280);
    const id = params.id as string;
    const draft = db.get().drafts[id];
    if (!draft || draft.user_id !== user.id) return err(404, "NOT_FOUND", "Draft not found.");

    const body = (await request.json().catch(() => null)) as {
      note?: string;
      rating?: number;
      restaurant_id?: string;
    } | null;

    const note = (body?.note ?? "").trim();
    if (!note) return err(400, "NOTE_REQUIRED", "A note is required to finish this entry.", "note");
    if (note.length > 500) return err(400, "NOTE_TOO_LONG", "Keep notes under 500 characters.", "note");

    const rating = body?.rating;
    if (rating != null) {
      if (rating < 0.5 || rating > 5 || ((rating * 2) % 1 !== 0)) {
        return err(400, "VALIDATION_ERROR", "Rating must be between 0.5 and 5 in 0.5 steps.", "rating");
      }
    }

    let restaurantId = draft.restaurant_id ?? body?.restaurant_id ?? null;
    if (body?.restaurant_id) restaurantId = body.restaurant_id;
    if (!restaurantId) {
      return err(400, "RESTAURANT_REQUIRED", "Pick a restaurant to finish this entry.", "restaurant_id");
    }
    if (!db.get().restaurants[restaurantId]) {
      return err(400, "RESTAURANT_NOT_FOUND", "Restaurant not found.", "restaurant_id");
    }

    const entryId = makeEntryId();
    const now = new Date().toISOString();
    const entry: MockEntry = {
      id: entryId,
      user_id: user.id,
      draft_id: draft.id,
      captured_at: draft.captured_at,
      meal_period: mealPeriodFor(draft.captured_at),
      media_ids: draft.media_ids,
      cover_media_id: draft.cover_media_id,
      rating: rating ?? null,
      note,
      ai_tags: [],
      restaurant_id: restaurantId,
      created_at: now,
    };
    db.update((d) => {
      d.entries[entryId] = entry;
      delete d.drafts[draft.id];
    });
    return HttpResponse.json({ entry_id: entryId, draft_id: draft.id }, { status: 201 });
  }),

  /* ─── GET /v1/entries ─── */
  http.get(`${BASE}/entries`, ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const items = Object.values(db.get().entries)
      .filter((e) => e.user_id === user.id)
      .sort((a, b) => b.captured_at.localeCompare(a.captured_at))
      .map(entrySummary);
    const stats = statsFor(user.id);
    const res: EntryListResponse = {
      items,
      next_cursor: null,
      has_more: false,
      total: items.length,
      stats,
    };
    return HttpResponse.json(res);
  }),

  /* ─── GET /v1/entries/:id ─── */
  http.get(`${BASE}/entries/:id`, ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const id = params.id as string;
    const e = db.get().entries[id];
    if (!e || e.user_id !== user.id) return err(404, "NOT_FOUND", "Entry not found.");
    return HttpResponse.json(entryDetail(e, user.id));
  }),

  /* ─── PATCH /v1/entries/:id ─── */
  http.patch(`${BASE}/entries/:id`, async ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const id = params.id as string;
    const existing = db.get().entries[id];
    if (!existing || existing.user_id !== user.id) return err(404, "NOT_FOUND", "Entry not found.");
    const patch = (await request.json().catch(() => null)) as {
      rating?: number;
      note?: string;
    } | null;
    db.update((d) => {
      const e = d.entries[id]!;
      if (patch?.rating != null) e.rating = patch.rating;
      if (patch?.note != null) e.note = patch.note;
    });
    return HttpResponse.json(entryDetail(db.get().entries[id]!, user.id));
  }),

  /* ─── DELETE /v1/entries/:id ─── */
  http.delete(`${BASE}/entries/:id`, ({ params, request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const id = params.id as string;
    const existing = db.get().entries[id];
    if (!existing || existing.user_id !== user.id) return err(404, "NOT_FOUND", "Entry not found.");
    db.update((d) => {
      delete d.entries[id];
    });
    return new HttpResponse(null, { status: 204 });
  }),

  /* ───────────────────────────────────────────────────────────
     GET /v1/taste/profile
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/taste/profile`, ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const entries = Object.values(db.get().entries).filter((e) => e.user_id === user.id);
    const MIN = 10;
    if (entries.length < MIN) {
      return HttpResponse.json({
        has_enough_data: false,
        min_entries_required: MIN,
        current_entries: entries.length,
      });
    }

    // Categories — count visits + ratings per restaurant category.
    const byCategory = new Map<string, { visits: number; ratingSum: number; ratingN: number; tone: string }>();
    for (const e of entries) {
      const r = db.get().restaurants[e.restaurant_id];
      if (!r) continue;
      const c = byCategory.get(r.category) ?? { visits: 0, ratingSum: 0, ratingN: 0, tone: r.thumbnail_tone };
      c.visits += 1;
      if (e.rating != null) { c.ratingSum += e.rating; c.ratingN += 1; }
      byCategory.set(r.category, c);
    }
    const maxVisits = Math.max(1, ...[...byCategory.values()].map((c) => c.visits));
    const categories = [...byCategory.entries()]
      .map(([name, c]) => ({
        name,
        weight: Math.round((c.visits / maxVisits) * 100) / 100,
        visits: c.visits,
        tone: c.tone as MockRestaurant["thumbnail_tone"],
      }))
      .sort((a, b) => b.weight - a.weight);

    // Time-of-day heatmap — 5 row buckets × 7 weekday columns.
    const rows = ["8 AM", "12 PM", "3 PM", "7 PM", "10 PM"] as const;
    const bucketFor = (h: number) => {
      if (h < 11) return 0;
      if (h < 14) return 1;
      if (h < 17) return 2;
      if (h < 21) return 3;
      return 4;
    };
    const heatmap: number[][] = Array.from({ length: 5 }, () => Array(7).fill(0));
    for (const e of entries) {
      const t = new Date(e.captured_at);
      const col = (t.getDay() + 6) % 7; // Monday = 0
      const row = bucketFor(t.getHours());
      heatmap[row]![col]! += 1;
    }
    const cols = ["M", "T", "W", "T", "F", "S", "S"];

    // Top day-of-week.
    const dayTotals = new Array(7).fill(0);
    for (const e of entries) {
      const col = (new Date(e.captured_at).getDay() + 6) % 7;
      dayTotals[col] += 1;
    }
    const topDay = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][
      dayTotals.indexOf(Math.max(...dayTotals))
    ];

    // Flavor lean — bogus but stable per-user values.
    const seedHash = [...user.id].reduce((a, c) => a + c.charCodeAt(0), 0);
    const flavor = (offset: number) =>
      Math.round(((Math.sin(seedHash + offset) + 1) / 2) * 80 + 15) / 100;

    // Top dishes — by visits × avg rating.
    const dishMap = new Map<string, { visits: number; ratingSum: number; ratingN: number; tone: string }>();
    for (const e of entries) {
      const r = db.get().restaurants[e.restaurant_id];
      if (!r?.signature_dish) continue;
      const d = dishMap.get(r.signature_dish) ?? { visits: 0, ratingSum: 0, ratingN: 0, tone: r.thumbnail_tone };
      d.visits += 1;
      if (e.rating != null) { d.ratingSum += e.rating; d.ratingN += 1; }
      dishMap.set(r.signature_dish, d);
    }
    const topDishes = [...dishMap.entries()]
      .map(([name, d]) => ({
        name,
        visits: d.visits,
        rating: d.ratingN > 0 ? Math.round((d.ratingSum / d.ratingN) * 10) / 10 : 0,
        tone: d.tone as MockRestaurant["thumbnail_tone"],
      }))
      .sort((a, b) => b.visits * b.rating - a.visits * a.rating)
      .slice(0, 3);

    // Summary stats.
    const ratings = entries.map((e) => e.rating).filter((r): r is number => r != null);
    const ratingDistribution = Object.fromEntries(
      Array.from({ length: 10 }, (_, i) => [((i + 1) / 2).toFixed(1), 0]),
    ) as Record<string, number>;
    for (const rating of ratings) {
      const key = (Math.round(rating * 2) / 2).toFixed(1);
      ratingDistribution[key] = (ratingDistribution[key] ?? 0) + 1;
    }
    const avgRating = ratings.length
      ? Math.round((ratings.reduce((a, b) => a + b, 0) / ratings.length) * 10) / 10
      : 0;
    const placeIds = new Set(entries.map((e) => e.restaurant_id));
    const now = new Date();
    const newThisMonth = new Set(
      entries
        .filter((e) => {
          const t = new Date(e.captured_at);
          return t.getFullYear() === now.getFullYear() && t.getMonth() === now.getMonth();
        })
        .map((e) => e.restaurant_id),
    ).size;

    return HttpResponse.json({
      has_enough_data: true,
      min_entries_required: MIN,
      current_entries: entries.length,
      computed_at: new Date().toISOString(),
      type: {
        label: "The Broth-Seeker",
        blurb:
          "You're drawn to warm, simmered dishes — kalguksu, jjigae, samgyetang. Texture matters more than spice. You rate places higher when there's quiet seating and patient service.",
      },
      summary: {
        avg_rating: avgRating,
        avg_rating_delta_month: 0.2,
        places_count: placeIds.size,
        new_places_month: newThisMonth,
        top_day_of_week: topDay ?? "Tuesday",
      },
      categories,
      rating_distribution: ratingDistribution,
      time_heatmap: {
        rows: [...rows],
        cols,
        data: heatmap,
      },
      flavor_lean: {
        umami: flavor(0),
        sweet: flavor(1),
        salty: flavor(2),
        sour: flavor(3),
        spicy: flavor(4),
        bitter: flavor(5),
      },
      top_dishes: topDishes,
      insights: [
        "You peak around Fri & Sat dinner, but your highest-rated entries are weekday lunches.",
      ],
    });
  }),

  /* ─── POST /v1/taste/refresh ─── */
  http.post(`${BASE}/taste/refresh`, async () => {
    await delay(150);
    return HttpResponse.json(
      { job_id: makeToken(), estimated_seconds: 4 },
      { status: 202 },
    );
  }),

  /* ───────────────────────────────────────────────────────────
     Settings
     ─────────────────────────────────────────────────────────── */
  http.get(`${BASE}/settings`, ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const settings = db.get().settings[user.id] ?? defaultSettings();
    return HttpResponse.json(settings);
  }),

  http.patch(`${BASE}/settings`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const body = (await request.json().catch(() => null)) as Partial<{
      notifications: Partial<{
        meal_reminders: boolean;
        taste_analysis_complete: boolean;
        weekly_picks: boolean;
      }>;
      appearance: "light" | "dark" | "system";
    }> | null;
    db.update((d) => {
      const current = d.settings[user.id] ?? defaultSettings();
      if (body?.notifications) {
        current.notifications = {
          ...current.notifications,
          ...body.notifications,
        };
      }
      if (body?.appearance) current.appearance = body.appearance;
      d.settings[user.id] = current;
    });
    return HttpResponse.json(db.get().settings[user.id]);
  }),

  /* ─── DELETE /v1/account ─── */
  http.delete(`${BASE}/account`, async ({ request }) => {
    const user = userFromAuthHeader(request);
    if (!user) return err(401, "UNAUTHORIZED", "Sign in to continue.");
    const body = (await request.json().catch(() => null)) as { confirm_email?: string } | null;
    if (body?.confirm_email !== user.email) {
      return err(400, "EMAIL_MISMATCH", "Email doesn't match your account.");
    }
    db.update((d) => {
      // Soft delete — drop user-owned records but keep the user row
      // marked so the magic-link flow could revive them. Real backend
      // does proper 30-day grace; the mock just wipes.
      delete d.users[user.id];
      delete d.emailIndex[user.email];
      for (const id of Object.keys(d.drafts)) if (d.drafts[id]!.user_id === user.id) delete d.drafts[id];
      for (const id of Object.keys(d.entries)) if (d.entries[id]!.user_id === user.id) delete d.entries[id];
      for (const id of Object.keys(d.bookmarks)) if (d.bookmarks[id]!.user_id === user.id) delete d.bookmarks[id];
      delete d.settings[user.id];
    });
    return new HttpResponse(null, { status: 204 });
  }),
];
