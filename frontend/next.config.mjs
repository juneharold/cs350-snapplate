/** @type {import('next').NextConfig} */

// Where the real backend lives. Override via .env.local (API_URL=...).
// Server-side only — used by the dev rewrite proxy below, so no CORS and the
// client keeps fetching the relative /v1 path.
const API_URL = process.env.API_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "cdn.snapplate.app" },
      { protocol: "https", hostname: "place.map.kakao.com" },
      // Local MinIO signed-URL images (dev) so media renders against the real backend.
      { protocol: "http", hostname: "localhost", port: "9000" },
    ],
  },
  async rewrites() {
    // Proxy the API to the backend. The frontend calls relative /v1/*; Next forwards
    // it server-side to the FastAPI backend. When MSW mocks are ON they intercept
    // /v1/* in the browser before this rewrite is ever reached.
    return [
      { source: "/v1/:path*", destination: `${API_URL}/v1/:path*` },
    ];
  },
};

export default nextConfig;
