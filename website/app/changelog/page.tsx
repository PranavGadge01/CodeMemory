import { release } from "@/lib/release";
import { DownloadCallout, ProseSection, SitePageShell } from "@/components/site/page-shell";

export const metadata = {
  title: "Changelog",
  description: "What changed in CodeMemory, version by version.",
};

const RELEASES = [
  {
    version: release.version,
    status: release.available ? "Available" : "Preparing",
    entries: [
      "Desktop application: Tauri shell with a bundled FastAPI sidecar that starts hidden, waits for readiness, and shuts down with the app.",
      "First-launch onboarding: one intro screen, LeetCode username, public sync, then the workspace. Returning accounts open the dashboard.",
      "Account-scoped ownership: review state, notes, priority, due dates and revision metadata are isolated per LeetCode account.",
      "Authenticated sync: paginated full history with explicit accounting for duplicates, failed records and code fetches.",
      "Credential lifecycle: connect, validate, sync, disconnect and revoke, with encrypted storage and a public connection that survives credential removal.",
      "Runtime data moves to %LOCALAPPDATA%\\CodeMemory through a verified copy migration that keeps the original data as a fallback.",
      "Search, memory and semantic search scoped to the active account.",
      "Public website: product presentation, download, and the supporting public pages.",
    ],
  },
];

export default function ChangelogPage() {
  return (
    <SitePageShell
      eyebrow="Changelog"
      title="What changed, and when."
      intro="Every entry here corresponds to work that is present in the repository. Versions follow the release configuration, and a version only appears as available once its installers are published."
    >
      <div className="flex flex-col gap-5">
        {RELEASES.map((entry) => (
          <ProseSection key={entry.version} title={`Version ${entry.version} · ${entry.status}`}>
            <ul className="flex flex-col gap-2">
              {entry.entries.map((line) => (
                <li key={line} className="flex gap-3">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </ProseSection>
        ))}

        <ProseSection title="Release notes">
          <p>
            Published installers and their notes appear in{" "}
            <a className="text-accent-ink hover:underline" href={`${release.repository}/releases`}>
              GitHub Releases
            </a>
            . The download page reflects the same release configuration shown here.
          </p>
        </ProseSection>

        <div>
          <DownloadCallout />
        </div>
      </div>
    </SitePageShell>
  );
}
