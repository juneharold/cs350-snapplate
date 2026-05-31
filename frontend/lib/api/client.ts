"use client";

import { useAuth } from "@/lib/store/auth";
import type { ApiError } from "@/lib/types";

// Relative base — Next.js rewrites /v1/* to the backend (see next.config.ts),
// so there's no CORS and the client stays origin-relative.
const BASE_URL = "/v1";

/** Backend success envelope: every 2xx body is { code, success, message, response }. */
type BaseResponse<T> = {
  code: number;
  success: boolean;
  message: string;
  response: T;
};

export class ApiException extends Error {
  code: string;
  status: number;
  field?: string;
  constructor(status: number, body: ApiError) {
    super(body.error.message);
    this.status = status;
    this.code = body.error.code;
    this.field = body.error.field;
  }
}

type Options = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  /** JSON body (serialized) OR a FormData for multipart uploads. */
  body?: unknown;
  /** Pass true on /auth/* — those don't need a token. */
  skipAuth?: boolean;
  signal?: AbortSignal;
};

export async function apiFetch<T>(path: string, opts: Options = {}): Promise<T> {
  const { method = "GET", body, skipAuth, signal } = opts;
  const token = skipAuth ? null : useAuth.getState().accessToken;
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

  const headers: Record<string, string> = {
    "X-Client-Version": "web-0.1.0",
    "Accept-Language": "en",
  };
  if (!(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  // Let the browser set the multipart Content-Type (with boundary) for FormData;
  // only set JSON content-type for JSON bodies.
  if (!isFormData) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body:
      body === undefined
        ? undefined
        : isFormData
          ? (body as FormData)
          : JSON.stringify(body),
    signal,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  // Errors use the {error:{code,message,field?,trace_id}} envelope (read top-level).
  if (!res.ok) throw new ApiException(res.status, data as ApiError);

  // Success bodies are wrapped in BaseResponse[T]; unwrap `response` here so every
  // domain hook keeps reading bare payloads (data.access_token, etc.). Tolerate a
  // bare body too (the MSW mock) so both backends work during the transition.
  if (data && typeof data === "object" && "response" in data && "success" in data) {
    return (data as BaseResponse<T>).response;
  }
  return data as T;
}
