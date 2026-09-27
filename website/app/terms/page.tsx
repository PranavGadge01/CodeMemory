import { release } from "@/lib/release";
import { ProseSection, SitePageShell } from "@/components/site/page-shell";

export const metadata = {
  title: "Terms",
  description: "CodeMemory license and terms of use.",
};

export default function TermsPage() {
  return (
    <SitePageShell
      eyebrow="Terms"
      title="Terms of use."
      intro="CodeMemory is open-source software you install and run yourself. These terms describe what you receive and what you are responsible for."
    >
      <div className="flex flex-col gap-5">
        <ProseSection title="License">
          <p>
            CodeMemory is released under the MIT License. You may use, modify and redistribute it
            under those terms; the license text is in the repository at{" "}
            <a className="text-accent-ink hover:underline" href={release.repository}>
              {release.repository.replace("https://", "")}
            </a>
            .
          </p>
        </ProseSection>

        <ProseSection title="No warranty">
          <p>
            The software is provided &ldquo;as is&rdquo;, without warranty of any kind. Submitted
            history, notes and review state are stored in your own user folder, so keeping your own
            backups is your responsibility.
          </p>
        </ProseSection>

        <ProseSection title="Your accounts and credentials">
          <p>
            You are responsible for using credentials you are entitled to use, and for the choices
            you make in Settings. Credentials are stored encrypted on your machine and can be
            revoked from the application at any time.
          </p>
        </ProseSection>

        <ProseSection title="Third-party services">
          <p>
            LeetCode is an independent service and CodeMemory is not affiliated with it. Your use
            of LeetCode remains subject to LeetCode&rsquo;s own terms. Sync behaviour depends on the
            data and interfaces that service makes available.
          </p>
        </ProseSection>

        <ProseSection title="Release status">
          <p>
            The current version is{" "}
            <span className="font-technical-sm">{release.version}</span>. Installers are published
            only when a verified build exists; until then the download page shows no download link.
          </p>
        </ProseSection>
      </div>
    </SitePageShell>
  );
}
