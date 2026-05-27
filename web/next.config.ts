import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ["d3-hierarchy", "d3-zoom", "d3-selection", "d3-shape", "recharts"],
  },
};

export default nextConfig;
