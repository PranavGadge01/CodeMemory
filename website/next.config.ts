import type { NextConfig } from "next";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * release.json at the repository root stays the single source of truth. It is
 * read here, in Node, and handed to the app as one inlined environment value so
 * no page ever reaches outside the website directory at build time.
 */
const root = dirname(fileURLToPath(import.meta.url));
const release = JSON.parse(readFileSync(join(root, "..", "release.json"), "utf8"));
const artifacts = process.env.CODEMEMORY_RELEASE_DIR;

const payload = {
  ...release,
  // Downloads only become real once the release is published, or when a local
  // artifact directory is supplied for a self-hosted build.
  available: Boolean(artifacts) || Boolean(release.published),
  base: artifacts
    ? `/releases/v${release.version}`
    : `${release.repository}/releases/download/v${release.version}`,
};

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  env: { NEXT_PUBLIC_CODEMEMORY_RELEASE: JSON.stringify(payload) },
};

export default nextConfig;
