/**
 * Self-hosted release step.
 *
 * When CODEMEMORY_RELEASE_DIR points at collected installers, the exported site
 * serves them from /releases/v<version>/ so the download page works offline.
 * It is a no-op for the default build, which links to GitHub Releases.
 */
import { cp, mkdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const artifacts = process.env.CODEMEMORY_RELEASE_DIR;
if (artifacts) {
  const release = JSON.parse(await readFile(join(root, "..", "..", "release.json"), "utf8"));
  const target = join(root, "..", "out", "releases", `v${release.version}`);
  await mkdir(target, { recursive: true });
  for (const platform of release.platforms) {
    for (const artifact of platform.artifacts) {
      const file = artifact.file.replaceAll("{version}", release.version);
      await cp(join(artifacts, file), join(target, file));
    }
  }
  console.log(`Copied local release artifacts into out/releases/v${release.version}.`);
} else {
  console.log("No CODEMEMORY_RELEASE_DIR; download page links to GitHub Releases.");
}
