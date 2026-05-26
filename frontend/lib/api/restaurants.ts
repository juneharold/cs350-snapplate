"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type {
  BookmarkListResponse,
  RecommendedResponse,
  RestaurantDetailResponse,
  RestaurantSearchResponse,
  RestaurantSummary,
} from "@/lib/types";

export const restaurantKeys = {
  all: ["restaurants"] as const,
  nearby: (lat: number | null, lng: number | null, category?: string | null) =>
    [...restaurantKeys.all, "nearby", lat, lng, category ?? null] as const,
  detail: (id: string) => [...restaurantKeys.all, "detail", id] as const,
  search: (q: string, lat: number | null, lng: number | null) =>
    [...restaurantKeys.all, "search", q, lat, lng] as const,
};

export const bookmarkKeys = {
  all: ["bookmarks"] as const,
  list: (q: string) => [...bookmarkKeys.all, "list", q] as const,
};

export type NearbyResponse = {
  items: RestaurantSummary[];
  next_cursor: string | null;
  has_more: boolean;
};

export function useNearbyRestaurants(
  lat: number | null,
  lng: number | null,
  opts: { category?: string | null; minRating?: number | null } = {},
) {
  const params = new URLSearchParams();
  if (lat != null) params.set("lat", String(lat));
  if (lng != null) params.set("lng", String(lng));
  params.set("limit", "10");
  if (opts.category) params.set("category", opts.category);
  if (opts.minRating != null) params.set("min_rating", String(opts.minRating));
  return useQuery({
    queryKey: restaurantKeys.nearby(lat, lng, opts.category ?? null),
    enabled: lat != null && lng != null,
    queryFn: () =>
      apiFetch<NearbyResponse>(`/restaurants/nearby?${params.toString()}`),
  });
}

export function useRestaurant(id: string | null) {
  return useQuery({
    queryKey: id ? restaurantKeys.detail(id) : ["restaurants", "detail", "noop"],
    enabled: !!id,
    queryFn: () => apiFetch<RestaurantDetailResponse>(`/restaurants/${id}`),
  });
}

export function useRecommendedRestaurants(
  lat: number | null,
  lng: number | null,
  opts: { limit?: number } = {},
) {
  const params = new URLSearchParams();
  if (lat != null) params.set("lat", String(lat));
  if (lng != null) params.set("lng", String(lng));
  params.set("limit", String(opts.limit ?? 10));
  return useQuery({
    queryKey: [...restaurantKeys.all, "recommended", lat, lng, opts.limit ?? 10] as const,
    queryFn: () =>
      apiFetch<RecommendedResponse>(`/restaurants/recommended?${params.toString()}`),
  });
}

export function useSearchRestaurants(
  q: string,
  lat: number | null,
  lng: number | null,
) {
  const params = new URLSearchParams();
  params.set("q", q);
  if (lat != null) params.set("lat", String(lat));
  if (lng != null) params.set("lng", String(lng));
  params.set("limit", "20");
  return useQuery({
    queryKey: restaurantKeys.search(q, lat, lng),
    // Debounced + length-gated on the call site — see /search page.
    enabled: q.length > 0,
    queryFn: () => apiFetch<RestaurantSearchResponse>(`/restaurants/search?${params.toString()}`),
  });
}

export function useBookmarks(q: string = "") {
  const params = q ? `?q=${encodeURIComponent(q)}` : "";
  return useQuery({
    queryKey: bookmarkKeys.list(q),
    queryFn: () => apiFetch<BookmarkListResponse>(`/bookmarks${params}`),
  });
}

export function useToggleBookmark() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      restaurantId,
      next,
    }: {
      restaurantId: string;
      next: boolean;
    }) => {
      if (next) {
        await apiFetch<{ id: string }>("/bookmarks", {
          method: "POST",
          body: { restaurant_id: restaurantId },
        });
      } else {
        await apiFetch<void>(`/bookmarks/${restaurantId}`, { method: "DELETE" });
      }
      return { restaurantId, next };
    },
    onSuccess: ({ restaurantId, next }) => {
      // Optimistically flip is_bookmarked on the cached detail.
      qc.setQueryData<RestaurantDetailResponse>(
        restaurantKeys.detail(restaurantId),
        (prev) => (prev ? { ...prev, is_bookmarked: next } : prev),
      );
      qc.invalidateQueries({ queryKey: restaurantKeys.all });
      qc.invalidateQueries({ queryKey: bookmarkKeys.all });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
}
