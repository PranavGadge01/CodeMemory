/** Release metadata, inlined at build time from the repository release.json. */
export interface ReleaseArtifact {
  label: string;
  file: string;
  kind: string;
}

export interface ReleasePlatform {
  id: string;
  name: string;
  requirements: string;
  artifacts: ReleaseArtifact[];
}

export interface ReleaseInfo {
  version: string;
  repository: string;
  published: boolean;
  /** True only when installers are published or supplied locally. */
  available: boolean;
  /** Base URL for the artifact files. */
  base: string;
  platforms: ReleasePlatform[];
}

const EMPTY: ReleaseInfo = {
  version: "0.0.0",
  repository: "https://github.com/PranavGadge01/CodeMemory",
  published: false,
  available: false,
  base: "",
  platforms: [],
};

function read(): ReleaseInfo {
  const raw = process.env.NEXT_PUBLIC_CODEMEMORY_RELEASE;
  if (!raw) return EMPTY;
  try {
    return { ...EMPTY, ...(JSON.parse(raw) as ReleaseInfo) };
  } catch {
    return EMPTY;
  }
}

export const release: ReleaseInfo = read();

/** The published file name for an artifact template. */
export function artifactName(file: string): string {
  return file.replaceAll("{version}", release.version);
}

/** The absolute URL for an artifact template. */
export function artifactUrl(file: string): string {
  return `${release.base}/${artifactName(file)}`;
}
