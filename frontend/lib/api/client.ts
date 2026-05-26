"use client";

import { useAuth } from "@/lib/store/auth";
import type { ApiError } from "@/lib/types";

const BASE_URL = "/v1";

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
  body?: unknown;
  /** Pass true on /auth/* — those don't need a token. */
  skipAuth?: boolean;
  signal?: AbortSignal;
};

export async function apiFetch<T>(path: string, opts: Options = {}): Promise<T> {
  const { method = "GET", body, skipAuth, signal } = opts;
  const token = skipAuth ? null : useAuth.getState().accessToken;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Client-Version": "web-0.1.0",
    "Accept-Language": "en",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) throw new ApiException(res.status, data as ApiError);
  return data as T;
}
