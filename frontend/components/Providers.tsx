"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";

/**
 * Single React-Query client per browser session.
 *
 * MSW boots first (in dev/MVP only) so every hook below renders
 * against the mock backend rather than racing the real network.
 */
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: false,
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}

let browserClient: QueryClient | undefined;
function getQueryClient() {
  if (typeof window === "undefined") return makeQueryClient();
  if (!browserClient) browserClient = makeQueryClient();
  return browserClient;
}

const ENABLE_MOCKS = true; // flip to false once the real backend is live

export function Providers({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(!ENABLE_MOCKS);

  useEffect(() => {
    if (!ENABLE_MOCKS) return;
    let cancelled = false;
    (async () => {
      const { worker } = await import("@/lib/mocks/browser");
      await worker.start({
        onUnhandledRequest: "bypass",
        serviceWorker: { url: "/mockServiceWorker.js" },
      });
      if (!cancelled) setReady(true);
    })().catch((e) => {
      console.error("[snapplate] MSW failed to start", e);
      if (!cancelled) setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) return null;

  return (
    <QueryClientProvider client={getQueryClient()}>
      {children}
    </QueryClientProvider>
  );
}
