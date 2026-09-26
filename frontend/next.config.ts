import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  /* config options here */
  allowedDevOrigins: ["192.168.56.1"],
};

export default nextConfig;