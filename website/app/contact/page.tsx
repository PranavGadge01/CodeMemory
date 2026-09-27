import { release } from "@/lib/release";
import { ProseSection, SitePageShell } from "@/components/site/page-shell";

export const metadata = {
  title: "Contact",
  description: "How to reach the CodeMemory project for bugs, questions and release issues.",
};

export default function ContactPage() {
  return (
    <SitePageShell
      eyebrow="Contact"
      title="Talk to the project."
      intro="CodeMemory is developed in the open, so the fastest way to reach it is through the repository rather than a support inbox."
    >
      <div className="flex flex-col gap-5">
        <ProseSection title="Bugs and feature requests">
          <p>
            Open an issue on{" "}
            <a className="text-accent-ink hover:underline" href={`${release.repository}/issues`}>
              GitHub Issues
            </a>
            . Include what you did, what you expected, and what happened instead. If a problem
            involves a sync run, the counters it reported are the most useful detail.
          </p>
        </ProseSection>

        <ProseSection title="Questions about a release">
          <p>
            Check{" "}
            <a className="text-accent-ink hover:underline" href={`${release.repository}/releases`}>
              GitHub Releases
            </a>{" "}
            for published installers and release notes. Until an artifact is published there, the
            download page stays disabled on purpose.
          </p>
        </ProseSection>

        <ProseSection title="Security">
          <p>
            Describe the impact without pasting credentials, session cookies or CSRF tokens.
            Never include a real <span className="font-technical-sm">LEETCODE_SESSION</span> value
            in an issue, a screenshot or a log.
          </p>
        </ProseSection>

        <ProseSection title="What is not here yet">
          <p>
            There is no hosted CodeMemory account and no support inbox. Everything the application
            does happens on your machine, so there is no service-side account to contact.
          </p>
        </ProseSection>
      </div>
    </SitePageShell>
  );
}
