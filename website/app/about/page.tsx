import { release } from "@/lib/release";
import { DownloadCallout, ProseSection, SitePageShell } from "@/components/site/page-shell";

export const metadata = {
  title: "About",
  description:
    "CodeMemory is a local-first Windows workspace that keeps your LeetCode submissions, notes and review history on your own computer.",
};

export default function AboutPage() {
  return (
    <SitePageShell
      eyebrow="About"
      title="A memory for the work behind the solution."
      intro="CodeMemory keeps the parts of practice that a submission list throws away: the wrong answers, the approach you abandoned, the reasoning that finally worked."
    >
      <div className="flex flex-col gap-5">
        <ProseSection title="What CodeMemory is">
          <p>
            A Windows application for your own coding history. It connects to LeetCode, keeps
            every attempt it can see, and turns that history into something you can search,
            revisit and learn from.
          </p>
          <p>
            Problems, attempts, notes, review state, revision priority and memory search are all
            account-scoped: switching LeetCode profiles never mixes one account&rsquo;s private
            notes or review state into another&rsquo;s.
          </p>
        </ProseSection>

        <ProseSection title="How it is built">
          <p>
            A Tauri desktop shell wraps a static Next.js interface and a local FastAPI service
            that listens on <span className="font-technical-sm">127.0.0.1</span>. History is
            stored in DuckDB with Parquet exports alongside it.
          </p>
          <p>
            The public website you are reading is a separate, static build. It has no server
            component, no database, and no access to any desktop data.
          </p>
        </ProseSection>

        <ProseSection title="Where your data lives">
          <p>
            Installed runtime data lives in your Windows user folder under{" "}
            <span className="font-technical-sm">%LOCALAPPDATA%\CodeMemory</span>. Upgrades move
            that data forward rather than replacing it, and credentials are encrypted through the
            operating system credential vault.
          </p>
        </ProseSection>

        <ProseSection title="Where the project lives">
          <p>
            CodeMemory is developed in the open. Source, issues and release notes are at{" "}
            <a className="text-accent-ink hover:underline" href={release.repository}>
              {release.repository.replace("https://", "")}
            </a>
            .
          </p>
        </ProseSection>

        <div>
          <DownloadCallout />
        </div>
      </div>
    </SitePageShell>
  );
}
