# SnapPlate — MVP Backend API Contract

> **Scope:** Just enough endpoints to demo the core flows we've designed:
> auth → snap → draft → reminder → finalize → diary → taste analysis.
> Out-of-scope for MVP: push notifications (use polling), collections,
> account-deletion grace period, advanced recommendation hybrid scoring.

**Base URL:** `https://api.snapplate.app/v1`
**Auth:** `Authorization: Bearer <jwt>` on every request except `/auth/*`
**Content type:** `application/json` (except `POST /media/upload` which is `multipart/form-data`)
**Errors:** Standardized envelope (see [Error Format](#error-format))

---

## Table of Contents

1. [Auth & Account](#1-auth--account)
2. [Profile](#2-profile)
3. [Restaurants — Explore & Search](#3-restaurants--explore--search)
4. [Bookmarks](#4-bookmarks)
5. [Media Upload](#5-media-upload)
6. [Diary — Drafts](#6-diary--drafts)
7. [Diary — Entries](#7-diary--entries)
8. [Taste Analysis](#8-taste-analysis)
9. [Settings](#9-settings)
10. [Common Conventions](#10-common-conventions)

---

## 1. Auth & Account

### `POST /auth/magic-link`
Send a magic-link email. Creates user record on first request.

**Request**
```json
{ "email": "jihoon@kaist.ac.kr" }
```

**Response — 200**
```json
{ "sent": true, "resend_available_at": "2026-05-24T10:31:00Z" }
```

**Errors:** `400 INVALID_EMAIL`, `429 RATE_LIMITED`

---

### `POST /auth/verify`
Exchange the link token (from email) for a JWT.

**Request**
```json
{ "token": "eyJhbGciOiJI..." }
```

**Response — 200**
```json
{
  "access_token": "<jwt>",
  "expires_in": 2592000,
  "user": {
    "id": "u_01H...",
    "email": "jihoon@kaist.ac.kr",
    "nickname": null,
    "profile_image_url": null,
    "is_new": true
  }
}
```

**Errors:** `401 INVALID_TOKEN`, `401 EXPIRED_TOKEN`

---

### `POST /auth/logout`
Invalidates the current token server-side. Client should also clear local storage.

**Response — 204** (no body)

---

### `DELETE /account`
Soft-deletes the account (sets `deleted_at`). 30-day grace period; logging in again within that window restores.

**Request**
```json
{ "confirm_email": "jihoon@kaist.ac.kr" }
```

**Response — 204**

**Errors:** `400 EMAIL_MISMATCH`

---

## 2. Profile

### `GET /me`
Returns the current user's profile.

**Response — 200**
```json
{
  "id": "u_01H...",
  "email": "jihoon@kaist.ac.kr",
  "nickname": "Jihoon",
  "profile_image_url": "https://cdn.snapplate.app/users/u_01H.../avatar.jpg",
  "taste_type": "The Broth-Seeker",
  "stats": {
    "entries_count": 87,
    "places_count": 28,
    "bookmarks_count": 12,
    "avg_rating": 4.3
  },
  "created_at": "2026-04-01T08:00:00Z"
}
```

---

### `PATCH /me`
Update editable profile fields. Email is **not** editable.

**Request** (any subset)
```json
{ "nickname": "Jihoon Lee" }
```

**Response — 200** (full updated profile, same shape as `GET /me`)

**Validation:**
- `nickname`: 1–20 chars, letters/numbers/spaces, trimmed

**Errors:** `400 NICKNAME_TOO_LONG`, `400 NICKNAME_EMPTY`

---

### `POST /me/avatar`
Upload a profile image. `multipart/form-data`.

**Request — fields**
- `file`: image (JPEG/PNG, max 5 MB)

**Response — 200**
```json
{ "profile_image_url": "https://cdn.snapplate.app/users/.../avatar.jpg" }
```

---

## 3. Restaurants — Explore & Search

### `GET /restaurants/nearby`
Lat/lng based nearby list. Used on the Home screen.

**Query params**
| Param      | Type   | Default | Notes |
|------------|--------|---------|-------|
| `lat`      | float  | required | |
| `lng`      | float  | required | |
| `radius_m` | int    | 1500    | 200–10000 |
| `cursor`   | string | null    | from previous response |
| `limit`    | int    | 20      | max 50 |
| `sort`     | enum   | `distance` | `distance`, `rating`, `recommended` |
| `category` | string | null    | filter (see Categories below) |
| `min_rating` | float | null   | e.g. `4.0` |

**Response — 200**
```json
{
  "items": [
    {
      "id": "r_abc123",
      "name": "Bonga BBQ",
      "category": "Korean BBQ",
      "signature_dish": "Marinated short rib",
      "rating": 4.7,
      "rating_count": 312,
      "distance_m": 820,
      "thumbnail_url": "https://cdn.snapplate.app/restaurants/r_abc123/cover.jpg",
      "tags": ["reserve ahead"],
      "lat": 36.3710,
      "lng": 127.3610,
      "kakao_id": "26338954",
      "is_bookmarked": false
    }
  ],
  "next_cursor": "eyJvZmZzZXQiOjIw",
  "has_more": true
}
```

**Errors:** `400 INVALID_COORDINATES`, `403 LOCATION_PERMISSION_REQUIRED`

---

### `GET /restaurants/search`
Keyword search. Debounced 300ms client-side.

**Query params**
| Param   | Type   | Notes |
|---------|--------|-------|
| `q`     | string | required, min 1 char |
| `lat`   | float  | optional, for distance |
| `lng`   | float  | optional |
| `limit` | int    | default 20 |
| `category` | string | optional |
| `min_rating` | float | optional |

**Response — 200** — same item shape as `/nearby`. Add `match_score: float` per item.

---

### `GET /restaurants/recommended`
Personalized recommendations. Populates "For your taste" on the home screen.

**Query params**
- `lat`, `lng` (optional but improves results)
- `limit` (default 10)

**Response — 200**
```json
{
  "items": [
    {
      "id": "r_abc123",
      "name": "Sungsim Bakery — Main",
      "category": "Bakery",
      "signature_dish": "Fried streusel bun",
      "rating": 4.8,
      "rating_count": 2341,
      "distance_m": 1200,
      "thumbnail_url": "https://...",
      "thumbnail_tone": "cream",
      "thumbnail_label": "streusel bun",
      "tags": ["local favorite"],
      "lat": 36.3275,
      "lng": 127.4275,
      "kakao_id": "26338954",
      "neighborhood": "Daejong-ro",
      "reason": "You loved Acorn Cafe — both lean buttery, golden-crust",
      "is_bookmarked": false
    }
  ],
  "based_on_entries": 23,
  "has_enough_data": true
}
```

**If insufficient data:** return `"has_enough_data": false` and empty `items` — the UI shows a fallback message.

---

### `GET /restaurants/:id`
Restaurant detail screen.

**Response — 200**
```json
{
  "id": "r_abc123",
  "name": "Sungsim Bakery — Main",
  "category": "Bakery",
  "price_range": "₩₩",
  "rating": 4.8,
  "rating_count": 2341,
  "address": "15 Daejong-ro 480beon-gil, Junggu, Daejeon",
  "lat": 36.3275,
  "lng": 127.4275,
  "distance_m": 1200,
  "hours": "8:00 AM – 10:00 PM · Open daily",
  "phone": "+82-42-256-4114",
  "kakao_id": "26338954",
  "kakao_place_url": "https://place.map.kakao.com/26338954",
  "photos": [
    { "url": "https://...", "width": 1080, "height": 1080 }
  ],
  "popular_dishes": [
    { "name": "Fried streusel bun", "price": "₩2,000", "photo_url": "..." }
  ],
  "tags": ["local favorite"],
  "is_bookmarked": true,
  "personalization": {
    "reason": "You've rated 4 bakeries 4.5+ in the last month.",
    "user_visited_count": 0,
    "user_first_visit": null,
    "user_last_visit": null
  }
}
```

---

### Categories (enum)
Used for filters & recommendation.
```
Korean · Korean BBQ · Noodles · Diner / Set meal · Comfort Korean ·
Cafe · Bakery · Snacks · Chinese · Japanese · Western · Bar · Dessert
```

---

## 4. Bookmarks

### `GET /bookmarks`
List of bookmarked restaurants, recency-sorted.

**Query params**
- `q` (string, optional — search saved)
- `cursor`, `limit`

**Response — 200**
```json
{
  "items": [
    {
      "id": "b_xyz",
      "restaurant": { /* same shape as /restaurants/:id summary */ },
      "bookmarked_at": "2026-04-20T12:30:00Z"
    }
  ],
  "next_cursor": null,
  "total": 12
}
```

---

### `POST /bookmarks`
Add a bookmark.

**Request**
```json
{ "restaurant_id": "r_abc123" }
```

**Response — 201**
```json
{ "id": "b_xyz", "restaurant_id": "r_abc123", "bookmarked_at": "..." }
```

**Errors:** `409 ALREADY_BOOKMARKED`, `404 RESTAURANT_NOT_FOUND`

---

### `DELETE /bookmarks/:restaurant_id`
Remove a bookmark.

**Response — 204**

---

## 5. Media Upload

### `POST /media/upload`
Upload one or more photos. Returns IDs to attach to drafts/diary entries.
`multipart/form-data`.

**Request — fields**
- `files`: 1–10 image files (JPEG/PNG, each ≤ 10 MB, total ≤ 50 MB)
- `extract_exif`: boolean (default `true`)

**Response — 200**
```json
{
  "uploads": [
    {
      "id": "m_01H...",
      "url": "https://cdn.snapplate.app/media/m_01H....jpg",
      "thumbnail_url": "https://cdn.snapplate.app/media/m_01H...-thumb.jpg",
      "width": 3024,
      "height": 4032,
      "bytes": 3456789,
      "exif": {
        "captured_at": "2026-05-24T12:43:00Z",
        "lat": 36.3710,
        "lng": 127.3610,
        "has_location": true,
        "has_timestamp": true
      }
    }
  ]
}
```

**Errors:** `400 TOO_MANY_FILES`, `400 FILE_TOO_LARGE`, `400 UNSUPPORTED_FORMAT`

---

## 6. Diary — Drafts

> Drafts are unfinished entries — photo captured but no rating/note yet.
> They live on the home-screen dock strip and the drafts inbox until finalized.

### `POST /drafts`
Create a draft from uploaded photos. Typically called right after `POST /media/upload`.

**Request**
```json
{
  "media_ids": ["m_01H...", "m_02H..."],
  "cover_media_id": "m_01H...",
  "captured_at": "2026-05-24T12:43:00Z",
  "lat": 36.3710,
  "lng": 127.3610,
  "restaurant_id": "r_abc123",
  "restaurant_suggested": true
}
```

**Field notes:**
- `captured_at`, `lat`, `lng` — fallback to server time / null if EXIF missing
- `restaurant_id` — null if no GPS match; user picks later
- `restaurant_suggested: true` flags this as auto-detected (UI shows "GPS-matched")

**Response — 201**
```json
{
  "id": "d_01H...",
  "status": "waiting",
  "remind_at": "2026-05-24T13:43:00Z",
  /* …full draft shape, same as GET /drafts/:id */
}
```

**Status enum:** `waiting` (default) · `reminded` (server-set after reminder fires) · `needs_place` (no GPS match) · `finalizing` (briefly, while user submits)

---

### `GET /drafts`
List of the user's pending drafts. Used by:
- Home-screen dock strip (limit 10)
- Drafts inbox page (full list)

**Query params**
- `cursor`, `limit`
- `status` (optional filter)

**Response — 200**
```json
{
  "items": [
    {
      "id": "d_01H...",
      "status": "waiting",
      "captured_at": "2026-05-24T12:43:00Z",
      "captured_relative": "1h ago",
      "cover_media_url": "https://...",
      "media_count": 3,
      "restaurant": {
        "id": "r_abc123",
        "name": "Bonga BBQ",
        "neighborhood": "Eoeun-dong"
      },
      "restaurant_suggested": true,
      "remind_at": "2026-05-24T13:43:00Z"
    }
  ],
  "next_cursor": null,
  "total": 3
}
```

---

### `GET /drafts/:id`
Full draft, used to populate the entry form when finalizing.

**Response — 200**
```json
{
  "id": "d_01H...",
  "status": "reminded",
  "media": [
    { "id": "m_01H...", "url": "...", "thumbnail_url": "...", "is_cover": true }
  ],
  "captured_at": "2026-05-24T12:43:00Z",
  "lat": 36.3710,
  "lng": 127.3610,
  "restaurant": { /* full restaurant summary */ },
  "restaurant_suggested": true,
  "created_at": "2026-05-24T12:43:30Z",
  "remind_at": "2026-05-24T13:43:00Z"
}
```

---

### `PATCH /drafts/:id`
Update a draft before finalizing — e.g. user changes the restaurant.

**Request** (any subset)
```json
{
  "restaurant_id": "r_def456",
  "captured_at": "2026-05-24T12:30:00Z",
  "cover_media_id": "m_02H..."
}
```

**Response — 200** (updated draft)

---

### `POST /drafts/:id/finalize`
**The critical endpoint.** Promotes a draft to a permanent diary entry.

**Request**
```json
{
  "note": "Galbi was tender, sauce a touch sweet for me but the banchan game was strong.",
  "rating": 4.0,
  "restaurant_id": "r_abc123"
}
```

**Validation:**
- `note` — **required**, 1–500 chars
- `rating` — **optional**, float 0.5–5.0, 0.5 step
- `restaurant_id` — required if draft was `needs_place`

**Response — 201**
```json
{ "entry_id": "e_01H...", "draft_id": "d_01H..." }
```

**Side-effects:** Draft is deleted server-side; entry appears in `/entries`.

**Errors:** `400 NOTE_REQUIRED`, `400 NOTE_TOO_LONG`, `400 RESTAURANT_REQUIRED`

---

### `DELETE /drafts/:id`
Discard a draft. Photos remain in storage for 30 days (in case of accident).

**Response — 204**

---

## 7. Diary — Entries

> Finalized records. Read-only chronological log of completed meals.

### `GET /entries`
List of diary entries. Used on the Diary list screen.

**Query params**
| Param   | Type   | Default | Notes |
|---------|--------|---------|-------|
| `cursor`  | string | null  | |
| `limit`   | int    | 20    | |
| `sort`    | enum   | `recency` | `recency`, `rating_desc`, `distance` |
| `q`       | string | null  | searches note + restaurant name |
| `from`    | date   | null  | filter range |
| `to`      | date   | null  | |

**Response — 200**
```json
{
  "items": [
    {
      "id": "e_01H...",
      "captured_at": "2026-05-24T12:43:00Z",
      "day_label": "Today",
      "cover_media_url": "https://...",
      "media_count": 3,
      "restaurant": {
        "id": "r_abc123",
        "name": "Bonga BBQ",
        "signature_dish": "Marinated short rib",
        "neighborhood": "Eoeun-dong"
      },
      "rating": 4.0,
      "note_excerpt": "Galbi was tender, sauce a touch sweet…"
    }
  ],
  "next_cursor": "...",
  "has_more": true,
  "total": 87,
  "stats": {
    "entries_total": 87,
    "places_total": 28,
    "this_month": 12,
    "avg_rating": 4.3
  }
}
```

> **Note:** `day_label` is a human-friendly group key the server computes
> from the user's locale ("Today", "Yesterday", "Sun, Apr 19"). The
> client groups by consecutive equal values.

---

### `GET /entries/:id`
Full entry detail.

**Response — 200**
```json
{
  "id": "e_01H...",
  "captured_at": "2026-05-24T12:43:00Z",
  "meal_period": "lunch",
  "media": [
    { "id": "m_01H...", "url": "...", "is_cover": true }
  ],
  "rating": 4.0,
  "note": "Galbi was tender, sauce a touch sweet…",
  "ai_tags": ["tender", "sweet sauce"],
  "restaurant": { /* full restaurant payload */ },
  "user_visit_history": [
    { "entry_id": "e_xxx", "captured_at": "2026-03-12T...", "rating": 5.0 }
  ],
  "created_at": "2026-05-24T13:50:00Z"
}
```

> **`ai_tags`:** Server-generated. Phase-2 NLP from `note`. Return empty array for MVP if not yet implemented.

---

### `PATCH /entries/:id`
Edit a saved entry (rating or note only — photos & metadata are locked).

**Request** (subset)
```json
{ "rating": 4.5, "note": "Updated note." }
```

**Response — 200** (updated entry)

---

### `DELETE /entries/:id`
Delete an entry. Soft-delete; recoverable for 7 days server-side (not exposed to UI in MVP).

**Response — 204**

---

## 8. Taste Analysis

### `GET /taste/profile`
The "Your gastronomic profile" screen.

**Response — 200** (when enough data exists)
```json
{
  "has_enough_data": true,
  "min_entries_required": 10,
  "current_entries": 87,
  "computed_at": "2026-05-24T08:00:00Z",
  "type": {
    "label": "The Broth-Seeker",
    "blurb": "You're drawn to warm, simmered dishes — kalguksu, jjigae, samgyetang. Texture matters more than spice."
  },
  "summary": {
    "avg_rating": 4.3,
    "avg_rating_delta_month": 0.2,
    "places_count": 28,
    "new_places_month": 12,
    "top_day_of_week": "Tuesday"
  },
  "categories": [
    { "name": "Noodles", "weight": 0.92, "visits": 18, "tone": "bone" },
    { "name": "Cafe",    "weight": 0.78, "visits": 14, "tone": "char" }
  ],
  "rating_distribution": {
    "0.5": 0, "1.0": 0, "1.5": 1, "2.0": 0, "2.5": 2,
    "3.0": 5, "3.5": 11, "4.0": 25, "4.5": 29, "5.0": 14
  },
  "time_heatmap": {
    "rows": ["8 AM", "12 PM", "3 PM", "7 PM", "10 PM"],
    "cols": ["M", "T", "W", "T", "F", "S", "S"],
    "data": [[1,0,2,0,1,3,4], [3,4,3,2,4,2,2], ...]
  },
  "flavor_lean": {
    "umami":  0.85, "sweet":  0.40, "salty": 0.60,
    "sour":   0.92, "spicy":  0.70, "bitter": 0.55
  },
  "top_dishes": [
    { "name": "Clam noodle soup", "rating": 4.8, "visits": 5, "tone": "bone" }
  ],
  "insights": [
    "You peak around Fri & Sat dinner, but your highest-rated entries are weekday lunches."
  ]
}
```

**Response — 200** (when insufficient data)
```json
{
  "has_enough_data": false,
  "min_entries_required": 10,
  "current_entries": 7
}
```

---

### `POST /taste/refresh`
Trigger an async re-analysis. Active refreshes are idempotent per user: if the
user already has a queued or running job, this returns that job without
enqueueing another task.

**Response — 202**
```json
{
  "code": 0,
  "success": true,
  "message": "success",
  "response": {
    "job_id": "tj_ab12cd34ef56ab78",
    "status": "queued"
  }
}
```

`status` is one of `queued`, `running`, `done`, or `failed`.

---

### `GET /taste/jobs/:job_id`
Returns the current user's refresh job state. Jobs are user-scoped; a job owned
by another user is returned as not found.

**Response — 200**
```json
{
  "code": 0,
  "success": true,
  "message": "success",
  "response": {
    "job_id": "tj_ab12cd34ef56ab78",
    "status": "running",
    "started_at": "2026-05-24T08:00:02Z",
    "finished_at": null,
    "error": null
  }
}
```

---

## 9. Settings

### `GET /settings`
**Response — 200**
```json
{
  "notifications": {
    "meal_reminders": true,
    "taste_analysis_complete": true,
    "weekly_picks": false
  },
  "appearance": "light"
}
```

### `PATCH /settings`
**Request** (any subset)
```json
{ "notifications": { "weekly_picks": true } }
```

**Response — 200** (full settings)

---

## 10. Common Conventions

### Error format
Every non-2xx returns:
```json
{
  "error": {
    "code": "NOTE_REQUIRED",
    "message": "A note is required to finish this entry.",
    "field": "note",
    "trace_id": "01H..."
  }
}
```

**Common codes:** `UNAUTHORIZED` · `FORBIDDEN` · `NOT_FOUND` · `VALIDATION_ERROR` · `RATE_LIMITED` · `CONFLICT` · `SERVER_ERROR`

### Pagination
Cursor-based throughout. Request `cursor` from previous response, never construct it client-side.

### Dates & times
All timestamps are **ISO 8601 UTC** (`2026-05-24T12:43:00Z`). Client formats for display.

### Image URLs
All `*_url` fields are absolute HTTPS, signed if private. Profile photos are signed; restaurant cover photos are public CDN.

### Rate limits
- `POST /auth/magic-link`: 5 / hour / email
- `POST /media/upload`: 30 / minute / user
- All other authed endpoints: 600 / minute / user

### Request headers (every call)
```
Authorization: Bearer <jwt>
X-Client-Version: ios-1.0.2
X-Device-Id: <stable uuid>
Accept-Language: en
```

---

## Endpoint summary — MVP checklist for backend

| Group | Endpoints | Priority |
|-------|-----------|----------|
| Auth | `/auth/magic-link`, `/auth/verify`, `/auth/logout` | **P0** |
| Profile | `GET /me`, `PATCH /me`, `POST /me/avatar` | **P0** |
| Restaurants | `/restaurants/nearby`, `/restaurants/search`, `/restaurants/:id` | **P0** |
| Recommendations | `/restaurants/recommended` | P1 (can return empty array initially) |
| Bookmarks | `GET/POST/DELETE /bookmarks` | P1 |
| Media | `POST /media/upload` | **P0** |
| Drafts | `POST /drafts`, `GET /drafts`, `GET /drafts/:id`, `PATCH`, `POST /:id/finalize`, `DELETE` | **P0** |
| Entries | `GET /entries`, `GET /entries/:id`, `PATCH`, `DELETE` | **P0** |
| Taste | `GET /taste/profile`, `POST /taste/refresh`, `GET /taste/jobs/:job_id` | P1 (mock response OK for first demo) |
| Settings | `GET /settings`, `PATCH /settings` | P2 |
| Account | `DELETE /account` | P2 |

**P0 = blocks the demo flow** (snap → draft → finalize → see in diary)
**P1 = needed for full demo** (recommendations, bookmarks, taste)
**P2 = post-demo polish**

---

## Open questions for the backend team

1. **Restaurant data source:** Kakao Local REST API per SRS, but how often do we cache? Per-restaurant TTL, or refresh on demand?
2. **Reminder delivery:** SRS specifies push, but MVP can poll `/drafts` on app foreground. Confirm we skip push for v1?
3. **Image storage:** Supabase Storage signed URLs, or a CDN like Cloudflare R2?
4. **Taste analysis cadence:** On every new entry, or batch hourly?
5. **Search backend:** Postgres full-text for MVP, or set up a search index (Meili / Typesense)?
