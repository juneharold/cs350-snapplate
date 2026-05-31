/**
 * Shared API types — kept in sync with api-mvp.md.
 * Only the shapes we actually consume in the MVP are declared here;
 * extend as endpoints come online.
 */

export type AuthUser = {
  id: string;
  email: string;
  nickname: string | null;
  profile_image_url: string | null;
  is_new?: boolean;
};

export type VerifyResponse = {
  access_token: string;
  expires_in: number;
  user: AuthUser;
};

export type MagicLinkResponse = {
  sent: true;
  resend_available_at: string;
};

export type MeResponse = {
  id: string;
  email: string;
  nickname: string | null;
  profile_image_url: string | null;
  taste_type: string | null;
  stats: {
    entries_count: number;
    places_count: number;
    bookmarks_count: number;
    avg_rating: number;
  };
  created_at: string;
};

export type ApiError = {
  error: {
    code: string;
    message: string;
    field?: string;
    trace_id?: string;
  };
};

export type LatLng = { lat: number; lng: number };

/* ───────────────────────────────────────────────────────────
   Restaurants
   ─────────────────────────────────────────────────────────── */
export type FoodTone =
  | "terra" | "ochre" | "rust" | "moss" | "cream" | "char"
  | "berry" | "forest" | "paprika" | "butter" | "hay" | "bone";

export type RestaurantSummary = {
  id: string;
  name: string;
  category: string;
  signature_dish: string | null;
  rating: number;
  rating_count: number;
  distance_m: number;
  thumbnail_url: string | null;
  thumbnail_tone: FoodTone;
  thumbnail_label: string;
  tags: string[];
  lat: number;
  lng: number;
  kakao_id: string;
  neighborhood: string;
  is_bookmarked: boolean;
};

/* ───────────────────────────────────────────────────────────
   Media
   ─────────────────────────────────────────────────────────── */
export type MediaRecord = {
  id: string;
  url: string | null;
  thumbnail_url: string | null;
  width: number;
  height: number;
  bytes: number;
  /** Mock-only — used by FoodPlaceholder when we don't have a real URL. */
  tone: FoodTone;
  label: string;
  exif: {
    captured_at: string | null;
    lat: number | null;
    lng: number | null;
    has_location: boolean;
    has_timestamp: boolean;
  };
};

export type MediaUploadResponse = {
  uploads: MediaRecord[];
};

/* ───────────────────────────────────────────────────────────
   Drafts
   ─────────────────────────────────────────────────────────── */
export type DraftStatus = "waiting" | "reminded" | "needs_place" | "finalizing";

export type DraftSummary = {
  id: string;
  status: DraftStatus;
  captured_at: string;
  captured_relative: string;
  cover_media_url: string | null;
  cover_media_tone: FoodTone;
  cover_media_label: string;
  media_count: number;
  restaurant: {
    id: string;
    name: string;
    neighborhood: string;
  } | null;
  restaurant_suggested: boolean;
  remind_at: string | null;
};

export type DraftDetail = {
  id: string;
  status: DraftStatus;
  media: Array<{
    id: string;
    url: string | null;
    thumbnail_url: string | null;
    is_cover: boolean;
    tone: FoodTone;
    label: string;
  }>;
  captured_at: string;
  lat: number | null;
  lng: number | null;
  restaurant: RestaurantSummary | null;
  restaurant_suggested: boolean;
  created_at: string;
  remind_at: string | null;
};

export type CreateDraftRequest = {
  media_ids: string[];
  cover_media_id?: string;
  captured_at?: string | null;
  lat?: number | null;
  lng?: number | null;
  restaurant_id?: string | null;
  restaurant_suggested?: boolean;
};

export type FinalizeDraftRequest = {
  note: string;
  rating?: number;
  restaurant_id?: string;
};

export type FinalizeDraftResponse = {
  entry_id: string;
  draft_id: string;
};

export type DraftListResponse = {
  items: DraftSummary[];
  next_cursor: string | null;
  total: number;
};

/* ───────────────────────────────────────────────────────────
   Entries
   ─────────────────────────────────────────────────────────── */
export type EntrySummary = {
  id: string;
  captured_at: string;
  day_label: string;
  cover_media_url: string | null;
  cover_media_tone: FoodTone;
  cover_media_label: string;
  media_count: number;
  restaurant: {
    id: string;
    name: string;
    signature_dish: string | null;
    neighborhood: string;
  };
  rating: number | null;
  note_excerpt: string;
};

export type EntryListResponse = {
  items: EntrySummary[];
  next_cursor: string | null;
  has_more: boolean;
  total: number;
  stats: {
    entries_total: number;
    places_total: number;
    this_month: number;
    avg_rating: number;
  };
};

/* ───────────────────────────────────────────────────────────
   Taste analysis
   ─────────────────────────────────────────────────────────── */
export type TasteCategory = {
  name: string;
  weight: number;
  visits: number;
  tone: FoodTone;
};

export type FlavorLean = {
  umami: number;
  sweet: number;
  salty: number;
  sour: number;
  spicy: number;
  bitter: number;
};

export type TasteProfileResponse =
  | {
      has_enough_data: true;
      min_entries_required: number;
      current_entries: number;
      computed_at: string;
      type: { label: string; blurb: string };
      summary: {
        avg_rating: number;
        avg_rating_delta_month: number;
        places_count: number;
        new_places_month: number;
        top_day_of_week: string;
      };
      categories: TasteCategory[];
      rating_distribution: Record<string, number>;
      time_heatmap: {
        rows: string[];
        cols: string[];
        data: number[][];
      };
      flavor_lean: FlavorLean;
      top_dishes: Array<{
        name: string;
        rating: number;
        visits: number;
        tone: FoodTone;
      }>;
      insights: string[];
    }
  | {
      has_enough_data: false;
      min_entries_required: number;
      current_entries: number;
    };

/* ───────────────────────────────────────────────────────────
   Settings
   ─────────────────────────────────────────────────────────── */
export type SettingsResponse = {
  notifications: {
    meal_reminders: boolean;
    taste_analysis_complete: boolean;
    weekly_picks: boolean;
  };
  appearance: "light" | "dark" | "system";
};

export type SearchResultItem = RestaurantSummary & { match_score: number };

export type RecommendedRestaurant = RestaurantSummary & { reason: string };

export type RecommendedResponse = {
  items: RecommendedRestaurant[];
  based_on_entries: number;
  has_enough_data: boolean;
};

export type RestaurantSearchResponse = {
  items: SearchResultItem[];
  next_cursor: string | null;
  has_more: boolean;
};

export type RestaurantDetailResponse = RestaurantSummary & {
  address: string;
  price_range: string;
  hours: string;
  phone: string;
  kakao_place_url: string;
  popular_dishes: Array<{
    name: string;
    price: string;
    photo_url: string | null;
    tone: FoodTone;
  }>;
  personalization: {
    reason: string | null;
    user_visited_count: number;
    user_first_visit: string | null;
    user_last_visit: string | null;
  };
};

export type BookmarkRecord = {
  id: string;
  restaurant_id: string;
  bookmarked_at: string;
  restaurant: RestaurantSummary;
};

export type BookmarkListResponse = {
  items: BookmarkRecord[];
  next_cursor: string | null;
  total: number;
};

export type EntryDetail = {
  id: string;
  captured_at: string;
  meal_period: string | null;
  media: Array<{
    id: string;
    url: string | null;
    is_cover: boolean;
    tone: FoodTone;
    label: string;
  }>;
  rating: number | null;
  note: string;
  ai_tags: string[];
  restaurant: RestaurantSummary;
  created_at: string;
};
