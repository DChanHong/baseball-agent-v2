import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.1.186"],
  compiler: {
    styledComponents: true,
  },
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
