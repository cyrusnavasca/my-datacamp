import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Content files and the progress DB are read from disk at request time.
  serverExternalPackages: [],
  devIndicators: false,
};

export default nextConfig;
