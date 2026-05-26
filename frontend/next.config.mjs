/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "cdn.snapplate.app" },
      { protocol: "https", hostname: "place.map.kakao.com" },
    ],
  },
};

export default nextConfig;
